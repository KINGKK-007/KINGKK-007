#!/usr/bin/env python3
"""Render README assets and a local GitHub-styled preview without publishing.

Requires Playwright, Pillow and an installed Chrome/Chromium. Dependencies belong
in a development virtualenv, not the profile's GitHub Actions runtime. Example:
  python scripts/preview_profile.py --label pass1

The Markdown API sanitizes a read-only copy of the README; it does not update the
repository. A clearly labeled raw-HTML fallback is available if that API fails.
The preview uses GitHub's current public styles but is not the live profile DOM.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from hashlib import sha256
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SVG = "http://www.w3.org/2000/svg"
CASE_SIZES = (("desktop-684", 684, 1440), ("compact-600", 600, 1000),
              ("mobile-390", 390, 390), ("mobile-358", 358, 390),
              ("desktop-684-light", 684, 1440), ("mobile-390-light", 390, 390))
BASELINE_DESKTOP_BYTES = 615755


def local_asset(value: str) -> str | None:
    """Resolve an image URL to a repository asset; never accept a path escape."""
    path = unquote(urlsplit(value.strip()).path)
    if "/assets/" in path:
        path = "assets/" + path.split("/assets/", 1)[1]
    elif path.startswith("./assets/"):
        path = path[2:]
    elif not path.startswith("assets/"):
        return None
    if ".." in Path(path).parts:
        return None
    return path


class ReadmeImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img":
            self.images.append(attributes)
        if tag not in ("img", "source"):
            return
        for attribute in ("src", "srcset"):
            if attribute not in attributes:
                continue
            for item in attributes[attribute].split(","):
                value = item.strip().split()[0]
                path = local_asset(value)
                if path:
                    self.references.append({"path": path, "tag": tag,
                                            "attribute": attribute,
                                            "media": attributes.get("media")})


def readme_images(source: str) -> ReadmeImages:
    parser = ReadmeImages()
    parser.feed(source)
    return parser


def desktop_payload(source: str, root: Path, baseline=BASELINE_DESKTOP_BYTES) -> dict:
    """Count each local fallback SVG once, even when several projects reuse it."""
    references = []
    for index, attributes in enumerate(readme_images(source).images):
        path = local_asset(attributes.get("src", ""))
        if path and path.endswith(".svg"):
            references.append({"image_index": index, "path": path,
                               "bytes": (root / path).stat().st_size})
    unique = {item["path"]: item["bytes"] for item in references}
    return {"baseline_bytes": baseline, "maximum_bytes": baseline * 110 // 100,
            "unique_bytes": sum(unique.values()), "unique_paths": sorted(unique),
            "reference_bytes": sum(item["bytes"] for item in references),
            "references": references}


def svg_issues(source: str) -> list[str]:
    """Check GitHub image security boundaries, independently of the generators."""
    root = ET.fromstring(source)
    issues = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in ("script", "foreignObject", "image", "text"):
            issues.append(f"unexpected {tag} element")
        for key, value in element.attrib.items():
            if key.rsplit("}", 1)[-1] == "href" and not value.startswith("#"):
                issues.append(f"external reference {value}")
            if key.startswith("on"):
                issues.append(f"event handler {key}")
        if tag == "style":
            style = element.text or ""
            if "@import" in style or "@font-face" in style:
                issues.append("external font/style dependency")
    for match in re.finditer(r"url\(\s*['\"]?([^)'\"]+)", source):
        if not match.group(1).startswith("#"):
            issues.append(f"external CSS reference {match.group(1)}")
    return sorted(set(issues))


def rectangle_overlap(a: dict, b: dict, minimum=0.25) -> float:
    width = min(a["right"], b["right"]) - max(a["left"], b["left"])
    height = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
    return width * height if width > minimum and height > minimum else 0


def text_geometry_issues(geometry: dict) -> dict:
    width, height = geometry["width"], geometry["height"]
    text = geometry["text"]
    clipped = [{"text": item["text"], "bounds": item["bounds"]} for item in text
               if (item["bounds"]["left"] < -0.15 or item["bounds"]["top"] < -0.15
                   or item["bounds"]["right"] > width + 0.15
                   or item["bounds"]["bottom"] > height + 0.15)]
    overlaps = []
    for index, first in enumerate(text):
        for second in text[index + 1:]:
            area = rectangle_overlap(first["bounds"], second["bounds"])
            if area > 0.5:
                overlaps.append({"first": first["text"], "second": second["text"],
                                 "intersection_area": round(area, 3)})
    return {"clipped_text": clipped, "text_overlaps": overlaps}


def gradient_paint_is_visible(evidence: dict) -> bool:
    """A nonempty path is insufficient: at least three raster pixels must change."""
    return evidence["painted_pixels"] >= 3 and evidence["max_channel_delta"] >= 1


def reusable_asset_evidence(raw: str, previous: dict | None, png: Path) -> bool:
    """Reuse only evidence whose SVG and saved PNG still match their hashes."""
    return bool(previous and png.is_file()
                and previous.get("sha256") == sha256(raw.encode()).hexdigest()
                and previous.get("png_sha256") == sha256(png.read_bytes()).hexdigest())


def layout_issues(name: str, result: dict, tolerance=1) -> list[str]:
    """Check the requested grid and phone wrapping using measured CSS geometry."""
    issues = []
    if name.startswith(("desktop-684", "compact-600")):
        tables = result["tables"]
        if len(tables) != 4:
            issues.append("expected four secondary project tables")
        else:
            for first, second in ((tables[0], tables[1]), (tables[2], tables[3])):
                if abs(first["top"] - second["top"]) > tolerance:
                    issues.append("secondary project cards do not form two aligned columns")
                gap = second["left"] - first["right"]
                if abs(gap - 16) > tolerance:
                    issues.append(f"secondary project gap is {gap:.3f}px; expected 16px")
            if tables[2]["top"] < max(tables[0]["bottom"], tables[1]["bottom"]) - tolerance:
                issues.append("secondary project rows overlap")
            heights = [table["height"] for table in tables]
            if max(heights) - min(heights) > tolerance:
                issues.append("secondary project cards have unequal heights")
    if name.startswith(("mobile-390", "mobile-358")):
        counts = [row["count"] for row in result["social_rows"]]
        if counts != [3, 2]:
            issues.append(f"social pills wrap as {counts}; expected [3, 2]")
    if name.startswith("mobile-358"):
        tables = result["tables"]
        if len(tables) != 4:
            issues.append("expected four stacked secondary project tables")
        else:
            for table in tables:
                if (abs(table["left"]) > tolerance or abs(table["right"] - 358) > tolerance
                        or abs(table["width"] - 358) > tolerance):
                    issues.append("phone secondary card does not fill the 358px usable column")
                    break
            if max(table["height"] for table in tables) - min(table["height"] for table in tables) > tolerance:
                issues.append("phone secondary project cards have unequal heights")
            for first, second in zip(tables, tables[1:]):
                if second["top"] < first["bottom"] - tolerance:
                    issues.append("phone secondary project cards do not form a single column")
                    break
    return issues


def fetch(url: str, body=None, content_type=None) -> bytes:
    headers = {"User-Agent": "profile-redesign-v2-local-preview",
               "Accept": "application/vnd.github+json"}
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(url, data=body, headers=headers)
    with urlopen(request, timeout=30) as response:
        return response.read()


def github_styles(cache: Path) -> tuple[str, list[dict]]:
    cache.mkdir(parents=True, exist_ok=True)
    index = cache / "github-styles.json"
    css_file = cache / "github.css"
    if index.exists() and css_file.exists():
        return css_file.read_text(), json.loads(index.read_text())
    page = fetch("https://github.com/KINGKK-007/KINGKK-007").decode()
    links = list(dict.fromkeys(re.findall(r'<link[^>]+href="([^"]+\.css)"', page)))
    names = ("light-", "dark-", "primer-primitives-", "primer-", "global-", "github-", "repository-")
    selected = [url for url in links if Path(urlsplit(url).path).name.startswith(names)]
    if not selected:
        raise RuntimeError("No public GitHub stylesheets found")
    styles, records = [], []
    for url in selected:
        css = fetch(url).decode()
        styles.append(css)
        records.append({"url": url, "bytes": len(css.encode()),
                        "sha256": sha256(css.encode()).hexdigest()})
    combined = "\n".join(styles)
    css_file.write_text(combined)
    index.write_text(json.dumps(records, indent=2))
    return combined, records


def sanitized_readme(source: str, raw=False) -> tuple[str, str]:
    if raw:
        return source, "raw README HTML; GitHub sanitizer was not used"
    try:
        body = json.dumps({"text": source, "mode": "gfm",
                           "context": "KINGKK-007/KINGKK-007"}).encode()
        html = fetch("https://api.github.com/markdown", body, "application/json").decode()
        return html, "GitHub Markdown API sanitized HTML + live public GitHub CSS; local mock"
    except (HTTPError, URLError, TimeoutError) as error:
        return source, f"raw README HTML fallback ({error}); GitHub sanitizer was not used"


def localize_images(markup: str, base: str) -> str:
    def replace(match):
        attribute, quote, value = match.groups()
        values = []
        for item in value.split(","):
            bits = item.strip().split()
            if not bits:
                continue
            path = local_asset(bits[0])
            if path:
                bits[0] = base + "/" + path
            values.append(" ".join(bits))
        return attribute + "=" + quote + ", ".join(values) + quote
    return re.sub(r"\b(src|srcset)=([\"'])(.*?)\2", replace, markup)


@contextmanager
def asset_server(root: Path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, *_):
            pass

    class Server(ThreadingHTTPServer):
        # A README with many pictures can open more than the default five local
        # connections at once. Avoid transient failures in the mock's own server.
        request_queue_size = 128

    server = Server(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


SVG_GEOMETRY_JS = """() => {
  const root = document.querySelector('svg');
  const vb = root.viewBox.baseVal;
  function bounds(element) {
    const b = element.getBBox(), m = root.getScreenCTM().inverse().multiply(element.getScreenCTM());
    const p = [[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]]
      .map(([x,y]) => new DOMPoint(x,y).matrixTransform(m));
    return {left:Math.min(...p.map(v=>v.x))-vb.x,top:Math.min(...p.map(v=>v.y))-vb.y,
      right:Math.max(...p.map(v=>v.x))-vb.x,bottom:Math.max(...p.map(v=>v.y))-vb.y};
  }
  const text = [...root.querySelectorAll('[data-text]')]
    .filter(e=>getComputedStyle(e).display!=='none' && getComputedStyle(e).visibility!=='hidden')
    .map(e=>({text:e.dataset.text,size:Number(e.dataset.size),bounds:bounds(e)}));
  const frames=[...root.querySelectorAll('rect')].filter(e=>
    Number(e.getAttribute('rx'))===12 && e.hasAttribute('stroke') && e.getAttribute('fill')!=='none')
    .map(e=>({bounds:bounds(e),stroke:e.getAttribute('stroke'),fill:e.getAttribute('fill')}));
  const animated=[...root.querySelectorAll('*')].filter(e=>getComputedStyle(e).animationName!=='none')
    .map(e=>({tag:e.tagName,class:e.getAttribute('class'),name:getComputedStyle(e).animationName}));
  const gradientPaintIssues=[],gradientStrokes=[],all=[...root.querySelectorAll('*')];
  for(const e of root.querySelectorAll('[stroke],[fill]'))for(const attribute of ['stroke','fill']){
    const ref=e.getAttribute(attribute)?.match(/^url\\(#([^)]*)\\)$/);if(!ref)continue;
    const gradient=root.querySelector('[id="'+ref[1]+'"]');
    if(!gradient||!gradient.tagName.endsWith('Gradient'))continue;
    if(attribute==='stroke')gradientStrokes.push({index:all.indexOf(e),id:ref[1],bounds:bounds(e),
      transform:[...['a','b','c','d','e','f'].map(key=>root.getScreenCTM().inverse().multiply(e.getScreenCTM())[key])]});
    if(gradient.getAttribute('gradientUnits')!=='userSpaceOnUse'){
      const box=e.getBBox();if(!box.width||!box.height)gradientPaintIssues.push({tag:e.tagName,attribute,id:ref[1]});
    }
  }
  const actionCrowding=[];
  for(const action of root.querySelectorAll('[data-action]')){
    const labels=[...action.querySelectorAll('[data-text]')],arrow=action.querySelector('path[fill="none"]');
    if(!labels.length||!arrow)continue;
    const clearance=bounds(arrow).left-Math.max(...labels.map(label=>bounds(label).right));
    if(clearance<4)actionCrowding.push({label:action.dataset.action,clearance});
  }
  return {width:vb.width,height:vb.height,text,frames,animated,gradientPaintIssues,gradientStrokes,actionCrowding};
}"""


GRADIENT_PAINT_JS = """async ({strokes, background}) => {
  const root=document.querySelector('svg'),vb=root.viewBox.baseVal;
  const width=Math.round(vb.width),height=Math.round(vb.height);
  const load=src=>new Promise((resolve,reject)=>{const image=new Image();
    image.onload=()=>resolve(image);image.onerror=reject;image.src=src});
  async function raster(svg){
    const image=await load('data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(svg)));
    const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
    const context=canvas.getContext('2d',{willReadFrequently:true});
    context.fillStyle=background;context.fillRect(0,0,width,height);context.drawImage(image,0,0,width,height);
    const png=canvas.toDataURL('image/png');
    // Decode the PNG again so evidence refers to the saved PNG pixel values.
    context.clearRect(0,0,width,height);context.drawImage(await load(png),0,0);
    return {png,data:context.getImageData(0,0,width,height).data};
  }
  const baseline=await raster(root),evidence=[];
  for(const stroke of strokes){
    const copy=root.cloneNode(true),element=copy.querySelectorAll('*')[stroke.index];
    element.setAttribute('stroke','none');element.style.setProperty('stroke','none','important');
    const hidden=await raster(copy),b=stroke.bounds;
    // CTM-transformed artboard bounds include parent translations/scales. Two
    // native pixels cover the 1px stroke and antialiasing on either side.
    const roi={left:Math.max(0,Math.floor(b.left-2)),top:Math.max(0,Math.floor(b.top-2)),
      right:Math.min(width,Math.ceil(b.right+2)),bottom:Math.min(height,Math.ceil(b.bottom+2))};
    let painted_pixels=0,max_channel_delta=0;
    for(let y=roi.top;y<roi.bottom;y++)for(let x=roi.left;x<roi.right;x++){
      const offset=(y*width+x)*4;let delta=0;
      for(let channel=0;channel<4;channel++)delta=Math.max(delta,Math.abs(baseline.data[offset+channel]-hidden.data[offset+channel]));
      if(delta){painted_pixels++;max_channel_delta=Math.max(max_channel_delta,delta)}
    }
    evidence.push({...stroke,roi,painted_pixels,max_channel_delta});
  }
  return {png:baseline.png,evidence,width,height};
}"""


README_GEOMETRY_JS = """() => {
  const article=document.querySelector('article'), ar=article.getBoundingClientRect();
  const rect=e=>{const r=e.getBoundingClientRect();return {left:r.left-ar.left,right:r.right-ar.left,
      top:r.top-ar.top,bottom:r.bottom-ar.top,width:r.width,height:r.height}};
  const imgs=[...article.querySelectorAll('img')].map(e=>({...rect(e),src:e.currentSrc,
      alt:e.alt,complete:e.complete,naturalWidth:e.naturalWidth,naturalHeight:e.naturalHeight}));
  const social=imgs.filter(e=>/assets\\/badges\\//.test(e.src));
  const rows=[];for(const img of social){let row=rows.find(r=>Math.abs(r.top-img.top)<1);
      if(!row){row={top:img.top,count:0};rows.push(row)}row.count++}
  return {article:{width:ar.width,height:ar.height},images:imgs,
    headings:[...article.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(e=>({...rect(e),tag:e.tagName,text:e.textContent})),
    tables:[...article.querySelectorAll('table')].map(rect),social_rows:rows,
    scrollWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth};
}"""


def find_chrome(value=None) -> str:
    candidates = [value, os.environ.get("CHROME_BIN"),
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  shutil.which("chromium"), shutil.which("google-chrome")]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError("Chrome not found; pass --chrome /path/to/browser")


def contact_sheets(paths: list[tuple[str, Path]], target: Path):
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=13)
    width, cell_width, cell_height = 1500, 500, 310
    for start in range(0, len(paths), 18):
        batch = paths[start:start + 18]
        sheet = Image.new("RGB", (width, ((len(batch) + 2) // 3) * cell_height), "#0d1117")
        draw = ImageDraw.Draw(sheet)
        for index, (label, path) in enumerate(batch):
            x, y = (index % 3) * cell_width, (index // 3) * cell_height
            draw.text((x + 8, y + 8), label, fill="#e6edf3", font=font)
            image = Image.open(path).convert("RGBA")
            image.thumbnail((cell_width - 16, cell_height - 34))
            sheet.paste(image, (x + 8, y + 30), image)
        sheet.save(target / f"contact-sheet-{start // 18 + 1}.png")


def run(args):
    from playwright.sync_api import sync_playwright

    root, output = args.root.resolve(), args.output.resolve()
    pass_dir = output / args.label
    pass_dir.mkdir(parents=True, exist_ok=True)
    source = (root / "README.md").read_text()
    parsed = readme_images(source)
    paths = sorted({reference["path"] for reference in parsed.references})
    missing = [path for path in paths if not (root / path).is_file()]
    if missing:
        raise RuntimeError(f"Missing README assets: {missing}")
    previous = json.loads(args.reuse_report.read_text()) if args.reuse_report else None
    selected_cases = set(args.cases.split(",")) if args.cases else {case[0] for case in CASE_SIZES}
    unknown_cases = selected_cases - {case[0] for case in CASE_SIZES}
    if unknown_cases:
        raise ValueError(f"Unknown preview cases: {sorted(unknown_cases)}")
    if previous:
        archive = pass_dir / "full-pass-geometry.json"
        if archive.exists() and archive.read_bytes() != args.reuse_report.read_bytes():
            fingerprint = sha256(args.reuse_report.read_bytes()).hexdigest()[:12]
            archive = pass_dir / f"geometry-before-focused-{fingerprint}.json"
        if not archive.exists():
            archive.write_text(args.reuse_report.read_text())
    if args.rendered_html:
        markup = args.rendered_html.read_text()
        # The captured branch page supplies its own article; the local wrapper
        # below establishes the requested column width without nesting articles.
        markup = re.sub(r"^\s*<article\b[^>]*>", "", markup, count=1)
        markup = re.sub(r"</article>\s*$", "", markup, count=1)
        rendering = ("GitHub-sanitized article captured from profile-redesign-v2 repository branch + "
                     "live public GitHub CSS; local assets/mock column, not the live profile page")
    else:
        markup, rendering = sanitized_readme(source, args.raw_html)
    css, style_sources = github_styles(args.cache)
    report = {"label": args.label, "rendering": rendering,
              "readme_sha256": sha256(source.encode()).hexdigest(),
              "style_sources": style_sources, "assets": {}, "cases": {},
              "readme_image_count": len(parsed.images), "readme_asset_count": len(paths),
              "markup_sha256": sha256(markup.encode()).hexdigest(),
              "desktop_payload": desktop_payload(source, root),
              "all_svg_bytes": {str(path.relative_to(root)): path.stat().st_size
                                for path in sorted((root / "assets").rglob("*.svg"))}}
    screenshots = []
    report["rendered_assets"] = []
    report["reused_assets"] = []
    report["rendered_cases"] = sorted(selected_cases)
    report["reused_cases"] = []
    if previous:
        report["reuse_source"] = {"path": str(archive),
                                  "readme_sha256": previous["readme_sha256"]}
        for name, metrics in previous["cases"].items():
            if name not in selected_cases:
                metrics["evidence_reused_from_readme_sha256"] = previous["readme_sha256"]
                report["cases"][name] = metrics
                report["reused_cases"].append(name)
    with sync_playwright() as playwright, asset_server(root) as base:
        browser = playwright.chromium.launch(executable_path=find_chrome(args.chrome), headless=True)
        context = browser.new_context(device_scale_factor=1, reduced_motion="reduce", color_scheme="dark")
        page = context.new_page()
        for path in paths:
            raw = (root / path).read_text()
            relative = Path(path).relative_to("assets").with_suffix(".png")
            image_path = output / "assets" / relative
            screenshots.append((path, image_path))
            old = previous["assets"].get(path) if previous else None
            if reusable_asset_evidence(raw, old, image_path):
                report["assets"][path] = old
                report["reused_assets"].append(path)
                continue
            report["rendered_assets"].append(path)
            issues = svg_issues(raw)
            element = ET.fromstring(raw)
            width, height = (float(value) for value in element.attrib["viewBox"].split()[2:])
            scheme = "light" if "-light" in Path(path).name else "dark"
            page.emulate_media(color_scheme=scheme)
            page.set_viewport_size({"width": max(400, int(width)), "height": max(300, int(height))})
            page.set_content("<html><head><style>html,body{margin:0;padding:0;line-height:0;background:"
                             + ("#fff" if scheme == "light" else "#0d1117") + "}</style></head>"
                             + "<body>" + raw + "</body></html>")
            page.wait_for_timeout(20)
            geometry = page.evaluate(SVG_GEOMETRY_JS)
            geometry.update(text_geometry_issues(geometry))
            paint = page.evaluate(GRADIENT_PAINT_JS, {
                "strokes": geometry["gradientStrokes"],
                "background": "#fff" if scheme == "light" else "#0d1117"})
            png = base64.b64decode(paint["png"].split(",", 1)[1])
            geometry["gradient_stroke_pixels"] = paint["evidence"]
            geometry["invisible_gradient_strokes"] = [item for item in paint["evidence"]
                                                       if not gradient_paint_is_visible(item)]
            geometry["png_sha256"] = sha256(png).hexdigest()
            geometry.update({"bytes": (root / path).stat().st_size,
                             "sha256": sha256(raw.encode()).hexdigest(), "security_issues": issues})
            report["assets"][path] = geometry
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(png)
        local_markup = localize_images(markup, base)
        for name, column, viewport in CASE_SIZES:
            if name not in selected_cases:
                continue
            scheme = "light" if name.endswith("-light") else "dark"
            page.emulate_media(color_scheme=scheme)
            page.set_viewport_size({"width": viewport, "height": 1000})
            document = (f"<!doctype html><html lang='en' data-color-mode='{scheme}' data-dark-theme='dark' "
                        "data-light-theme='light'><head><meta charset='utf-8'><style>" + css
                        + "</style><style>html,body{margin:0;padding:0}"
                        + f"article.preview{{width:{column}px;margin:0 auto;display:flow-root;}}"
                        + "</style></head><body><article class='preview markdown-body entry-content container-lg'>"
                        + local_markup + "</article></body></html>")
            page.set_content(document, wait_until="load")
            page.wait_for_function("[...document.images].every(i=>i.complete)")
            page.evaluate("""async () => {
              await Promise.all([...document.images].filter(i=>!i.naturalWidth).map(async image=>{
                const picture=image.closest('picture');
                if(picture)for(const source of picture.querySelectorAll('source')){
                  source.srcset=source.srcset.replace(/([?&])preview_retry=\\d+/g,'$1')
                    +(source.srcset.includes('?')?'&':'?')+'preview_retry=1';
                }
                image.src=image.src+(image.src.includes('?')?'&':'?')+'preview_retry=1';
                try{await image.decode()}catch{}
              }));
            }""")
            metrics = page.evaluate(README_GEOMETRY_JS)
            metrics["failed_images"] = [image["src"] for image in metrics["images"]
                                        if not image["naturalWidth"]]
            metrics["layout_issues"] = layout_issues(name, metrics)
            # Map each native card frame through the rendered <img> scale. Rounded
            # borders are measured at their rectangular x extent, not corner pixels.
            panels = []
            for image in metrics["images"]:
                asset = local_asset(image["src"])
                if asset not in report["assets"]:
                    continue
                geometry = report["assets"][asset]
                if not geometry["frames"] or not image["width"]:
                    continue
                if not (asset.startswith("assets/header-") or asset.startswith("assets/editorial/")
                        or asset.startswith("assets/stats/") or "pitchperfect" in asset
                        or "milestones/strip" in asset):
                    continue
                scale = image["width"] / geometry["width"]
                bounds = [frame["bounds"] for frame in geometry["frames"]]
                left, right = min(b["left"] for b in bounds), max(b["right"] for b in bounds)
                panels.append({"asset": asset, "left": image["left"] + (left - .5) * scale,
                               "right": image["left"] + (right + .5) * scale,
                               "image_width": image["width"]})
            if panels:
                metrics["full_panel_frames"] = panels
                metrics["full_panel_edge_spread"] = {
                    "left": max(p["left"] for p in panels) - min(p["left"] for p in panels),
                    "right": max(p["right"] for p in panels) - min(p["right"] for p in panels)}
            report["cases"][name] = metrics
            page.locator("article").screenshot(path=str(pass_dir / f"{name}.png"), animations="disabled")
        # Validate the actual CSS animation states in isolated image documents.
        report["animation_checks"] = {}
        page.emulate_media(color_scheme="dark")
        for path, geometry in report["assets"].items():
            raw = (root / path).read_text()
            if "@keyframes" not in raw:
                continue
            if (previous and path in report["reused_assets"]
                    and path in previous.get("animation_checks", {})):
                report["animation_checks"][path] = previous["animation_checks"][path]
                continue
            page.set_content("<html><body>" + raw + "</body></html>")
            await_reduced = page.evaluate(SVG_GEOMETRY_JS)["animated"]
            page.emulate_media(reduced_motion="no-preference")
            normal = page.evaluate(SVG_GEOMETRY_JS)["animated"]
            page.emulate_media(reduced_motion="reduce")
            report["animation_checks"][path] = {"reduced_motion_animations": await_reduced,
                                                "normal_animation_count": len(normal)}
        browser.close()
    contact_sheets(screenshots, pass_dir)
    counts = {"clipped": sum(bool(g["clipped_text"]) for g in report["assets"].values()),
              "overlaps": sum(bool(g["text_overlaps"]) for g in report["assets"].values()),
              "security": sum(bool(g["security_issues"]) for g in report["assets"].values()),
              "gradient_paint": sum(bool(g["gradientPaintIssues"]) for g in report["assets"].values()),
              "invisible_gradient_strokes": sum(bool(g["invisible_gradient_strokes"])
                                                 for g in report["assets"].values()),
              "action_crowding": sum(bool(g["actionCrowding"]) for g in report["assets"].values())}
    failures = []
    payload = report["desktop_payload"]
    if payload["unique_bytes"] > payload["maximum_bytes"]:
        failures.append(f"unique desktop payload is {payload['unique_bytes']} bytes; "
                        f"maximum is {payload['maximum_bytes']} bytes")
    for category, count in counts.items():
        if count:
            failures.append(f"{count} asset(s) with {category} issues")
    for name, result in report["cases"].items():
        result["layout_issues"] = layout_issues(name, result)
        failures.extend(f"{name}: {issue}" for issue in result["layout_issues"])
        if result["failed_images"]:
            failures.append(f"{name}: images failed to load")
        if result["scrollWidth"] > result["viewportWidth"]:
            failures.append(f"{name}: horizontal page overflow")
        edges = result.get("full_panel_edge_spread")
        if not edges or len(result.get("full_panel_frames", [])) < 7:
            failures.append(f"{name}: fewer than seven full-panel frames measured")
        elif max(edges.values()) > 1:
            failures.append(f"{name}: panel edges differ by more than 1px")
    for path, result in report["animation_checks"].items():
        if result["reduced_motion_animations"]:
            failures.append(f"{path}: CSS animations still active in reduced motion")
    report["validation_failures"] = failures
    (pass_dir / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(pass_dir / "geometry.json"), "rendering": rendering,
                      "assets": len(paths), "issues": counts,
                      "rendered_assets": len(report["rendered_assets"]),
                      "reused_assets": len(report["reused_assets"]),
                      "rendered_cases": report["rendered_cases"],
                      "desktop_payload_bytes": payload["unique_bytes"],
                      "desktop_payload_maximum_bytes": payload["maximum_bytes"],
                      "validation_failures": failures,
                      "frames": {name: result.get("full_panel_edge_spread")
                                 for name, result in report["cases"].items()},
                      "social_rows": {name: [row["count"] for row in result["social_rows"]]
                                      for name, result in report["cases"].items()}}, indent=2))
    if args.strict and failures:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="pass1")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "preview-v2")
    parser.add_argument("--cache", type=Path, default=Path("/tmp/profile-v2-preview-cache"))
    parser.add_argument("--chrome")
    parser.add_argument("--raw-html", action="store_true")
    parser.add_argument("--rendered-html", type=Path, help="Captured sanitized branch README article")
    parser.add_argument("--reuse-report", type=Path, help="Reuse unchanged SVG/PNG evidence by matching hashes")
    parser.add_argument("--cases", help="Comma-separated case names to refresh; reuse other cases from --reuse-report")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero for measured validation failures")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
