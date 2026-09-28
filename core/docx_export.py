"""FRD → .docx (FR-DOC-09): a neutral template and a GOST-style one (D-13).

Sources of each requirement become real Word footnotes (date · time · speaker ·
quote). python-docx has no footnote API, so the footnotes part is written as
OOXML here. The table of contents is a TOC field with the entries pre-filled,
so it reads well at once and Word refreshes page numbers when opened.
"""
import datetime
import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Mm, Pt, RGBColor

from core.transcripts import format_time

LABELS = {
    "ru": {"version": "Версия", "built": "собрана", "toc": "Содержание", "conflict": "Конфликт",
           "source": "источник", "atoms": ("требование", "требования", "требований"), "doc_kind": "ФУНКЦИОНАЛЬНЫЕ ТРЕБОВАНИЯ", "empty": "Не указано."},
    "en": {"version": "Version", "built": "built", "toc": "Contents", "conflict": "Conflict",
           "source": "source", "atoms": ("requirement", "requirements", "requirements"), "doc_kind": "FUNCTIONAL REQUIREMENTS", "empty": "Not stated."},
}

def _plural(n, forms, lang):
    if lang != "ru":
        return forms[0] if n == 1 else forms[1]
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    return forms[1] if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else forms[2]


FOOTNOTES_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"


class _Footnotes:
    """Collects footnotes while the body is written; attached as a part at the end."""

    def __init__(self, size):
        self.notes = []
        self.size = size

    def reference(self, paragraph, text):
        self.notes.append(text)
        run = paragraph.add_run()
        rpr = OxmlElement("w:rPr")
        va = OxmlElement("w:vertAlign")
        va.set(qn("w:val"), "superscript")
        rpr.append(va)
        run._r.append(rpr)
        ref = OxmlElement("w:footnoteReference")
        ref.set(qn("w:id"), str(len(self.notes)))
        run._r.append(ref)

    def attach(self, document):
        if not self.notes:
            return
        half_points = int(self.size.pt * 2)
        xml = [f"<w:footnotes {nsdecls('w')}>",
               '<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
               "</w:pPr><w:r><w:separator/></w:r></w:p></w:footnote>",
               '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:spacing w:after="0" w:line="240" '
               'w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>']
        for i, text in enumerate(self.notes, 1):
            safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            xml.append(f'<w:footnote w:id="{i}"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
                       '<w:ind w:firstLine="0"/><w:jc w:val="left"/></w:pPr>'
                       f'<w:r><w:rPr><w:vertAlign w:val="superscript"/><w:sz w:val="{half_points}"/></w:rPr><w:footnoteRef/></w:r>'
                       f'<w:r><w:rPr><w:sz w:val="{half_points}"/></w:rPr><w:t xml:space="preserve"> {safe}</w:t></w:r></w:p></w:footnote>')
        xml.append("</w:footnotes>")
        part = Part(PackURI("/word/footnotes.xml"), FOOTNOTES_CT, "".join(xml).encode("utf-8"), document.part.package)
        document.part.relate_to(part, RT.FOOTNOTES)
        settings = document.settings.element
        pr = parse_xml(f'<w:footnotePr {nsdecls("w")}><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>')
        settings.append(pr)


def _source_note(src, lang):
    bits = []
    if src.get("source_date"):
        bits.append(datetime.datetime.fromtimestamp(src["source_date"]).strftime("%d.%m.%Y"))
    if src.get("start") is not None:
        bits.append(format_time(src["start"]))
    who = src.get("speaker_name") or src.get("speaker")
    if who:
        bits.append({"BA": "BA", "OTHER": "—"}.get(who, who))
    head = " · ".join(bits)
    quote = f"«{src['quote']}»" if lang == "ru" else f"“{src['quote']}”"
    title = src.get("source_title") or ""
    return f"{head} — {quote}" + (f" ({LABELS[lang]['source']}: {title})" if title else "")


def _set_font(style, name, size, bold=None, color=None):
    style.font.name = name
    style.font.size = size
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        fonts.attrib.pop(qn(attr), None)


