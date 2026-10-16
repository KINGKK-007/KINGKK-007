"""Render bundled fonts as SVG paths, preserving editable text in metadata."""

from functools import cache
from decimal import Decimal
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
FONT_ROOT = Path(__file__).resolve().parents[1] / "assets" / "fonts"
PATH_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
PATH_TOKEN = re.compile(r"[A-Za-z]|" + PATH_NUMBER.pattern)


def compact_path_numbers(path):
    """Shorten decimal spellings without rounding or changing SVG geometry.

    Keep separators and exponent spellings intact. Repositioning outlined
    glyphs into symbols can change browser antialiasing, so paths retain their
    original absolute coordinates and grouping.
    """
    def compact(match):
        number = match.group()
        if "." in number and "e" not in number.lower():
            number = number.rstrip("0").rstrip(".")
            number = re.sub(r"^(-?)0\.", r"\1.", number)
        return number

    return PATH_NUMBER.sub(compact, path)


def compact_quadratic_commands(path):
    """Use SVG's smooth quadratic shorthand for exact reflected controls.

    Decimal arithmetic preserves every existing coordinate. Only absolute
    contours are rewritten; relative artwork and arcs retain their source.
    Browser float arithmetic can give shorthand curves slightly different
    antialiasing, but their source geometry is unchanged.
    """
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4,
             "T": 2, "C": 6, "S": 4, "Z": 0}
    tokens = PATH_TOKEN.findall(path)
    if any(token.isalpha() and token not in arity for token in tokens):
        return path
    output = []
    index = 0
    command = previous = None
    point = start = (Decimal(0), Decimal(0))
    control = None
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        if command == "Z":
            output.append("Z")
            point, control, previous, command = start, None, "Z", None
            continue
        if command not in arity:
            return path
        count = arity[command]
        chunk = tokens[index:index + count]
        if len(chunk) != count or any(token.isalpha() for token in chunk):
            return path
        values = list(map(Decimal, chunk))
        index += count
        emitted = command
        if command == "M":
            point = start = (values[0], values[1])
        elif command == "L":
            point = (values[0], values[1])
        elif command == "H":
            point = (values[0], point[1])
        elif command == "V":
            point = (point[0], values[0])
        elif command == "Q":
            next_control = (values[0], values[1])
            if previous in ("Q", "T"):
                reflected = tuple(2 * coordinate - old for coordinate, old in zip(point, control))
                if next_control == reflected:
                    emitted, chunk = "T", chunk[2:]
            control = next_control
            point = (values[2], values[3])
        elif command == "T":
            control = (tuple(2 * coordinate - old for coordinate, old in zip(point, control))
                       if previous in ("Q", "T") else point)
            point = (values[0], values[1])
        elif command == "C":
            point = (values[4], values[5])
        elif command == "S":
            point = (values[2], values[3])
        output.append(emitted + " ".join(chunk))
        previous = command
        if command not in ("Q", "T"):
            control = None
        # Subsequent coordinate pairs after a moveto are implicit lineto.
        if command == "M":
            command = "L"
    compact = "".join(output)
    return compact if len(compact) < len(path) else path


@cache
def font(family):
    directory = "jetbrainsmono" if family == "mono" else "manrope"
    return TTFont(FONT_ROOT / directory / "font.ttf")


@cache
def glyphs(family, weight):
    return font(family).getGlyphSet(location={"wght": float(weight)})


def text_width(text, size, weight=500, family="sans", spacing=0):
    source = font(family)
    glyph_set = glyphs(family, weight)
    cmap = source.getBestCmap()
    units = source["head"].unitsPerEm
    return sum(glyph_set[cmap[ord(char)]].width for char in text) * size / units + max(0, len(text) - 1) * spacing


