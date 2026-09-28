"""FRD builder: accepted atoms → a structured, versioned document (spec increment 3).

One requirement in the document = one accepted atom, under a stable ID (FR-n,
NFR-n, Q-n; BR-14), with its sources copied into the version for provenance
(FR-DOC-03). The model writes the prose (purpose, context, formal wording,
grouping into sub-sections) and flags quality problems; code enforces the
structure: every atom appears exactly once, nothing is invented.

"Rebuild" regenerates only what changed since the last version (Q-15, FR-DOC-05
AC2): unchanged requirements keep their text and place word for word.
"""
import re

from core.llm import LLMError, complete_json, for_project, model_name

ORDER = ["purpose", "context", "functional", "nfr", "out_of_scope", "questions"]
TITLES = {
    "ru": {"purpose": "Назначение документа", "context": "Контекст и допущения",
           "functional": "Функциональные требования", "nfr": "Нефункциональные требования",
           "out_of_scope": "Вне рамок проекта", "questions": "Открытые вопросы",
           "assumptions": "Допущения", "other": "Прочее", "empty": "В источниках не указано."},
    "en": {"purpose": "Purpose", "context": "Context and assumptions",
           "functional": "Functional requirements", "nfr": "Non-functional requirements",
           "out_of_scope": "Out of scope", "questions": "Open questions",
           "assumptions": "Assumptions", "other": "Other", "empty": "Not stated in the sources."},
}
RULES = ["not_measurable", "vague", "ambiguous", "compound", "untestable"]
SECTION_OF_TYPE = {"functional": "functional", "nfr": "nfr", "question": "questions"}

# Subjective words that make a requirement untestable (BR-08). Stems, matched at word start.
VAGUE = {
    "ru": ["быстр", "удобн", "интуитивн", "современн", "надёжн", "надежн", "дружелюбн", "оптимальн",
           "эффективн", "гибк", "масштабируем", "по возможности", "при необходимости", "и т\\.\\s?д", "как правило",
           "максимально", "минимальн\\w* время"],
    "en": ["fast", "quick", "user-friendly", "intuitive", "easy", "modern", "reliable", "efficient", "flexible",
           "scalable", "as appropriate", "if possible", "etc\\.", "robust", "seamless", "as soon as possible"],
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

FULL_SYSTEM = """You are a senior business analyst writing a Functional Requirements Document (FRD) from requirement atoms that the analyst has already reviewed and accepted. Write everything in {language}.

Rules:
- Each atom becomes exactly one requirement item with the atom's ID. Rewrite its statement as one clear, formal, testable requirement ("The system shall…" / "Система должна…"). Keep every number, limit, role and name exactly; never add facts that are not in the atom. Questions (Q-…) stay questions to the client, phrased clearly.
- Group the functional requirements (FR-…) into 2–8 sub-sections by capability, each with a short noun-phrase title. Every FR ID goes into exactly one group. (With only a few FRs, one or two groups are fine.)
- purpose: 2–4 sentences on what the system or feature is and what this document covers, based only on the atoms and the list of sources.
- context: one short paragraph on the users, their situation and the problem, as far as the atoms show it.
- assumptions: only assumptions the atoms clearly imply; may be empty.
- out_of_scope: only things the atoms explicitly exclude; otherwise empty.
- issues: check each FR and NFR item you wrote against these rules and report only real problems, with a one-sentence message: not_measurable (an NFR without a number or threshold), vague (subjective words like "fast" or "convenient"), ambiguous (can be read in more than one way), compound (several requirements in one), untestable."""

CHANGED_SYSTEM = """You are a senior business analyst updating a Functional Requirements Document (FRD). Only some requirement atoms are new or changed; everything else stays as it is. Write in {language}.

For each item listed under "To write":
- text: rewrite the atom's statement as one clear, formal, testable requirement ("The system shall…" / "Система должна…"), keeping every number, limit and name exactly and adding nothing. Questions (Q-…) stay questions to the client.
- group: for a functional requirement (FR-…), the title of the existing sub-section it belongs to, copied exactly, or a short new title if none fits. Empty for other items.
- issues: report real problems in the text you wrote: not_measurable (an NFR without a number or threshold), vague, ambiguous, compound, untestable."""

FULL_SCHEMA = {
    "type": "object",
    "properties": {
        "purpose": {"type": "string"},
        "context": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "groups": {"type": "array", "items": {
            "type": "object", "properties": {"title": {"type": "string"}, "ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["title", "ids"], "additionalProperties": False}},
        "items": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["id", "text"], "additionalProperties": False}},
        "out_of_scope": {"type": "array", "items": {"type": "string"}},
        "issues": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"}, "rule": {"type": "string", "enum": RULES},
                                             "message": {"type": "string"}},
            "required": ["id", "rule", "message"], "additionalProperties": False}},
    },
    "required": ["purpose", "context", "assumptions", "groups", "items", "out_of_scope", "issues"],
    "additionalProperties": False,
}

