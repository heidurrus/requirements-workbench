"""FRD builder: accepted atoms → a structured, versioned document (spec increment 3).

One requirement in the document = one accepted atom, under a stable ID (FR-n,
NFR-n, Q-n; BR-14), with its sources copied into the version for provenance
(FR-DOC-03). The *frd* skill decides the document's sections, their titles and
order (plus extra AI-written sections) and how requirements are worded; the
*quality* skill decides which checks run. Code enforces the structure: every
atom appears exactly once, nothing is invented.

"Rebuild" regenerates only what changed since the last version (Q-15, FR-DOC-05
AC2): unchanged requirements keep their text and place word for word.
"""
import re

from core import skills
from core.llm import LLMError, complete_json, for_project, model_name

LABELS = {
    "ru": {"assumptions": "Допущения", "other": "Прочее"},
    "en": {"assumptions": "Assumptions", "other": "Other"},
}
RULES = list(skills.BUILTIN_RULES)

# Fallback vague stems when no quality skill is given (the quality skill's list wins).
VAGUE = {
    "ru": ["быстр", "удобн", "интуитивн", "современн", "надёжн", "надежн", "дружелюбн", "оптимальн",
           "эффективн", "гибк", "масштабируем", "по возможности", "при необходимости", "как правило", "максимально"],
    "en": ["fast", "quick", "user-friendly", "intuitive", "easy", "modern", "reliable", "efficient", "flexible",
           "scalable", "as appropriate", "if possible", "robust", "seamless", "as soon as possible"],
}
# NFRs about these qualities need a number or threshold to be testable (BR-08); others
# (access rules, compliance, localisation) are testable without one.
QUANTITATIVE = re.compile(r"(?<!\w)(быстр|скорост|врем|время|секунд|минут|задержк|отклик|откры|загруз|производительн|"
                          r"нагрузк|одновременн|пропускн|доступност|безотказн|аптайм|восстановлен|объ[её]м|ёмкост|емкост|"
                          r"масштаб|fast|speed|time|latency|response|load|perform|throughput|concurren|availab|uptime|"
                          r"recover|capacity|scal)", re.I)
NUMBER_WORDS = re.compile(r"\d|\b(одн|один|два|двух|три|трёх|трех|четыр|пят|шест|сем|восьм|восем|девят|десят|"
                          r"двадцат|тридцат|сорок|пятьдесят|сто|сотн|тысяч|миллион|процент|one|two|three|four|five|"
                          r"six|seven|eight|nine|ten|twenty|thirty|hundred|thousand|million|percent)", re.I)

# What the app adds to the frd skill, whatever the skill says (keeps the structure intact).
FULL_CONTRACT = """- items: each atom becomes exactly one item with the atom's ID. Keep every number, limit, role and name exactly; never add facts that are not in the atoms.
- groups: every FR ID goes into exactly one group (a sub-section with a short title).
- purpose, context, assumptions, out_of_scope: as instructed above; leave empty when the atoms give nothing.
{extra}- issues: check each FR and NFR item you wrote against the rules below and report only real problems, with a one-sentence message in {language}.

Quality rules:
{rules}"""

CHANGED_CONTRACT = """Only some requirement atoms are new or changed; everything else in the document stays as it is.
For each item under "To write":
- text: rewrite it as instructed above, keeping every number, limit and name exactly and adding nothing.
- group: for a functional requirement (FR-…), the title of the existing sub-section it belongs to, copied exactly, or a short new title if none fits. Empty for other items.
- issues: report real problems in the text you wrote, with a one-sentence message in {language}.

Quality rules:
{rules}"""

FIX_CONTRACT = """Keep every fact, number and name from the original; do not invent new facts. If fixing needs a value nobody has stated (for example a time limit), put a placeholder in square brackets, e.g. "[уточнить: N секунд]" or "[to confirm: N seconds]". Return only the rewritten requirement."""


def _issue_schema(rule_ids):
    return {"type": "array", "items": {
        "type": "object", "properties": {"id": {"type": "string"}, "rule": {"type": "string", "enum": rule_ids},
                                         "message": {"type": "string"}},
        "required": ["id", "rule", "message"], "additionalProperties": False}}