def text_path(text, x, y, size, weight, family, spacing, anchor):
    source = font(family)
    glyph_set = glyphs(family, weight)
    cmap = source.getBestCmap()
    scale = size / source["head"].unitsPerEm
    width = text_width(text, size, weight, family, spacing)
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    pen = SVGPathPen(glyph_set, ntos=lambda value: str(round(value, 2)))
    for char in text:
        glyph = glyph_set[cmap[ord(char)]]
        glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, x, y)))
        x += glyph.width * scale + spacing
    return pen.getCommands()


def outlined_text(text, attributes, family=None):
    size = float(attributes.get("font-size", 16))
    weight = float(attributes.get("font-weight", 500))
    spacing = float(attributes.get("letter-spacing", 0))
    x, y = float(attributes.get("x", 0)), float(attributes.get("y", 0))
    anchor = attributes.get("text-anchor", "start")
    if family is None:
        family = "mono" if "mono" in attributes.get("font-family", "").lower() else "sans"
    metadata = {"data-text": text, "data-family": family, "data-size": str(size),
                "data-weight": str(weight), "data-spacing": str(spacing),
                "data-x": str(x), "data-y": str(y), "data-anchor": anchor}
    for key in ("fill", "opacity", "class", "style"):
        if key in attributes:
            metadata[key] = attributes[key]
    group = ET.Element(f"{{{SVG}}}g", metadata)
    ET.SubElement(group, f"{{{SVG}}}path", {
        "d": text_path(text, x, y, size, weight, family, spacing, anchor)
    })
    return group


def outline_svg(svg):
    root = ET.fromstring(svg)
    theme_aware = "--text:" in svg

    def visit(parent, inherited):
        attributes = dict(inherited)
        for key in ("font-size", "font-weight", "font-family", "letter-spacing", "fill"):
            if key in parent.attrib:
                attributes[key] = parent.attrib[key]
        for child in list(parent):
            if child.tag == f"{{{SVG}}}g" and "data-text" in child.attrib:
                a = child.attrib
                settings = {"font-size": a["data-size"], "font-weight": a["data-weight"],
                            "letter-spacing": a["data-spacing"], "x": a["data-x"],
                            "y": a["data-y"], "text-anchor": a["data-anchor"]}
                settings.update({k: a[k] for k in ("fill", "opacity", "class", "style") if k in a})
                replacement = outlined_text(a["data-text"], settings, a["data-family"])
                replacement.tail = child.tail
                index = list(parent).index(child)
                parent.remove(child)
                parent.insert(index, replacement)
            elif child.tag == f"{{{SVG}}}text":
                settings = {**attributes, **child.attrib}
                if theme_aware:
                    settings.setdefault("fill", "var(--text)")
                replacement = ET.Element(f"{{{SVG}}}g")
                cursor = float(settings.get("x", 0))
                fragments = [(child.text or "", {})]
                for span in child:
                    fragments.append((span.text or "", span.attrib))
                    if span.tail:
                        fragments.append((span.tail, {}))
                for text, extra in fragments:
                    if not text:
                        continue
                    fragment = {**settings, "x": str(cursor), **extra}
                    replacement.append(outlined_text(text, fragment))
                    family = "mono" if "mono" in fragment.get("font-family", "").lower() else "sans"
                    cursor += text_width(text, float(fragment.get("font-size", 16)),
                                         float(fragment.get("font-weight", 500)), family,
                                         float(fragment.get("letter-spacing", 0)))
                replacement.tail = child.tail
                index = list(parent).index(child)
                parent.remove(child)
                parent.insert(index, replacement)
            else:
                visit(child, attributes)

    visit(root, {})
    for path in root.iter(f"{{{SVG}}}path"):
        if "d" in path.attrib:
            path.set("d", compact_quadratic_commands(compact_path_numbers(path.get("d"))))
    return ET.tostring(root, encoding="unicode") + "\n"


if __name__ == "__main__":
    import sys

    for filename in sys.argv[1:]:
        path = Path(filename)
        path.write_text(outline_svg(path.read_text()))