CHANGED_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}, "group": {"type": "string"}},
            "required": ["id", "text", "group"], "additionalProperties": False}},
        "issues": FULL_SCHEMA["properties"]["issues"],
    },
    "required": ["items", "issues"],
    "additionalProperties": False,
}

FIX_SYSTEM = """You improve one requirement of a software specification so it passes a quality check. Write in {language}.
Return the requirement rewritten as one clear, testable statement that fixes the problem named below. Keep every fact, number and name from the original; do not invent new facts. If fixing needs a value nobody has stated (for example a time limit), put a placeholder in square brackets, e.g. "[уточнить: N секунд]" or "[to confirm: N seconds]"."""

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


def rule_checks(text, kind, lang):
    """Deterministic quality rules (BR-08), on top of what the model reports."""
    issues = []
    words = [w for w in VAGUE[lang] if re.search(r"(?<!\w)" + w, text, flags=re.I)]
    if words:
        found = re.search(r"(?<!\w)(" + "|".join(words) + r")\w*", text, flags=re.I).group(0)
        issues.append({"rule": "vague", "message": (f"Нечёткое слово «{found}» — чем его измерить?" if lang == "ru"
                                                   else f"Vague word “{found}”: how would it be measured?")})
    if kind == "nfr" and QUANTITATIVE.search(text) and not NUMBER_WORDS.search(text):
        issues.append({"rule": "not_measurable", "message": ("Нет измеримого критерия (числа или порога)." if lang == "ru"
                                                            else "No measurable criterion (a number or threshold).")})
    return issues


def _merge_issues(*lists):
    seen, out = set(), []
    for lst in lists:
        for issue in lst or []:
            if issue["rule"] in RULES and issue["rule"] not in seen:
                seen.add(issue["rule"])
                out.append({"rule": issue["rule"], "message": issue["message"].strip()})
    return out


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


def _assemble(lang, purpose, context, assumptions, groups, nfr_blocks, out_of_scope, question_blocks):
    t = TITLES[lang]
    context_blocks = [{"id": "context", "kind": "text", "text": context.strip()}] if context.strip() else []
    if assumptions:
        context_blocks.append({"id": "assumptions", "kind": "list", "title": t["assumptions"],
                               "items": [a.strip() for a in assumptions if a.strip()]})
    sections = [
        {"key": "purpose", "title": t["purpose"], "blocks": [{"id": "purpose", "kind": "text", "text": purpose.strip()}]
         if purpose.strip() else []},
        {"key": "context", "title": t["context"], "blocks": context_blocks},
        {"key": "functional", "title": t["functional"], "blocks": [],
         "subsections": [{"key": f"functional.{i}", "title": title, "blocks": blocks}
                         for i, (title, blocks) in enumerate(groups, 1) if blocks]},
        {"key": "nfr", "title": t["nfr"], "blocks": nfr_blocks},
        {"key": "out_of_scope", "title": t["out_of_scope"],
         "blocks": [{"id": "out_of_scope", "kind": "list", "items": out_of_scope}] if out_of_scope else []},
        {"key": "questions", "title": t["questions"], "blocks": question_blocks},
    ]
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