def full_schema(rule_ids, extra_keys=()):
    strings = {"type": "array", "items": {"type": "string"}}
    key = {"type": "string", "enum": list(extra_keys)} if extra_keys else {"type": "string"}
    return {
        "type": "object",
        "properties": {
            "purpose": {"type": "string"}, "context": {"type": "string"}, "assumptions": strings,
            "groups": {"type": "array", "items": {
                "type": "object", "properties": {"title": {"type": "string"}, "ids": strings},
                "required": ["title", "ids"], "additionalProperties": False}},
            "items": {"type": "array", "items": {
                "type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"], "additionalProperties": False}},
            "out_of_scope": strings,
            "extra": {"type": "array", "items": {
                "type": "object", "properties": {"key": key, "text": {"type": "string"}},
                "required": ["key", "text"], "additionalProperties": False}},
            "issues": _issue_schema(rule_ids),
        },
        "required": ["purpose", "context", "assumptions", "groups", "items", "out_of_scope", "extra", "issues"],
        "additionalProperties": False,
    }


def changed_schema(rule_ids):
    return {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {
                "type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"},
                                                 "group": {"type": "string"}},
                "required": ["id", "text", "group"], "additionalProperties": False}},
            "issues": _issue_schema(rule_ids),
        },
        "required": ["items", "issues"],
        "additionalProperties": False,
    }


FIX_SCHEMA = {"type": "object", "properties": {"statement": {"type": "string"}},
              "required": ["statement"], "additionalProperties": False}


class BuildError(Exception):
    """A user-facing reason the document can't be built."""


def language_of(texts):
    text = " ".join(texts)
    cyr = len(re.findall(r"[а-яё]", text, flags=re.I))
    lat = len(re.findall(r"[a-z]", text, flags=re.I))
    return "ru" if cyr >= lat else "en"


def _lang_name(lang):
    return "Russian" if lang == "ru" else "English"


# ── quality ──────────────────────────────────────────────────────────────────

class Quality:
    """The rules in effect, from the quality skill."""

    def __init__(self, skill=None):
        meta = skill.meta if skill else {}
        self.skill = skill
        self.vague = {k: list(v) for k, v in (meta.get("vague_words") or VAGUE).items()}
        self.custom = [r for r in meta.get("rules") or [] if isinstance(r, dict)]
        self.rule_ids = RULES + [r["id"] for r in self.custom]
        self.titles = {r["id"]: r["title"] for r in self.custom}

    def prompt(self, language):
        text = skills.instructions(self.skill, language).strip() if self.skill else ""
        if self.custom:
            text += "\nYour own rules:\n" + "\n".join(f"- {r['id']}: {r['description']}" for r in self.custom)
        return text or "Report ambiguous, vague, compound, untestable and not measurable requirements."

    def checks(self, text, kind, lang):
        """Deterministic checks (BR-08), on top of what the model reports."""
        issues = []
        stems = [str(w).strip() for w in self.vague.get(lang, []) if str(w).strip()]
        found = None
        for w in stems:
            m = re.search(r"(?<!\w)" + re.escape(w) + r"\w*", text, flags=re.I)
            if m:
                found = m.group(0)
                break
        if found:
            issues.append({"rule": "vague", "message": (f"Нечёткое слово «{found}» — чем его измерить?" if lang == "ru"
                                                       else f"Vague word “{found}”: how would it be measured?")})
        if kind == "nfr" and QUANTITATIVE.search(text) and not NUMBER_WORDS.search(text):
            issues.append({"rule": "not_measurable", "message": ("Нет измеримого критерия (числа или порога)." if lang == "ru"
                                                                else "No measurable criterion (a number or threshold).")})
        return issues

    def merge(self, *lists):
        seen, out = set(), []
        for lst in lists:
            for issue in lst or []:
                if issue.get("rule") in self.rule_ids and issue["rule"] not in seen:
                    seen.add(issue["rule"])
                    out.append({"rule": issue["rule"], "message": str(issue.get("message") or "").strip()})
        return out


def rule_checks(text, kind, lang):
    return Quality().checks(text, kind, lang)


# ── document structure (from the frd skill) ──────────────────────────────────

