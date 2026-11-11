"""Build the submission report from the project's Kazakh Markdown guides.

Run from any directory with the project's virtual environment::

    .venv/bin/python scripts/build_report.py

Only the generated DOCX is written; the Markdown sources stay unchanged.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"
INK = "183A56"
TEAL = "087F8C"
STUDENT = "Касанова Аружан"
GROUP = "Ис-24а"
SOURCES = (
    ("report.md", "Жоба туралы"),
    ("lab_01.md", "№1 зертханалық жұмыс"),
    ("lab_02.md", "№2 зертханалық жұмыс"),
    ("lab_03.md", "№3 зертханалық жұмыс"),
    ("lab_04.md", "№4 зертханалық жұмыс"),
    ("lab_05.md", "№5 зертханалық жұмыс"),
    ("lab_06.md", "№6 зертханалық жұмыс"),
    ("lab_07.md", "№7 зертханалық жұмыс"),
    ("defense_questions.md", "Қорғауға дайындық"),
)


def element(tag: str, **attrs: str) -> OxmlElement:
    node = OxmlElement(tag)
    for name, value in attrs.items():
        node.set(qn(name), value)
    return node


def font_for(run, *, name: str = FONT, size: float | None = None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is not None:
        fonts.set(qn("w:eastAsia"), name)
        fonts.set(qn("w:cs"), name)
    if size is not None:
        run.font.size = Pt(size)
    return run


def add_inline(paragraph, text: str) -> None:
    """Render common inline Markdown without leaking its punctuation."""
    pattern = r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|(?<!\*)\*[^*]+\*(?!\*))"
    for piece in re.split(pattern, text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            font_for(paragraph.add_run(piece[2:-2])).bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            run = font_for(paragraph.add_run(piece[1:-1]), name=MONO, size=9)
            run.font.color.rgb = RGBColor.from_string(TEAL)
        elif piece.startswith("[") and "](" in piece and piece.endswith(")"):
            label, target = piece[1:-1].split("](", 1)
            # Local source links become clear labels; web URLs remain useful in print.
            font_for(paragraph.add_run(label))
            if target.startswith(("http://", "https://")) and target != label:
                run = font_for(paragraph.add_run(f" ({target})"), size=9)
                run.font.color.rgb = RGBColor.from_string(TEAL)
        elif piece.startswith("*") and piece.endswith("*"):
            font_for(paragraph.add_run(piece[1:-1])).italic = True
        else:
            font_for(paragraph.add_run(piece))


def set_shading(cell, color: str) -> None:
    cell._tc.get_or_add_tcPr().append(element("w:shd", **{"w:fill": color}))


class ReportBuilder:
    def __init__(self, student: str = STUDENT, group: str = GROUP) -> None:
        self.doc = Document()
        self.images: set[Path] = set()
        self.student = student
        self.group = group
        self.configure()

    def configure(self) -> None:
        doc = self.doc
        section = doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.4)
        section.right_margin = Cm(1.8)
        section.header_distance = Cm(0.8)
        section.footer_distance = Cm(0.8)
        section.different_first_page_header_footer = True
        normal = doc.styles["Normal"]
        normal.font.name = FONT
        normal.font.size = Pt(10.5)
        normal.paragraph_format.line_spacing = 1.15
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.widow_control = True
        for name, size in (("Title", 26), ("Heading 1", 17), ("Heading 2", 13), ("Heading 3", 11)):
            style = doc.styles[name]
            style.font.name = FONT
            style.font.size = Pt(size)
            style.font.color.rgb = RGBColor.from_string(INK)
            style.paragraph_format.space_before = Pt(12)
            style.paragraph_format.space_after = Pt(7)
            style.paragraph_format.keep_with_next = True
        for name in ("List Bullet", "List Number"):
            doc.styles[name].font.name = FONT
            doc.styles[name].font.size = Pt(10.5)
            doc.styles[name].paragraph_format.space_after = Pt(4)
        caption = doc.styles["Caption"]
        caption.font.name = FONT
        caption.font.size = Pt(9)
        caption.font.italic = True
        caption.font.color.rgb = RGBColor.from_string("526675")
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        font_for(header.add_run("StayBook  •  №1–7 зертханалық жұмыстар"), size=8).font.color.rgb = RGBColor.from_string("677888")
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_for(footer.add_run("StayBook  |  "), size=8)
        field = element("w:fldSimple", **{"w:instr": "PAGE"})
        footer._p.append(field)
        doc.core_properties.title = "StayBook — №1–7 зертханалық жұмыстар есебі"
        doc.core_properties.subject = "Қонақүй нөмірлерін брондау ақпараттық жүйесі"
        doc.core_properties.author = self.student
        doc.core_properties.keywords = "StayBook, FastAPI, SQLModel, SQLite, Streamlit, Docker, pytest, зертханалық жұмыс"

    def title_page(self) -> None:
        doc = self.doc
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(42)
        font_for(p.add_run("ЗЕРТХАНАЛЫҚ ЖҰМЫСТАР ЕСЕБІ"), size=13).bold = True
        p = doc.add_paragraph("StayBook", "Title")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(38)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_for(p.add_run("Қонақүй нөмірлерін брондау\nақпараттық жүйесі"), size=17)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_for(p.add_run("№1 · №2 · №3 · №4 · №5 · №6 · №7"), size=15).font.color.rgb = RGBColor.from_string(TEAL)
        p.paragraph_format.space_after = Pt(42)
        for label, value in (
            ("Білім алушы", self.student),
            ("Тобы", self.group),
            ("Оқытушы", "__________________________"),
            ("Тапсыру күні", "__________________________"),
        ):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(5)
            p.paragraph_format.space_after = Pt(14)
            font_for(p.add_run(f"{label}: {value}"), size=10.5)
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(42)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_for(p.add_run("Python · FastAPI · SQLModel · SQLite\nStreamlit · Docker Compose · pytest"), size=10).font.color.rgb = RGBColor.from_string("526675")
        doc.add_page_break()
        doc.add_heading("Есептің құрамы", level=1)
        for _, title in SOURCES:
            p = doc.add_paragraph(style="List Bullet")
            add_inline(p, title)
        p = doc.add_paragraph()
        add_inline(p, "Бұл есеп бір ақпараттық жүйені жобалауды, дерекқор мен толық CRUD API жасауды, Streamlit интерфейсін, Docker арқылы іске қосуды және автоматты тестілеуді қамтитын жеті зертханалық жұмысты біріктіреді.")
        p = doc.add_paragraph()
        add_inline(p, "Титул бетіндегі оқытушы мен тапсыру күні жолдары тапсырар алдында толтырылады.")

    def add_image(self, path: Path, caption: str) -> bool:
        path = path.resolve()
        if not path.is_file() or path in self.images:
            return False
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        run = p.add_run()
        # Limit both dimensions so tall screenshots fit without clipping.
        from docx.image.image import Image

        img = Image.from_file(str(path))
        max_width, max_height = Cm(16.5), Cm(18)
        scale = min(max_width / img.width, max_height / img.height)
        run.add_picture(str(path), width=int(img.width * scale), height=int(img.height * scale))
        p = self.doc.add_paragraph(style="Caption")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(caption)
        self.images.add(path)
        return True

    def add_code(self, lines: list[str]) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(5)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.left_indent = Cm(0.2)
        p.paragraph_format.right_indent = Cm(0.2)
        p.paragraph_format.line_spacing = 1.0
        ppr = p._p.get_or_add_pPr()
        ppr.append(element("w:shd", **{"w:fill": "F1F5F8"}))
        run = font_for(p.add_run("\n".join(lines)), name=MONO, size=8)
        run.font.color.rgb = RGBColor.from_string("243847")

    def add_table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        cols = max(len(row) for row in rows)
        table = self.doc.add_table(rows=len(rows), cols=cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"
        table.autofit = True
        for row_index, cells in enumerate(rows):
            trpr = table.rows[row_index]._tr.get_or_add_trPr()
            trpr.append(element("w:cantSplit"))
            if row_index == 0:
                trpr.append(element("w:tblHeader"))
            for col_index in range(cols):
                cell = table.cell(row_index, col_index)
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.line_spacing = 1.05
                add_inline(p, cells[col_index] if col_index < len(cells) else "")
                for run in p.runs:
                    run.font.size = Pt(8.5 if cols >= 4 else 9)
                    if row_index == 0:
                        run.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                if row_index == 0:
                    set_shading(cell, INK)
                elif row_index % 2 == 0:
                    set_shading(cell, "F1F5F8")
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def markdown(self, path: Path) -> None:
        lines = path.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if line.startswith("```") or line.startswith("~~~"):
                marker = line[:3]
                i += 1
                block = []
                while i < len(lines) and not lines[i].strip().startswith(marker):
                    block.append(lines[i])
                    i += 1
                self.add_code(block)
                i += 1
                continue
            image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if image_match:
                caption, target = image_match.groups()
                if not target.startswith(("https://", "http://")):
                    self.add_image(path.parent / target, caption or "Жоба иллюстрациясы")
                i += 1
                continue
            if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
                rows = [[cell.strip() for cell in line.strip("|").split("|")]]
                i += 2
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                    i += 1
                self.add_table(rows)
                continue
            heading = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading:
                level = min(len(heading.group(1)), 3)
                p = self.doc.add_heading(level=level)
                add_inline(p, heading.group(2))
                i += 1
                continue
            if re.fullmatch(r"[-*_]{3,}", line):
                i += 1
                continue
            bullet = re.match(r"^[-*+]\s+(.*)$", line)
            numbered = re.match(r"^\d+[.)]\s+(.*)$", line)
            if bullet or numbered:
                text = (bullet or numbered).group(1)
                # Markdown task boxes render consistently in Word with plain glyphs.
                text = re.sub(r"^\[[xX]\]\s*", "✓ ", text)
                text = re.sub(r"^\[ \]\s*", "□ ", text)
                p = self.doc.add_paragraph(style="List Bullet" if bullet else "Normal")
                if numbered:
                    # Keep the source number, so independent procedures restart at 1.
                    number = re.match(r"^\d+", line).group(0)
                    text = f"{number}. {text}"
                    p.paragraph_format.left_indent = Cm(0.55)
                    p.paragraph_format.first_line_indent = Cm(-0.55)
                add_inline(p, text)
                i += 1
                continue
            if line.startswith(">"):
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.4)
                add_inline(p, line.lstrip("> "))
                for run in p.runs:
                    run.italic = True
                i += 1
                continue
            paragraph_lines = [line]
            i += 1
            while i < len(lines):
                following = lines[i].strip()
                if not following or re.match(r"^(#|[-*+]\s|\d+[.)]\s|```|~~~|\||!\[|>)", following):
                    break
                paragraph_lines.append(following)
                i += 1
            p = self.doc.add_paragraph()
            add_inline(p, " ".join(paragraph_lines))

    def build(self, output: Path) -> None:
        missing = [name for name, _ in SOURCES if not (DOCS / name).is_file()]
        if missing:
            raise FileNotFoundError("Есептің бастапқы файлдары табылмады: " + ", ".join(missing))
        self.title_page()
        for name, _ in SOURCES:
            self.doc.add_page_break()
            self.markdown(DOCS / name)
            if name == "lab_01.md":
                self.add_image(DOCS / "er_diagram.png", "ER-диаграмма: StayBook кестелері мен байланыстары")
        verification = DOCS / "verification.md"
        if verification.is_file():
            self.doc.add_page_break()
            self.markdown(verification)
        docker_verification = DOCS / "docker_verification.md"
        if docker_verification.is_file():
            self.doc.add_page_break()
            self.markdown(docker_verification)
        screenshots = []
        for name, caption in (
            ("swagger.png", "Swagger UI — StayBook API әдістері"),
            ("frontend.png", "StayBook — пайдаланушы интерфейсі"),
            ("docker.png", "Docker — контейнерлердің іске қосылуы"),
            ("docker_compose.png", "Docker Compose — backend және frontend қызметтері"),
        ):
            path = next((candidate for candidate in (DOCS / "screenshots" / name, DOCS / name) if candidate.is_file()), None)
            if path and path.resolve() not in self.images:
                screenshots.append((path, caption))
        if screenshots:
            self.doc.add_page_break()
            self.doc.add_heading("Қосымша: жұмыс істейтін жүйе", level=1)
            for path, caption in screenshots:
                self.add_image(path, caption)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DOCS / "StayBook_Labs_1-7_Report.docx")
    parser.add_argument("--student", default=STUDENT, help="Білім алушының аты-жөні")
    parser.add_argument("--group", default=GROUP, help="Оқу тобы")
    args = parser.parse_args()
    ReportBuilder(student=args.student, group=args.group).build(args.output)
    print(f"Есеп дайын: {args.output.resolve()}")


if __name__ == "__main__":
    main()