class _Template:
    """Formatting shared by both templates; GOST overrides fonts, spacing and headings."""
    name = "neutral"
    font, size, heading_color = "Arial", Pt(10.5), RGBColor(0x19, 0x1C, 0x1A)
    footnote_size = Pt(8)
    number_suffix = "."

    def setup(self, doc):
        sec = doc.sections[0]
        sec.page_width, sec.page_height = Mm(210), Mm(297)
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.top_margin = sec.bottom_margin = Cm(2)
        normal = doc.styles["Normal"]
        _set_font(normal, self.font, self.size)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15
        for level, size in ((1, Pt(15)), (2, Pt(12))):
            st = doc.styles[f"Heading {level}"]
            _set_font(st, self.font, size, bold=True, color=self.heading_color)
            st.paragraph_format.space_before = Pt(16 if level == 1 else 10)
            st.paragraph_format.space_after = Pt(6)
            st.paragraph_format.keep_with_next = True

    def title(self, doc, title, meta, lang):
        p = doc.add_paragraph()
        r = p.add_run(title)
        r.bold, r.font.size = True, Pt(20)
        m = doc.add_paragraph(meta)
        m.runs[0].font.color.rgb = RGBColor(0x5E, 0x64, 0x5F)

    def heading(self, doc, number, text, level):
        return doc.add_heading(f"{number}{self.number_suffix} {text}", level=level)

    def bullet(self, doc, text):
        return doc.add_paragraph(text, style="List Bullet")

    def footer(self, doc):
        pass


class _Gost(_Template):
    """ГОСТ-style layout (ГОСТ 2.105 / 34.602 conventions): Times New Roman 14, 1.5 spacing,
    margins 30/15/20/20 mm, 1.25 cm indent, numbers without a trailing dot, title page, page numbers."""
    name = "gost"
    font, size, heading_color = "Times New Roman", Pt(14), RGBColor(0, 0, 0)
    footnote_size = Pt(10)
    number_suffix = ""

    def setup(self, doc):
        sec = doc.sections[0]
        sec.page_width, sec.page_height = Mm(210), Mm(297)
        sec.left_margin, sec.right_margin = Mm(30), Mm(15)
        sec.top_margin = sec.bottom_margin = Mm(20)
        normal = doc.styles["Normal"]
        _set_font(normal, self.font, self.size)
        pf = normal.paragraph_format
        pf.line_spacing, pf.first_line_indent = 1.5, Cm(1.25)
        pf.space_after = pf.space_before = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for level in (1, 2):
            st = doc.styles[f"Heading {level}"]
            _set_font(st, self.font, self.size, bold=True, color=self.heading_color)
            st.paragraph_format.first_line_indent = Cm(1.25)
            st.paragraph_format.space_before = Pt(12)
            st.paragraph_format.space_after = Pt(6)
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            st.paragraph_format.keep_with_next = True
            st.font.italic = False

    def title(self, doc, title, meta, lang):
        for _ in range(8):
            doc.add_paragraph()
        for text, bold in ((LABELS[lang]["doc_kind"], True), (title, True), (meta, False)):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.add_run(text).bold = bold
        for _ in range(12):
            doc.add_paragraph()
        p = doc.add_paragraph(str(datetime.date.today().year))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

    def bullet(self, doc, text):
        return doc.add_paragraph(f"– {text}")

    def footer(self, doc):
        p = doc.sections[0].footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        _field(p, "PAGE", "1")
        doc.sections[0].different_first_page_header_footer = True    # no number on the title page


TEMPLATES = {"neutral": _Template, "gost": _Gost}


def _field(paragraph, instruction, cached):
    for kind, text in (("begin", None), ("instr", instruction), ("separate", None), ("text", cached), ("end", None)):
        run = paragraph.add_run()
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {text} "
            run._r.append(el)
        elif kind == "text":
            run.text = text
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            run._r.append(el)


