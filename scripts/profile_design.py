#!/usr/bin/env python3
"""Regenerate the profile's typography and responsive editorial assets."""

from html import escape
from math import ceil
from pathlib import Path
import xml.etree.ElementTree as ET

from typography import outline_svg, text_width

ROOT = Path(__file__).resolve().parents[1] / "assets"
NS = "http://www.w3.org/2000/svg"
MONO = "JetBrains Mono, monospace"
SANS = "Manrope, sans-serif"

# Edit the About copy here; desktop and mobile layouts wrap it independently.
ABOUT = [
    ["Hey, I'm Kanav. I'm studying Computer Science at IIIT Bangalore, graduating in 2028.",
     "I like asking questions and sticking with something until it finally makes sense."],
    ["Lately, I've been getting deeper into AI/ML, systems, and backend engineering.",
     "I enjoy figuring out how things work under the hood, even when it means learning from my own bugs."],
    ["Outside coding, I'm into cricket, the gym, travelling, and collecting way too many jerseys.",
     "I also keep telling myself I'll watch “just one more episode.”"],
]


def nodes(root):
    return [node for node in root.iter() if node.tag == f"{{{NS}}}text" or "data-text" in node.attrib]


def style(node, **values):
    metadata = {"x": "data-x", "y": "data-y", "font_size": "data-size",
                "font_weight": "data-weight", "letter_spacing": "data-spacing"}
    outlined = "data-text" in node.attrib
    for key, value in values.items():
        if key == "text":
            if outlined:
                node.set("data-text", value)
            else:
                node.text = value
        elif key == "family":
            node.set("data-family" if outlined else "font-family",
                     value if outlined else (MONO if value == "mono" else SANS))
        else:
            node.set(metadata.get(key, key) if outlined else key.replace("_", "-"), str(value))


def save(path, root):
    path.write_text(outline_svg(ET.tostring(root, encoding="unicode")))


def badges():
    for path in (ROOT / "badges").glob("*.svg"):
        root = ET.parse(path).getroot()
        node = nodes(root)[0]
        label = node.get("data-text", node.text or "")
        width = max(60, ceil(text_width(label, 11, 500, "mono", .15) + 50))
        root.set("width", str(width)); root.set("height", "34")
        root.set("viewBox", f"0 0 {width} 34")
        rect = root.find(f"{{{NS}}}rect")
        rect.set("width", str(width - 1)); rect.set("height", "33"); rect.set("rx", "5")
        icon = root.find(f"{{{NS}}}svg")
        icon.set("x", "12"); icon.set("y", "9")
        icon.set("width", "16"); icon.set("height", "16")
        style(node, x=37, y=21, font_size=11, font_weight=500, letter_spacing=.15, family="mono")
        save(path, root)


def cards():
    for path in (ROOT / "projects").glob("*.svg"):
        root = ET.parse(path).getroot()
        root.set("width", "400"); root.set("height", "84"); root.set("viewBox", "0 0 400 84")
        rect = root.find(f"{{{NS}}}rect")
        rect.set("width", "399"); rect.set("height", "83"); rect.set("rx", "8")
        title, description = nodes(root)
        style(title, text=root.find(f"{{{NS}}}title").text, x=50, y=30,
              font_size=14, font_weight=650, letter_spacing=-.2, family="sans")
        style(description, x=20, y=61, font_size=12.5, font_weight=450, letter_spacing=0, family="sans")
        root.find(f"{{{NS}}}g").set("transform", "translate(5 4)")
        arrow = root.findall(f"{{{NS}}}path")[-1]
        arrow.set("d", "m367 33 9-9m-9 0h9v9")
        save(path, root)
    for path in (ROOT / "milestones").glob("*.svg"):
        root = ET.parse(path).getroot()
        root.set("width", "260"); root.set("height", "112"); root.set("viewBox", "0 0 260 112")
        rect = root.find(f"{{{NS}}}rect")
        rect.set("width", "259"); rect.set("height", "111"); rect.set("rx", "8")
        title, result, description = nodes(root)
        style(title, x=44, y=26, font_size=10.2, font_weight=500, letter_spacing=.15, family="mono")
        style(result, x=20, y=67, font_size=24, font_weight=600, letter_spacing=-.7, family="sans")
        style(description, x=20, y=93, font_size=11.5, font_weight=450, family="sans")
        save(path, root)


def themed_svg(width, height, title):
    return f'''<svg xmlns="{NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(title)}</desc>
<style>:root{{--text:#182d23;--muted:#526b5d;--accent:#347a5b}}
@media(prefers-color-scheme:dark){{:root{{--text:#e6ede8;--muted:#92a69a;--accent:#9bd8bc}}}}</style>
'''


def write_svg(path, svg):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(outline_svg(svg))


