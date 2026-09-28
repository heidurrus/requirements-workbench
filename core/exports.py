"""Deterministic exports and imports around the FRD (PM review: PM-15, PM-28, PM-35, bet 4.4).

- traceability matrix: quote → atom → FR → story → Jira, as an .xlsx (written by hand: no extra dependency)
- the FRD as Markdown
- the follow-up email to the client: open questions, conflicts waiting for an answer, action items
- a reviewed .docx: every comment becomes a line of a new source, tagged with the nearest requirement ID
"""
import datetime
import io
import re
import zipfile
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from core.frd import req_blocks

T = {
    "ru": {"id": "ID", "section": "Раздел", "req": "Требование", "type": "Тип", "status": "Статус атома",
           "priority": "Приоритет", "quote": "Цитата", "source": "Источник", "when": "Время", "speaker": "Спикер",
           "stories": "Истории", "jira": "Jira", "fr": "функц.", "nfr": "нефункц.", "question": "вопрос",
           "hello": "Добрый день!", "intro": "По итогам наших встреч осталось несколько вопросов. Буду благодарен за ответы.",
           "questions": "Вопросы", "confirm": "Нужно выбрать один из вариантов", "or": "или",
           "actions": "Договорённости", "owner_none": "без исполнителя", "due": "срок",
           "bye": "Спасибо!", "nothing": "Открытых вопросов нет.", "said": "прозвучало"},
    "en": {"id": "ID", "section": "Section", "req": "Requirement", "type": "Type", "status": "Atom status",
           "priority": "Priority", "quote": "Quote", "source": "Source", "when": "Time", "speaker": "Speaker",
           "stories": "Stories", "jira": "Jira", "fr": "functional", "nfr": "non-functional", "question": "question",
           "hello": "Hello,", "intro": "A few questions are still open after our meetings. I'd be grateful for your answers.",
           "questions": "Questions", "confirm": "Please choose one of the options", "or": "or",
           "actions": "Agreed next steps", "owner_none": "no owner", "due": "due",
           "bye": "Thank you!", "nothing": "No open questions.", "said": "said"},
}
PRIO = {"must": "Must", "should": "Should", "could": "Could", "wont": "Won't"}


def _t(lang):
    return T.get(lang, T["ru"])


def _clock(seconds):
    if seconds is None:
        return ""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


# ── traceability matrix ──────────────────────────────────────────────────────

def traceability_rows(store, project_id, lang="ru"):
    t = _t(lang)
    doc = store.document(project_id)
    version = store.version(doc["id"])
    if version is None:
        return [], None
    atoms = {a["id"]: a for a in store.list_atoms(project_id)}
    stories = {}
    for item in store.backlog(project_id):
        for r in item.get("refs") or []:
            stories.setdefault(r["id"], []).append(item)
    rows = []
    for number, _key, b in req_blocks(version["content"]):
        atom = atoms.get(b["atom_id"]) or {}
        linked = stories.get(b["id"], [])
        srcs = b.get("sources") or [{}]
        for i, s in enumerate(srcs):
            rows.append([b["id"] if i == 0 else "", number if i == 0 else "", b["text"] if i == 0 else "",
                         t.get({"functional": "fr"}.get(b.get("type"), b.get("type") or ""), "") if i == 0 else "",
                         atom.get("status", "") if i == 0 else "", PRIO.get(atom.get("priority"), "") if i == 0 else "",
                         s.get("quote", ""), s.get("source_title", ""), _clock(s.get("start")),
                         s.get("speaker_name") or s.get("speaker") or "",
                         "; ".join(x["title"] for x in linked) if i == 0 else "",
                         ", ".join(x["jira_key"] for x in linked if x.get("jira_key")) if i == 0 else ""])
    head = [t[k] for k in ("id", "section", "req", "type", "status", "priority", "quote", "source", "when",
                           "speaker", "stories", "jira")]
    return [head] + rows, version


def xlsx(rows, sheet="Traceability"):
    """A minimal valid .xlsx: one sheet, inline strings, bold header row."""
    def col(n):
        s = ""
        while n:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    def cell(r, c, v):
        style = ' s="1"' if r == 1 else ""
        text = escape(str(v if v is not None else "")).replace("\n", "&#10;")
        return f'<c r="{col(c)}{r}" t="inlineStr"{style}><is><t xml:space="preserve">{text}</t></is></c>'

    body = "".join(f'<row r="{r}">' + "".join(cell(r, c, v) for c, v in enumerate(row, 1)) + "</row>"
                   for r, row in enumerate(rows, 1))
    widths = [10, 8, 60, 12, 12, 10, 50, 28, 8, 16, 40, 16]
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths, 1))
    sheet_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                 f'</sheetView></sheetViews><cols>{cols}</cols><sheetData>{body}</sheetData></worksheet>')
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{escape(sheet)}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>',
        "xl/styles.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment wrapText="1" vertical="top"/></xf>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs></styleSheet>',
        "xl/worksheets/sheet1.xml": sheet_xml,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


