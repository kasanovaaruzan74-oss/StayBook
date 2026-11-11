"""Regenerate the StayBook ER diagram in PNG, SVG and editable draw.io formats.

Run from the project root: python scripts/generate_er.py
Requires Pillow (listed in requirements-dev.txt).
The diagram deliberately matches the grey table-card style of the lab example.
"""

from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
WIDTH, HEIGHT = 1800, 1330
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

# Coordinates are shared by all three exports, so the editable source always
# represents precisely the same entities and links as the rendered diagram.
TABLES = [
    {
        "id": "guests",
        "title": "Қонақтар",
        "x": 105,
        "y": 260,
        "w": 620,
        "fields": ["PK  id", "full_name", "phone UNIQUE", "email UNIQUE"],
    },
    {
        "id": "room_categories",
        "title": "Нөмір санаттары",
        "x": 1075,
        "y": 260,
        "w": 620,
        "fields": ["PK  id", "name UNIQUE", "description"],
    },
    {
        "id": "bookings",
        "title": "Брондаулар",
        "x": 105,
        "y": 765,
        "w": 620,
        "fields": [
            "PK  id",
            "FK  guest_id",
            "FK  room_id",
            "check_in",
            "check_out",
            "status",
        ],
    },
    {
        "id": "rooms",
        "title": "Қонақүй нөмірлері",
        "x": 1075,
        "y": 765,
        "w": 620,
        "fields": [
            "PK  id",
            "FK  category_id",
            "room_number UNIQUE",
            "price_per_night",
            "capacity",
        ],
    },
]
for table in TABLES:
    table["h"] = 124 + 45 * len(table["fields"])

LINKS = [
    {
        "from": "guests", "to": "bookings",
        "points": [(415, 564), (415, 765)],
        "labels": [("1", 439, 587), ("0..N", 439, 722)],
        "exit": (0.5, 1), "entry": (0.5, 0),
    },
    {
        "from": "room_categories", "to": "rooms",
        "points": [(1385, 519), (1385, 765)],
        "labels": [("1", 1409, 542), ("0..N", 1409, 722)],
        "exit": (0.5, 1), "entry": (0.5, 0),
    },
    {
        "from": "rooms", "to": "bookings",
        "points": [(1075, 990), (725, 990)],
        "labels": [("1", 1034, 944), ("0..N", 746, 944)],
        "exit": (0, 225 / 349), "entry": (1, 225 / 394),
    },
]

TITLE = "StayBook дерекқорының ER сызбасы"
LEGEND = "PK — бастапқы кілт     FK — сыртқы кілт     1:0..N — бірден көпке байланыс"
NOTE = "Нөмір бір-бірімен қабаттаспайтын күндерге бірнеше рет брондалуы мүмкін."


def load_font(size: int, *, bold: bool = False, serif: bool = False):
    name = "DejaVuSerif" if serif else "DejaVuSans"
    if bold:
        name += "-Bold"
    # Fall back to Pillow's font search on Windows/macOS. Installing DejaVu Sans
    # on those systems keeps the PNG typography identical to the supplied SVG.
    path = FONT_DIR / f"{name}.ttf"
    return ImageFont.truetype(str(path) if path.exists() else f"{name}.ttf", size)


def draw_png():
    scale = 2
    canvas = Image.new("RGB", (WIDTH * scale, HEIGHT * scale), "white")
    draw = ImageDraw.Draw(canvas)

    def text_at(x, y, content, size, *, fill="#15191d", bold=False, serif=False):
        draw.text(
            (round(x * scale), round(y * scale)), content,
            font=load_font(size * scale, bold=bold, serif=serif),
            fill=fill, anchor="lt",
        )

    def centered(y, content, size, **kwargs):
        font = load_font(size * scale, bold=kwargs.get("bold", False), serif=kwargs.get("serif", False))
        length = draw.textlength(content, font=font) / scale
        text_at((WIDTH - length) / 2, y, content, size, **kwargs)

    centered(48, TITLE, 60, bold=True, serif=True)
    centered(144, LEGEND, 28)

    # Draw links before the cards: their ends terminate at the card boundaries.
    for link in LINKS:
        draw.line([(x * scale, y * scale) for x, y in link["points"]], fill="#343b42", width=3 * scale)
        for label, x, y in link["labels"]:
            text_at(x, y, label, 30, bold=True)

    for table in TABLES:
        x, y, w, h = (table[k] for k in ("x", "y", "w", "h"))
        draw.rounded_rectangle(
            (x * scale, y * scale, (x + w) * scale, (y + h) * scale),
            radius=14 * scale, fill="#f0f2f4", outline="#8e969f", width=2 * scale,
        )
        text_at(x + 28, y + 24, table["title"], 36, bold=True)
        text_at(x + 29, y + 70, table["id"], 27, bold=True, fill="#64717c")
        draw.line(
            ((x + 22) * scale, (y + 109) * scale, (x + w - 22) * scale, (y + 109) * scale),
            fill="#b1b8bf", width=2 * scale,
        )
        for index, field in enumerate(table["fields"]):
            text_at(x + 31, y + 132 + index * 45, field, 30)

    centered(1258, NOTE, 25, fill="#59636d")
    canvas.save(OUT / "er_diagram.png", dpi=(192, 192), optimize=True)