def sections():
    items = [("about", "01 / ABOUT", "A little about me"),
             ("toolkit", "02 / TOOLKIT", "My toolkit"),
             ("github", "03 / ACTIVITY", "On GitHub"),
             ("projects", "04 / PROJECTS", "A few things I've built"),
             ("milestones", "05 / MILESTONES", "Along the way")]
    for name, eyebrow, title in items:
        svg = themed_svg(360, 66, title)
        svg += f'<text x="180" y="13" text-anchor="middle" font-family="{MONO}" font-size="10" font-weight="500" letter-spacing="1.2" fill="var(--muted)">{eyebrow}</text>'
        svg += f'<text x="180" y="43" text-anchor="middle" font-family="{SANS}" font-size="24" font-weight="600" letter-spacing="-.65" fill="var(--text)">{escape(title)}</text>'
        svg += '<path d="M166 60h28" stroke="var(--accent)" stroke-opacity=".65"/></svg>'
        write_svg(ROOT / "sections" / f"{name}.svg", svg)
    for name, title in [("languages", "LANGUAGES"), ("frameworks", "FRAMEWORKS"), ("tools", "TOOLS & DATA")]:
        svg = themed_svg(200, 24, title)
        svg += f'<text x="100" y="15" text-anchor="middle" font-family="{MONO}" font-size="10.5" font-weight="500" letter-spacing="1.1" fill="var(--muted)">{escape(title)}</text></svg>'
        write_svg(ROOT / "sections" / f"{name}.svg", svg)


def wrap(text, width, size, weight=450):
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate, size, weight) > width:
            lines.append(current); current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def about():
    for name, width, size, leading, gap in [("about", 840, 17, 29, 17), ("about-mobile", 360, 18, 27, 18)]:
        y, lines = 20, []
        for paragraph in ABOUT:
            sentences = paragraph if width > 400 else [" ".join(paragraph)]
            for sentence in sentences:
                for line in wrap(sentence, width - (40 if width > 400 else 20), size):
                    lines.append(f'<text x="{width/2}" y="{y}" text-anchor="middle" font-family="{SANS}" font-size="{size}" font-weight="450" fill="var(--text)">{escape(line)}</text>')
                    y += leading
            y += gap
        y -= gap
        lines.append(f'<text x="{width/2}" y="{y+5}" text-anchor="middle" font-family="{MONO}" font-size="{13 if width>400 else 14.5}" font-weight="400" fill="var(--muted)">Ctrl + Z is a lifestyle.</text>')
        description = " ".join(sentence for paragraph in ABOUT for sentence in paragraph) + " Ctrl + Z is a lifestyle."
        svg = themed_svg(width, y + 24, description) + "".join(lines) + '</svg>'
        write_svg(ROOT / "editorial" / f"{name}.svg", svg)
    for name, title, size, family, weight in [
        ("tagline", "Fueled by caffeine and questionable Git commits.", 13.5, SANS, 450),
        ("footer", "Always curious. Always building.", 11, MONO, 400),
    ]:
        svg = themed_svg(360, 32, title)
        svg += f'<text x="180" y="20" text-anchor="middle" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="var(--muted)">{escape(title)}</text></svg>'
        write_svg(ROOT / "editorial" / f"{name}.svg", svg)


def banners():
    for theme in ("dark", "light"):
        path = ROOT / f"header-{theme}.svg"
        root = ET.parse(path).getroot()
        for node in nodes(root):
            y = float(node.get("data-y", node.get("y", "0")))
            if y == 166:
                style(node, font_size=82, font_weight=600, letter_spacing=-3, family="sans")
            elif y == 210:
                style(node, font_size=22, font_weight=450, letter_spacing=-.25, family="sans")
            elif y in (53, 306, 326):
                style(node, font_size=12 if y != 326 else 10.5, letter_spacing=1.2, family="mono")
        # Preserve the existing artwork, with a separately sized mobile wordmark.
        background = "#0d1117" if theme == "dark" else "#f7f9f7"
        ink = "#f0f6f2" if theme == "dark" else "#182d23"
        muted = "#92a69a" if theme == "dark" else "#526b5d"
        accent = "#9bd8bc" if theme == "dark" else "#347a5b"
        defs = ET.tostring(root.find(f"{{{NS}}}defs"), encoding="unicode")
        art = ET.fromstring(ET.tostring(root.find(f"{{{NS}}}g")))
        art.attrib.pop("clip-path", None)
        for child in list(art):
            if nodes(child):
                art.remove(child)
        mobile = f'<svg xmlns="{NS}" width="600" height="310" viewBox="0 0 600 310" role="img" aria-labelledby="title desc"><title id="title">Kanav Kumar</title><desc id="desc">Computer Science at IIIT Bangalore. Software. Systems. Curiosity.</desc>{defs}<rect width="600" height="310" rx="18" fill="{background}"/><g transform="translate(0 90) scale(.5)">{ET.tostring(art,encoding="unicode")}</g>'
        mobile += f'<text x="32" y="38" font-family="{MONO}" font-size="11" letter-spacing="1.1" fill="{muted}">KINGKK-007 / HELLO, WORLD</text>'
        mobile += f'<text x="28" y="126" font-family="{SANS}" font-size="58" font-weight="600" letter-spacing="-2" fill="{ink}">Kanav Kumar<tspan fill="{accent}">.</tspan></text>'
        mobile += f'<text x="32" y="165" font-family="{SANS}" font-size="18" font-weight="450" fill="{muted}">Software. Systems. Curiosity.</text><path d="M32 223h24" stroke="{accent}"/>'
        mobile += f'<text x="32" y="258" font-family="{MONO}" font-size="11" letter-spacing=".5" fill="{muted}">COMPUTER SCIENCE @ IIIT BANGALORE</text></svg>'
        save(path, root)
        write_svg(ROOT / f"header-{theme}-mobile.svg", mobile)


if __name__ == "__main__":
    badges()
    cards()
    sections()
    about()
    banners()
    print("Regenerated typography, cards, section headings, and responsive About and banner assets.")