# ── Markdown ─────────────────────────────────────────────────────────────────

def markdown(document, version, free_blocks, lang="ru"):
    t = _t(lang)
    out = [f"# {document['title']}", "", f"_v{version['number']} · "
           f"{datetime.datetime.fromtimestamp(version['created_at']).strftime('%d.%m.%Y')}_", ""]
    free = {}
    for f in free_blocks or []:
        free.setdefault(f["section"], []).append(f)

    def blocks(items):
        for b in items:
            if b["kind"] == "req":
                refs = "; ".join(f"{s.get('source_title', '')} {_clock(s.get('start'))}".strip() for s in b.get("sources") or [])
                out.append(f"- **{b['id']}** {b['text']}" + (f"  \n  _{t['source']}: {refs}_" if refs else ""))
            elif b["kind"] == "text":
                out.extend([b["text"], ""])
            elif b["kind"] == "list":
                if b.get("title"):
                    out.append(f"**{b['title']}**")
                out.extend(f"- {x}" for x in b["items"])
                out.append("")
    for sec in version["content"]["sections"]:
        out += [f"## {sec['number']}. {sec['title']}", ""]
        for f in free.get(sec["key"], []):
            out += [f["text"], ""]
        blocks(sec["blocks"])
        for sub in sec.get("subsections") or []:
            out += ["", f"### {sub['number']} {sub['title']}", ""]
            blocks(sub["blocks"])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# ── the follow-up email ──────────────────────────────────────────────────────

def followup(store, project_id, lang="ru"):
    """Plain text the BA can paste into an email, plus the question ids it covers."""
    t = _t(lang)
    atoms = store.list_atoms(project_id)
    by_id = {a["id"]: a for a in atoms}
    waiting = {c["question_atom"]: c for c in store.list_conflicts(project_id) if c.get("question_atom")}
    questions = [a for a in atoms if a["type"] == "question" and a["status"] != "rejected" and a.get("q_state") != "answered"]
    actions = [a for a in store.list_actions(project_id) if a["status"] == "open"]
    lines = [t["hello"], "", t["intro"], ""]
    ids = []
    if questions:
        lines.append(f"{t['questions']}:")
        for n, q in enumerate(questions, 1):
            lines.append(f"{n}. {q['statement']}")
            conf = waiting.get(q["id"])
            if conf:
                a, b = by_id.get(conf["atom_a"]), by_id.get(conf["atom_b"])
                if a and b:
                    lines.append(f"   {t['confirm']}: «{a['statement']}» {t['or']} «{b['statement']}»")
            ev = (q.get("evidence") or [])[:1]
            if ev and not conf:
                lines.append(f"   ({t['said']}: «{ev[0]['quote']}» — {ev[0].get('source_title', '')})")
            ids.append(q["id"])
        lines.append("")
    else:
        lines += [t["nothing"], ""]
    if actions:
        lines.append(f"{t['actions']}:")
        for a in actions:
            who = a.get("owner") or t["owner_none"]
            due = f", {t['due']}: {a['due']}" if a.get("due") else ""
            lines.append(f"- {a['text']} ({who}{due})")
        lines.append("")
    lines.append(t["bye"])
    return {"text": "\n".join(lines), "question_ids": ids, "questions": len(questions), "actions": len(actions)}


# ── a reviewed .docx comes back ──────────────────────────────────────────────

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REQ_ID = re.compile(r"\b(?:FR|NFR|Q)-\d+\b")


def docx_comments(data):
    """[(req_id or None, author, comment, anchored text)] from a .docx with review comments."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        comments_xml = z.read("word/comments.xml")
        doc_xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError):
        return []
    comments = {}
    for c in ET.fromstring(comments_xml).iter(f"{W}comment"):
        text = " ".join("".join(t.text or "" for t in p.iter(f"{W}t")) for p in c.iter(f"{W}p")).strip()
        comments[c.get(f"{W}id")] = {"author": c.get(f"{W}author") or "", "text": text}
    out, last_id = [], None
    open_ranges = {}
    for p in ET.fromstring(doc_xml).iter(f"{W}p"):
        para = "".join(t.text or "" for t in p.iter(f"{W}t"))
        found = REQ_ID.findall(para)
        if found:
            last_id = found[0]
        for el in p.iter():
            if el.tag == f"{W}commentRangeStart":
                open_ranges[el.get(f"{W}id")] = {"req": found[0] if found else last_id, "text": para}
            elif el.tag == f"{W}commentReference":
                cid = el.get(f"{W}id")
                if cid in comments:
                    anchor = open_ranges.pop(cid, {"req": found[0] if found else last_id, "text": para})
                    out.append((anchor["req"], comments[cid]["author"], comments[cid]["text"], anchor["text"][:300]))
    return out