def section_spec(skill, lang):
    """[(key, title, instructions)] in the skill's order."""
    return [(s["key"], skills.title_text(s.get("title"), lang), str(s.get("instructions") or "").strip())
            for s in skill.meta.get("sections") or []]


def _extra_contract(spec):
    custom = [(k, t, i) for k, t, i in spec if k not in skills.FRD_KINDS]
    if not custom:
        return "- extra: return an empty list.\n"
    lines = "\n".join(f"  - {k} (“{t}”): {i}" for k, t, i in custom)
    return ("- extra: one entry per additional section below, with its key and its text (based only on the atoms "
            "and sources; empty text when they give nothing):\n" + lines + "\n")


def _sources(evidence):
    return [{k: e.get(k) for k in ("source_id", "source_title", "source_kind", "source_date", "segment_idx",
                                   "start", "speaker", "speaker_name", "quote")} for e in evidence]


def _snapshot(atoms, rids):
    return {a["id"]: {"statement": a["statement"], "type": a["type"], "rid": rids[a["id"]]} for a in atoms}


def _atom_lines(atoms, rids, conflicts):
    lines = []
    for a in atoms:
        note = f"  (conflicts with another requirement: {conflicts[a['id']]})" if a["id"] in conflicts else ""
        lines.append(f"{rids[a['id']]} [{a['type']}] {a['statement']}{note}")
    return lines


def _open_conflicts(store, project_id):
    out = {}
    for c in store.list_conflicts(project_id):
        if c["status"] == "open":
            out.setdefault(c["atom_a"], c["description"])
            out.setdefault(c["atom_b"], c["description"])
    return out


def _block(atom, rid, text, conflicts, issues):
    return {"id": rid, "kind": "req", "atom_id": atom["id"], "type": atom["type"], "text": text.strip(),
            "sources": _sources(atom["evidence"]), "conflict": conflicts.get(atom["id"]), "issues": issues}


def _number(sections):
    for i, sec in enumerate(sections, 1):
        sec["number"] = str(i)
        for j, sub in enumerate(sec.get("subsections") or [], 1):
            sub["number"] = f"{i}.{j}"
    return sections


def _assemble(spec, lang, parts):
    """Sections in the skill's order. parts: purpose, context, assumptions, groups, nfr, out_of_scope,
    questions, extra {key: text}."""
    sections = []
    for key, title, _instr in spec:
        sec = {"key": key, "title": title, "blocks": []}
        if key == "purpose" and parts["purpose"].strip():
            sec["blocks"] = [{"id": "purpose", "kind": "text", "text": parts["purpose"].strip()}]
        elif key == "context":
            if parts["context"].strip():
                sec["blocks"].append({"id": "context", "kind": "text", "text": parts["context"].strip()})
            items = [a.strip() for a in parts["assumptions"] if a.strip()]
            if items:
                sec["blocks"].append({"id": "assumptions", "kind": "list", "title": LABELS[lang]["assumptions"],
                                      "items": items})
        elif key == "functional":
            sec["subsections"] = [{"key": f"functional.{i}", "title": t, "blocks": b}
                                  for i, (t, b) in enumerate(parts["groups"], 1) if b]
        elif key == "nfr":
            sec["blocks"] = parts["nfr"]
        elif key == "out_of_scope" and parts["out_of_scope"]:
            sec["blocks"] = [{"id": "out_of_scope", "kind": "list", "items": parts["out_of_scope"]}]
        elif key == "questions":
            sec["blocks"] = parts["questions"]
        elif key not in skills.FRD_KINDS and (parts["extra"].get(key) or "").strip():
            sec["blocks"] = [{"id": key, "kind": "text", "text": parts["extra"][key].strip()}]
        sections.append(sec)
    return {"sections": _number(sections)}


def req_blocks(content):
    """Every requirement block of a version, with the number of the (sub)section holding it."""
    for sec in content["sections"]:
        for b in sec["blocks"]:
            if b["kind"] == "req":
                yield sec["number"], sec["key"], b
        for sub in sec.get("subsections") or []:
            for b in sub["blocks"]:
                yield sub["number"], sub["key"], b


# ── building ─────────────────────────────────────────────────────────────────