def _toc(doc, content, tpl, lang):
    heading = doc.add_paragraph()
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER if tpl.name == "gost" else WD_ALIGN_PARAGRAPH.LEFT
    heading.paragraph_format.first_line_indent = Cm(0)
    heading.paragraph_format.page_break_before = tpl.name == "gost"      # after the title page
    run = heading.add_run(LABELS[lang]["toc"])
    run.bold = True
    entries = []
    for sec in content["sections"]:
        entries.append((0, f"{sec['number']}{tpl.number_suffix} {sec['title']}"))
        for sub in sec.get("subsections") or []:
            entries.append((1, f"{sub['number']}{tpl.number_suffix} {sub['title']}"))
    paragraphs = []
    for level, text in entries:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(0.8 * level)
        p.paragraph_format.space_after = Pt(0)
        paragraphs.append((p, text))
    # One TOC field spanning the pre-filled entries: Word replaces them with page numbers on update.
    first, last = paragraphs[0][0], paragraphs[-1][0]
    for kind in ("begin", "instr", "separate"):
        run = first.add_run()
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = ' TOC \\o "1-2" \\h \\z \\u '
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            if kind == "begin":
                el.set(qn("w:dirty"), "true")
        run._r.append(el)
    for p, text in paragraphs:
        p.add_run(text)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    last.add_run()._r.append(end)
    # Ask Word to refresh fields (page numbers in the TOC) when the file is opened.
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    doc.settings.element.append(upd)


def _req(doc, block, notes, lang, tpl):
    p = doc.add_paragraph()
    rid = p.add_run(f"{block['id']}. ")
    rid.bold = True
    p.add_run(block["text"])
    for src in block.get("sources") or []:
        notes.reference(p, _source_note(src, lang))
    if block.get("conflict"):
        c = doc.add_paragraph()
        r = c.add_run(f"⚠ {LABELS[lang]['conflict']}: {block['conflict']}")
        r.italic = True
        r.font.color.rgb = RGBColor(0x9E, 0x36, 0x26)


def _blocks(doc, blocks, notes, lang, tpl):
    for b in blocks:
        if b["kind"] == "req":
            _req(doc, b, notes, lang, tpl)
        elif b["kind"] == "text":
            doc.add_paragraph(b["text"])
        elif b["kind"] == "list":
            if b.get("title"):
                doc.add_paragraph().add_run(b["title"]).bold = True
            for item in b["items"]:
                tpl.bullet(doc, item)


def render(document, version, free_blocks, template=None):
    """Bytes of a .docx for this version; free blocks are the BA's pinned text per section."""
    content = version["content"]
    lang = content.get("language", "ru")
    tpl = TEMPLATES.get(template or document["template"], _Template)()
    doc = Document()
    tpl.setup(doc)
    notes = _Footnotes(tpl.footnote_size)
    built = datetime.datetime.fromtimestamp(version["created_at"]).strftime("%d.%m.%Y %H:%M")
    l = LABELS[lang]
    n = version["atom_count"]
    meta = f"{l['version']} {version['number']} · {l['built']} {built} · {n} {_plural(n, l['atoms'], lang)}"
    tpl.title(doc, document["title"], meta, lang)
    _toc(doc, content, tpl, lang)
    free = {}
    for fb in free_blocks:
        free.setdefault(fb["section"], []).append(fb["text"])
    for i, sec in enumerate(content["sections"]):
        h = tpl.heading(doc, sec["number"], sec["title"], 1)
        if i == 0:
            h.paragraph_format.page_break_before = True          # the document starts after the contents
        for text in free.get(sec["key"], []):
            doc.add_paragraph(text)
        _blocks(doc, sec["blocks"], notes, lang, tpl)
        for sub in sec.get("subsections") or []:
            tpl.heading(doc, sub["number"], sub["title"], 2)
            _blocks(doc, sub["blocks"], notes, lang, tpl)
        if not sec["blocks"] and not sec.get("subsections") and not free.get(sec["key"]):
            doc.add_paragraph(l["empty"])
    tpl.footer(doc)
    notes.attach(doc)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