def build(store, project_id, prefs, api_key, ollama_url, mode="changed", progress=None, complete=complete_json):
    """Build a new version. mode "changed": rewrite only new/changed atoms; "full": rewrite everything."""
    report = progress or (lambda pct, msg: None)
    project = store.get_project(project_id)
    doc = store.document(project_id)
    atoms = store.list_atoms(project_id, status="accepted")
    if not atoms:
        raise BuildError("There are no accepted atoms yet. Review the atoms first.")
    prefs = for_project(prefs, project)
    rids = store.requirement_ids(project_id, atoms)
    order = {"FR": 0, "NFR": 1, "Q": 2}
    atoms.sort(key=lambda a: (order[rids[a["id"]].split("-")[0]], int(rids[a["id"]].split("-")[1])))
    by_rid = {rids[a["id"]]: a for a in atoms}
    conflicts = _open_conflicts(store, project_id)
    lang = language_of([a["statement"] for a in atoms])
    previous = store.version(doc["id"])
    if previous is None or mode == "full":
        content = _build_full(store, project, atoms, rids, by_rid, conflicts, lang, prefs, api_key, ollama_url, report, complete)
        mode = "full"
    else:
        content = _build_changed(previous, atoms, rids, by_rid, conflicts, lang, prefs, api_key, ollama_url, report, complete)
    content["language"] = lang
    number = store.add_version(doc["id"], content, _snapshot(atoms, rids), len(atoms),
                               provider=prefs["llm_provider"], model=model_name(prefs), mode=mode)
    report(100, "Done")
    return {"document_id": doc["id"], "version": number, "atoms": len(atoms), "mode": mode,
            "conflicts": sum(1 for a in atoms if a["id"] in conflicts)}


def _sources_line(store, project_id):
    lines = []
    for s in store.list_sources(project_id):
        if s["status"] == "ready":
            lines.append(f"- {s['title']} ({s['kind']})")
    return "\n".join(lines[:40])


def _build_full(store, project, atoms, rids, by_rid, conflicts, lang, prefs, api_key, ollama_url, report, complete):
    report(5, "Writing the document…")
    user = (f"Project: {project['name']}\n\nSources:\n{_sources_line(store, project['id'])}\n\n"
            "Accepted requirement atoms:\n" + "\n".join(_atom_lines(atoms, rids, conflicts)))
    reply = complete(FULL_SYSTEM.format(language=_lang_name(lang)), user, FULL_SCHEMA, prefs, api_key, ollama_url)
    report(85, "Checking quality…")
    texts = {i["id"].strip(): i["text"] for i in reply.get("items") or [] if i.get("id", "").strip() in by_rid and i.get("text", "").strip()}
    model_issues = {}
    for issue in reply.get("issues") or []:
        model_issues.setdefault(issue.get("id", "").strip(), []).append(issue)

    def block(rid):
        atom = by_rid[rid]
        text = texts.get(rid) or atom["statement"]
        return _block(atom, rid, text, conflicts, _merge_issues(
            model_issues.get(rid), rule_checks(text, atom["type"], lang) if atom["type"] != "question" else []))

    frs = [r for r in by_rid if r.startswith("FR-")]
    placed, groups = set(), []
    for g in reply.get("groups") or []:
        ids = [i.strip() for i in g.get("ids") or [] if i.strip() in by_rid and i.strip().startswith("FR-") and i.strip() not in placed]
        placed.update(ids)
        if ids and g.get("title", "").strip():
            groups.append((g["title"].strip(), [block(r) for r in ids]))
    missing = [r for r in frs if r not in placed]
    if missing:                                   # the model skipped some: never drop a requirement
        groups.append((TITLES[lang]["other"], [block(r) for r in missing]))
    nfr = [block(r) for r in by_rid if r.startswith("NFR-")]
    questions = [block(r) for r in by_rid if r.startswith("Q-")]
    out_of_scope = [x.strip() for x in reply.get("out_of_scope") or [] if x.strip()]
    return _assemble(lang, reply.get("purpose") or "", reply.get("context") or "", reply.get("assumptions") or [],
                     groups, nfr, out_of_scope, questions)