def build(store, project_id, prefs, api_key, ollama_url, mode="changed", progress=None, complete=complete_json,
          skillset=None, save=True):
    """Build a new version. mode "changed": rewrite only new/changed atoms; "full": rewrite everything.
    save=False returns the content without storing a version (used to try a skill)."""
    report = progress or (lambda pct, msg: None)
    project = store.get_project(project_id)
    doc = store.document(project_id)
    atoms = store.list_atoms(project_id, status="accepted")
    if not atoms:
        raise BuildError("There are no accepted atoms yet. Review the atoms first.")
    prefs = for_project(prefs, project)
    skillset = skillset or skills.resolve()
    rids = store.requirement_ids(project_id, atoms)
    order = {"FR": 0, "NFR": 1, "Q": 2}
    atoms.sort(key=lambda a: (order[rids[a["id"]].split("-")[0]], int(rids[a["id"]].split("-")[1])))
    by_rid = {rids[a["id"]]: a for a in atoms}
    conflicts = _open_conflicts(store, project_id)
    lang = language_of([a["statement"] for a in atoms])
    ctx = {"store": store, "project": project, "atoms": atoms, "rids": rids, "by_rid": by_rid, "conflicts": conflicts,
           "lang": lang, "prefs": prefs, "api_key": api_key, "ollama_url": ollama_url, "report": report,
           "complete": complete, "skillset": skillset, "quality": Quality(skillset.get("quality")),
           "spec": section_spec(skillset["frd"], lang)}
    previous = store.version(doc["id"])
    if previous is None or mode == "full":
        content = _build_full(ctx)
        mode = "full"
    else:
        content = _build_changed(ctx, previous)
    content["language"] = lang
    content["skills"] = {"frd": skillset["frd"].name, "quality": skillset["quality"].name}
    content["rule_titles"] = ctx["quality"].titles
    if not save:
        report(100, "Done")
        return {"content": content, "atoms": len(atoms), "mode": mode}
    number = store.add_version(doc["id"], content, _snapshot(atoms, rids), len(atoms),
                               provider=prefs["llm_provider"], model=model_name(prefs), mode=mode)
    report(100, "Done")
    return {"document_id": doc["id"], "version": number, "atoms": len(atoms), "mode": mode,
            "conflicts": sum(1 for a in atoms if a["id"] in conflicts)}


def _sources_line(store, project_id):
    lines = [f"- {s['title']} ({s['kind']})" for s in store.list_sources(project_id) if s["status"] == "ready"]
    return "\n".join(lines[:40])


def _system(ctx, contract):
    lang = _lang_name(ctx["lang"])
    return skills.compose(ctx["skillset"], "frd", contract.replace("{language}", lang), language=lang)


def _model_issues(reply):
    out = {}
    for issue in reply.get("issues") or []:
        out.setdefault(str(issue.get("id", "")).strip(), []).append(issue)
    return out


