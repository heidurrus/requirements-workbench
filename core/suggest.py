"""Steer by review (PM review, bet 4.3): turn repeated review decisions into skill rules.

Deterministic: counts the BA's reject reasons and rewrites, and proposes a rule once a pattern
repeats. Applying a rule appends it to the project's own copy of the extraction skill (a built-in
skill is copied first), so it never changes other projects.
"""
from collections import Counter

from core import skills

MIN_REPEATS = 5
RULES = {
    "ru": {
        "not_requirement": "Не выделяй как требования высказывания такого рода (аналитик отклонил их как «не требование»):",
        "out_of_scope": "Это вне рамок проекта; не выделяй такие требования:",
        "rewrite": "Формулируй требования так: «{new} …», а не «{old} …».",
        "title": "Правило из ревью",
    },
    "en": {
        "not_requirement": "Do not extract statements like these as requirements (the analyst rejected them as not requirements):",
        "out_of_scope": "These are out of the project's scope; do not extract such requirements:",
        "rewrite": "Word requirements as “{new} …”, not “{old} …”.",
        "title": "Rule from review",
    },
}


def _lead(text, n=2):
    return " ".join(text.split()[:n]).rstrip(",:;").strip()


def suggestions(store, project_id, lang="ru"):
    t = RULES.get(lang, RULES["ru"])
    atoms = store.list_atoms(project_id)
    out = []
    for reason in ("not_requirement", "out_of_scope"):
        hits = [a for a in atoms if a["status"] == "rejected" and a.get("reject_reason") == reason]
        if len(hits) >= MIN_REPEATS:
            examples = [a["statement"] for a in hits[:6]]
            out.append({"id": f"reject:{reason}", "kind": "reject", "reason": reason, "count": len(hits),
                        "rule": t[reason] + "\n" + "\n".join(f"- {x}" for x in examples)})
    pairs = Counter()
    for a in atoms:
        if a["statement"] != a["original_statement"]:
            old, new = _lead(a["original_statement"]), _lead(a["statement"])
            if old and new and old.casefold() != new.casefold():
                pairs[(old, new)] += 1
    for (old, new), n in pairs.most_common(3):
        if n >= MIN_REPEATS:
            out.append({"id": f"rewrite:{old}→{new}", "kind": "rewrite", "count": n, "old": old, "new": new,
                        "rule": t["rewrite"].format(old=old, new=new)})
    return out


def apply(store, project_id, rule, lang="ru"):
    """Append the rule to the project's extraction skill; returns the skill name now in effect."""
    project = store.get_project(project_id)
    current = skills.resolve(store.project_skills(project_id))["extract"]
    if current.builtin:
        mine = skills.create(current.name, title=f"{current.title} · {project['name']}")
        store.set_project_skill(project_id, "extract", mine.name)
    else:
        mine = current
    body = mine.instructions.rstrip() + f"\n\n## {RULES.get(lang, RULES['ru'])['title']}\n{rule.strip()}\n"
    skills.save(mine.name, instructions=body)
    return mine.name