def draw_svg():
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">',
        '<title id="title">' + escape(TITLE) + '</title>',
        '<desc id="description">Қонақтар, нөмір санаттары, қонақүй нөмірлері және брондаулар. Үш бірден көпке байланыс.</desc>',
        '<rect width="1800" height="1330" fill="white"/>',
        '<g font-family="DejaVu Sans,Arial,sans-serif" fill="#15191d">',
    ]

    def svg_text(x, y, value, size, *, weight="normal", color="#15191d", anchor="start", serif=False):
        # SVG y is a baseline; adding the font ascent aligns it to Pillow's
        # top-aligned text without relying on browser-specific baseline modes.
        family = ' font-family="DejaVu Serif,serif"' if serif else ""
        parts.append(f'<text x="{x}" y="{y + size * 0.8:g}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{family}>{escape(value)}</text>')

    svg_text(WIDTH / 2, 48, TITLE, 60, weight="bold", anchor="middle", serif=True)
    svg_text(WIDTH / 2, 144, LEGEND, 28, anchor="middle")
    for link in LINKS:
        points = " ".join(f"{x},{y}" for x, y in link["points"])
        parts.append(f'<polyline points="{points}" fill="none" stroke="#343b42" stroke-width="3"/>')
        for label, x, y in link["labels"]:
            svg_text(x, y, label, 30, weight="bold")

    for table in TABLES:
        x, y, w, h = (table[k] for k in ("x", "y", "w", "h"))
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#f0f2f4" stroke="#8e969f" stroke-width="2"/>')
        svg_text(x + 28, y + 24, table["title"], 36, weight="bold")
        svg_text(x + 29, y + 70, table["id"], 27, weight="bold", color="#64717c")
        parts.append(f'<line x1="{x + 22}" y1="{y + 109}" x2="{x + w - 22}" y2="{y + 109}" stroke="#b1b8bf" stroke-width="2"/>')
        for index, field in enumerate(table["fields"]):
            svg_text(x + 31, y + 132 + index * 45, field, 30)
    svg_text(WIDTH / 2, 1258, NOTE, 25, color="#59636d", anchor="middle")
    parts.extend(["</g>", "</svg>"])
    (OUT / "er_diagram.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")


def draw_drawio():
    document = ET.Element("mxfile", host="app.diagrams.net", version="24.7.17", type="device")
    diagram = ET.SubElement(document, "diagram", id="staybook-er", name="StayBook ER")
    model = ET.SubElement(diagram, "mxGraphModel", dx="1800", dy="1330", grid="1", gridSize="10", guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1", pageWidth="1800", pageHeight="1330", background="#ffffff")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    def node(node_id, value, style, x, y, w, h, parent="1"):
        cell = ET.SubElement(root, "mxCell", id=node_id, value=value, style=style, vertex="1", parent=parent)
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"})
        return cell

    text_style = "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontFamily=DejaVu Sans;"
    node("title", escape(TITLE), text_style + "fontSize=58;fontStyle=1;", 80, 32, 1640, 90)
    node("legend", escape(LEGEND), text_style + "fontSize=28;", 80, 128, 1640, 55)
    node("note", escape(NOTE), text_style + "fontSize=25;fontColor=#59636d;", 80, 1240, 1640, 60)

    for table in TABLES:
        table_id = table["id"]
        node(table_id, "", "rounded=1;arcSize=7;whiteSpace=wrap;html=1;fillColor=#f0f2f4;strokeColor=#8e969f;strokeWidth=2;", table["x"], table["y"], table["w"], table["h"])
        left_text = "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontFamily=DejaVu Sans;spacing=0;"
        node(f"{table_id}-title", escape(table["title"]), left_text + "fontSize=36;fontStyle=1;", 28, 24, table["w"] - 56, 45, parent=table_id)
        node(f"{table_id}-sql", table_id, left_text + "fontSize=27;fontStyle=1;fontColor=#64717c;", 29, 70, table["w"] - 58, 34, parent=table_id)
        divider = ET.SubElement(root, "mxCell", id=f"{table_id}-line", style="endArrow=none;html=1;strokeColor=#b1b8bf;strokeWidth=2;", edge="1", parent=table_id)
        geo = ET.SubElement(divider, "mxGeometry", relative="1", **{"as": "geometry"})
        ET.SubElement(geo, "mxPoint", x="22", y="109", **{"as": "sourcePoint"})
        ET.SubElement(geo, "mxPoint", x=str(table["w"] - 22), y="109", **{"as": "targetPoint"})
        for index, field in enumerate(table["fields"]):
            node(f"{table_id}-field-{index}", escape(field), left_text + "fontSize=30;", 31, 132 + index * 45, table["w"] - 62, 42, parent=table_id)

    for index, link in enumerate(LINKS):
        exit_x, exit_y = link["exit"]
        entry_x, entry_y = link["entry"]
        edge = ET.SubElement(root, "mxCell", id=f"relation-{index}", source=link["from"], target=link["to"], parent="1", edge="1", style=f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=none;startArrow=none;strokeColor=#343b42;strokeWidth=3;exitX={exit_x};exitY={exit_y};exitDx=0;exitDy=0;entryX={entry_x};entryY={entry_y};entryDx=0;entryDy=0;")
        ET.SubElement(edge, "mxGeometry", relative="1", **{"as": "geometry"})
        for label_index, (label, x, y) in enumerate(link["labels"]):
            node(f"relation-{index}-label-{label_index}", label, text_style + "fontSize=30;fontStyle=1;align=left;", x, y, 98, 44)

    ET.indent(document, space="  ")
    ET.ElementTree(document).write(OUT / "er_diagram.drawio", encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    draw_png()
    draw_svg()
    draw_drawio()
    print("Created docs/er_diagram.png, docs/er_diagram.svg, docs/er_diagram.drawio")