def _build_full(ctx):
    ctx["report"](5, "Writing the document…")
    q, by_rid, lang = ctx["quality"], ctx["by_rid"], ctx["lang"]
    contract = FULL_CONTRACT.replace("{extra}", _extra_contract(ctx["spec"])).replace("{rules}", q.prompt(_lang_name(lang)))
    user = (f"Project: {ctx['project']['name']}\n\nSources:\n{_sources_line(ctx['store'], ctx['project']['id'])}\n\n"
            "Accepted requirement atoms:\n" + "\n".join(_atom_lines(ctx["atoms"], ctx["rids"], ctx["conflicts"])))
    custom = [(k, t) for k, t, _i in ctx["spec"] if k not in skills.FRD_KINDS]
    reply = ctx["complete"](_system(ctx, contract), user, full_schema(q.rule_ids, [k for k, _t in custom]),
                            ctx["prefs"], ctx["api_key"], ctx["ollama_url"])
    ctx["report"](85, "Checking quality…")
    texts = {str(i.get("id", "")).strip(): i["text"] for i in reply.get("items") or []
             if str(i.get("id", "")).strip() in by_rid and str(i.get("text", "")).strip()}
    model_issues = _model_issues(reply)

    def block(rid):
        atom = by_rid[rid]
        text = texts.get(rid) or atom["statement"]
        return _block(atom, rid, text, ctx["conflicts"], q.merge(
            model_issues.get(rid), q.checks(text, atom["type"], lang) if atom["type"] != "question" else []))

    frs = [r for r in by_rid if r.startswith("FR-")]
    placed, groups = set(), []
    for g in reply.get("groups") or []:
        ids = [str(i).strip() for i in g.get("ids") or []]
        ids = [i for i in ids if i in by_rid and i.startswith("FR-") and i not in placed]
        placed.update(ids)
        if ids and str(g.get("title", "")).strip():
            groups.append((g["title"].strip(), [block(r) for r in ids]))
    missing = [r for r in frs if r not in placed]
    if missing:                                   # the model skipped some: never drop a requirement
        groups.append((LABELS[lang]["other"], [block(r) for r in missing]))
    # Match by key; models sometimes answer with the section's title instead.
    by_title = {t.strip().casefold(): k for k, t in custom}
    extra = {}
    for e in reply.get("extra") or []:
        raw = str(e.get("key", "")).strip()
        k = raw if raw in dict(custom) else by_title.get(raw.casefold())
        if k and str(e.get("text") or "").strip():
            extra[k] = e["text"]
    return _assemble(ctx["spec"], lang, {
        "purpose": reply.get("purpose") or "", "context": reply.get("context") or "",
        "assumptions": reply.get("assumptions") or [], "groups": groups,
        "nfr": [block(r) for r in by_rid if r.startswith("NFR-")],
        "out_of_scope": [x.strip() for x in reply.get("out_of_scope") or [] if str(x).strip()],
        "questions": [block(r) for r in by_rid if r.startswith("Q-")], "extra": extra})


def _build_changed(ctx, previous):
    snap, rids, by_rid, lang, q = previous["snapshot"], ctx["rids"], ctx["by_rid"], ctx["lang"], ctx["quality"]
    old = {b["id"]: (num, key, b) for num, key, b in req_blocks(previous["content"])}
    sections = {s["key"]: s for s in previous["content"]["sections"]}
    functional = sections.get("functional", {"subsections": []})
    group_titles = [sub["title"] for sub in functional.get("subsections") or []]
    old_group = {b["id"]: sub["title"] for sub in functional.get("subsections") or [] for b in sub["blocks"]}

    def unchanged(atom):
        s = snap.get(atom["id"])
        return s is not None and s["statement"] == atom["statement"] and s["type"] == atom["type"] \
            and s["rid"] == rids[atom["id"]] and rids[atom["id"]] in old

    to_write = [a for a in ctx["atoms"] if not unchanged(a)]
    removed = [aid for aid in snap if aid not in {a["id"] for a in ctx["atoms"]}]
    if not to_write and not removed:
        raise BuildError("The document is up to date: no atoms changed since the last version.")
    reply = {"items": [], "issues": []}
    if to_write:
        ctx["report"](10, f"Rewriting {len(to_write)} changed requirement(s)…")
        contract = CHANGED_CONTRACT.replace("{rules}", q.prompt(_lang_name(lang)))
        user = ("Existing functional sub-sections:\n" + ("\n".join(f"- {t}" for t in group_titles) or "(none)") +
                "\n\nTo write:\n" + "\n".join(_atom_lines(to_write, rids, ctx["conflicts"])))
        reply = ctx["complete"](_system(ctx, contract), user, changed_schema(q.rule_ids), ctx["prefs"],
                                ctx["api_key"], ctx["ollama_url"])
    ctx["report"](85, "Checking quality…")
    written = {str(i.get("id", "")).strip(): i for i in reply.get("items") or [] if str(i.get("id", "")).strip() in by_rid}
    model_issues = _model_issues(reply)

    def block(rid):
        atom = by_rid[rid]
        if unchanged(atom):
            prev = dict(old[rid][2])
            prev.update(sources=_sources(atom["evidence"]), conflict=ctx["conflicts"].get(atom["id"]))
            return prev
        text = str((written.get(rid) or {}).get("text", "")).strip() or atom["statement"]
        return _block(atom, rid, text, ctx["conflicts"], q.merge(
            model_issues.get(rid), q.checks(text, atom["type"], lang) if atom["type"] != "question" else []))

    groups = {t: [] for t in group_titles}
    for rid in (r for r in by_rid if r.startswith("FR-")):
        if unchanged(by_rid[rid]) and rid in old_group:
            title = old_group[rid]
        else:
            title = str((written.get(rid) or {}).get("group", "")).strip() or old_group.get(rid) or LABELS[lang]["other"]
        groups.setdefault(title, []).append(block(rid))

    def text_of(key):
        sec = sections.get(key)
        return next((b["text"] for b in sec["blocks"] if b["kind"] == "text"), "") if sec else ""

    def list_of(key):
        sec = sections.get(key)
        return next((b["items"] for b in sec["blocks"] if b["kind"] == "list"), []) if sec else []
    extra = {k: text_of(k) for k, _t, _i in ctx["spec"] if k not in skills.FRD_KINDS}
    return _assemble(ctx["spec"], lang, {
        "purpose": text_of("purpose"), "context": text_of("context"), "assumptions": list_of("context"),
        "groups": list(groups.items()), "nfr": [block(r) for r in by_rid if r.startswith("NFR-")],
        "out_of_scope": list_of("out_of_scope"), "questions": [block(r) for r in by_rid if r.startswith("Q-")],
        "extra": extra})