def _build_changed(previous, atoms, rids, by_rid, conflicts, lang, prefs, api_key, ollama_url, report, complete):
    snap = previous["snapshot"]
    old = {b["id"]: (num, key, b) for num, key, b in req_blocks(previous["content"])}
    old_group = {}
    functional = next(s for s in previous["content"]["sections"] if s["key"] == "functional")
    group_titles = [sub["title"] for sub in functional.get("subsections") or []]
    for sub in functional.get("subsections") or []:
        for b in sub["blocks"]:
            old_group[b["id"]] = sub["title"]

    def unchanged(atom):
        s = snap.get(atom["id"])
        return s is not None and s["statement"] == atom["statement"] and s["type"] == atom["type"] \
            and s["rid"] == rids[atom["id"]] and rids[atom["id"]] in old

    to_write = [a for a in atoms if not unchanged(a)]
    removed = [aid for aid in snap if aid not in {a["id"] for a in atoms}]
    if not to_write and not removed:
        raise BuildError("The document is up to date: no atoms changed since the last version.")
    reply = {"items": [], "issues": []}
    if to_write:
        report(10, f"Rewriting {len(to_write)} changed requirement(s)…")
        user = ("Existing functional sub-sections:\n" + ("\n".join(f"- {t}" for t in group_titles) or "(none)") +
                "\n\nTo write:\n" + "\n".join(_atom_lines(to_write, rids, conflicts)))
        reply = complete(CHANGED_SYSTEM.format(language=_lang_name(lang)), user, CHANGED_SCHEMA, prefs, api_key, ollama_url)
    report(85, "Checking quality…")
    written = {i["id"].strip(): i for i in reply.get("items") or [] if i.get("id", "").strip() in by_rid}
    model_issues = {}
    for issue in reply.get("issues") or []:
        model_issues.setdefault(issue.get("id", "").strip(), []).append(issue)

    def block(rid):
        atom = by_rid[rid]
        if unchanged(atom):
            prev = dict(old[rid][2])
            prev.update(sources=_sources(atom["evidence"]), conflict=conflicts.get(atom["id"]))
            return prev
        text = (written.get(rid) or {}).get("text", "").strip() or atom["statement"]
        return _block(atom, rid, text, conflicts, _merge_issues(
            model_issues.get(rid), rule_checks(text, atom["type"], lang) if atom["type"] != "question" else []))

    groups = {t: [] for t in group_titles}
    for rid in (r for r in by_rid if r.startswith("FR-")):
        if unchanged(by_rid[rid]) and rid in old_group:
            title = old_group[rid]
        else:
            title = (written.get(rid) or {}).get("group", "").strip() or old_group.get(rid) or TITLES[lang]["other"]
        groups.setdefault(title, []).append(block(rid))
    sections = {s["key"]: s for s in previous["content"]["sections"]}

    def text_of(key):
        return next((b["text"] for b in sections[key]["blocks"] if b["kind"] == "text"), "")
    assumptions = next((b["items"] for b in sections["context"]["blocks"] if b["kind"] == "list"), [])
    out_of_scope = next((b["items"] for b in sections["out_of_scope"]["blocks"] if b["kind"] == "list"), [])
    return _assemble(lang, text_of("purpose"), text_of("context"), assumptions, list(groups.items()),
                     [block(r) for r in by_rid if r.startswith("NFR-")], out_of_scope,
                     [block(r) for r in by_rid if r.startswith("Q-")])


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


def suggest_fix(store, project_id, atom_id, rule, message, prefs, api_key, ollama_url, complete=complete_json):
    """A rewrite of the atom that fixes a quality finding; the BA accepts, edits or dismisses it (FR-DOC-06 AC2)."""
    atom = store.get_atom(atom_id)
    prefs = for_project(prefs, store.get_project(project_id))
    lang = language_of([atom["statement"]])
    user = f"Requirement ({atom['type']}): {atom['statement']}\n\nProblem ({rule}): {message}"
    reply = complete(FIX_SYSTEM.format(language=_lang_name(lang)), user, FIX_SCHEMA, prefs, api_key, ollama_url)
    statement = (reply.get("statement") or "").strip()
    if not statement:
        raise LLMError("The model returned an empty suggestion; try again.")
    return {"atom_id": atom_id, "rule": rule, "statement": statement}