def staleness(store, project_id, version):
    """What changed since the version was built (FR-DOC-05 AC1), per (sub)section."""
    if version is None:
        return None
    snap = version["snapshot"]
    current = {a["id"]: a for a in store.list_atoms(project_id, status="accepted")}
    where = {b["atom_id"]: num for num, _key, b in req_blocks(version["content"])}
    changed = [aid for aid, s in snap.items() if aid in current and
               (current[aid]["statement"] != s["statement"] or current[aid]["type"] != s["type"])]
    removed = [aid for aid in snap if aid not in current]
    added = [aid for aid in current if aid not in snap]
    sections = {}
    for aid in changed + removed:
        num = where.get(aid)
        if num:
            sections[num] = sections.get(num, 0) + 1
    return {"stale": bool(changed or removed or added), "changed": len(changed), "removed": len(removed),
            "added": len(added), "sections": sections, "atom_ids": changed + removed + added}


def diff(old, new):
    """Block-level differences between two versions (FR-DOC-02 AC2)."""
    def blocks(content):
        out = {}
        for sec in content["sections"]:
            for b in sec["blocks"]:
                out[b["id"]] = (sec["number"], b)
            for sub in sec.get("subsections") or []:
                for b in sub["blocks"]:
                    out[b["id"]] = (sub["number"], b)
        return out

    def text(b):
        return b.get("text") or "\n".join(b.get("items") or [])
    a, b = blocks(old["content"]), blocks(new["content"])
    changes = []
    for bid, (num, blk) in b.items():
        if bid not in a:
            changes.append({"id": bid, "section": num, "change": "added", "new": text(blk)})
        elif text(a[bid][1]) != text(blk) or a[bid][0] != num:
            changes.append({"id": bid, "section": num, "change": "changed", "old": text(a[bid][1]), "new": text(blk),
                            "moved_from": a[bid][0] if a[bid][0] != num else None})
    for bid, (num, blk) in a.items():
        if bid not in b:
            changes.append({"id": bid, "section": num, "change": "removed", "old": text(blk)})
    return changes


def suggest_fix(store, project_id, atom_id, rule, message, prefs, api_key, ollama_url, complete=complete_json,
                skillset=None):
    """A rewrite of the atom that fixes a quality finding; the BA accepts, edits or dismisses it (FR-DOC-06 AC2)."""
    atom = store.get_atom(atom_id)
    prefs = for_project(prefs, store.get_project(project_id))
    lang = _lang_name(language_of([atom["statement"]]))
    system = skills.compose(skillset or skills.resolve(), "fix", FIX_CONTRACT, language=lang)
    user = f"Requirement ({atom['type']}): {atom['statement']}\n\nProblem ({rule}): {message}"
    reply = complete(system, user, FIX_SCHEMA, prefs, api_key, ollama_url)
    statement = (reply.get("statement") or "").strip()
    if not statement:
        raise LLMError("The model returned an empty suggestion; try again.")
    return {"atom_id": atom_id, "rule": rule, "statement": statement}
