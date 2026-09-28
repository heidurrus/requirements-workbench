"""Skills: editable, shareable instructions for every AI stage (spec FR-SET-04, D-13).

A skill is a folder with a SKILL.md: YAML frontmatter (name, title, description,
stage, and stage-specific settings) followed by the instructions in Markdown —
the same shape as Anthropic's Agent Skills. Built-in skills ship with the app
and are read-only; the user's own live in the app data folder, where they can be
edited in the app or in any editor, versioned, exported and imported as .zip.

The skill says *what* to write and *how*. The app adds a short fixed "contract"
(output shape and safety rules like "quote verbatim", "never invent facts"), so
no edit can break the pipeline. "House rules" (stage `global`) are appended to
every stage.
"""
import io
import json
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field

import yaml

from core.paths import app_data_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STAGES = ["global", "summary", "extract", "dedup", "frd", "quality", "fix", "export", "decompose", "invest"]
DEFAULTS = {"global": "house-rules", "summary": "summarize-source", "extract": "extract-requirements",
            "dedup": "find-duplicates", "frd": "write-frd", "quality": "quality-check",
            "fix": "fix-requirement", "export": "export-standard", "decompose": "split-into-stories",
            "invest": "invest-check"}
FRD_KINDS = {"purpose", "context", "functional", "nfr", "out_of_scope", "questions"}
FRD_REQUIRED = {"functional", "nfr", "questions"}            # requirements must always have a home
BUILTIN_RULES = ["not_measurable", "vague", "ambiguous", "compound", "untestable"]
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
ALLOWED_FILES = {".md", ".txt", ".docx", ".yaml", ".yml", ".json", ".csv"}
MAX_IMPORT_BYTES = 20 * 1024 * 1024
MAX_IMPORT_FILES = 60


class SkillError(ValueError):
    """A user-facing problem with a skill."""


@dataclass
class Skill:
    name: str
    title: str
    description: str
    stage: str
    instructions: str
    meta: dict = field(default_factory=dict)
    builtin: bool = False
    path: str = ""
    error: str = None
    version: int = 1

    def summary(self):
        return {"name": self.name, "title": self.title, "description": self.description, "stage": self.stage,
                "builtin": self.builtin, "error": self.error, "version": self.version}

    def full(self):
        return {**self.summary(), "instructions": self.instructions, "meta": self.settings(),
                "path": None if self.builtin else self.path}

    def settings(self):
        """Stage-specific settings (everything in the frontmatter except the identity fields)."""
        return {k: v for k, v in self.meta.items() if k not in ("name", "title", "description", "stage", "version")}


# ── folders ──────────────────────────────────────────────────────────────────

def builtin_dir():
    return os.path.join(ROOT, "skills")


def custom_dir():
    path = os.path.join(app_data_dir(), "skills")
    os.makedirs(path, exist_ok=True)
    return path


def _trash_dir():
    path = os.path.join(app_data_dir(), "skills-trash")
    os.makedirs(path, exist_ok=True)
    return path


# ── parsing and validation ───────────────────────────────────────────────────

def parse(text):
    """SKILL.md → (frontmatter dict, instructions)."""
    text = text.lstrip("﻿")
    m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)(.*)$", text, flags=re.S)
    if not m:
        raise SkillError("SKILL.md must start with a header between two '---' lines")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise SkillError(f"the header is not valid YAML: {e}")
    if not isinstance(meta, dict):
        raise SkillError("the header must be a set of 'key: value' lines")
    return meta, m.group(2).strip()


def dump(meta, instructions):
    header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=110).strip()
    return f"---\n{header}\n---\n{instructions.strip()}\n"


def title_text(title, lang):
    """A title is a string or {ru: …, en: …}."""
    if isinstance(title, dict):
        return str(title.get(lang) or next(iter(title.values()), ""))
    return str(title or "")


def validate(meta, instructions, folder=None):
    """Raise SkillError with every problem found, in one message."""
    errors = []
    name, stage = meta.get("name"), meta.get("stage")
    if not isinstance(name, str) or not NAME_RE.match(name):
        errors.append("name: 2–63 characters, lowercase latin letters, digits and '-'")
    if stage not in STAGES:
        errors.append(f"stage: one of {', '.join(STAGES)}")
    if not str(meta.get("title") or "").strip():
        errors.append("title: must not be empty")
    if stage not in ("global", "export") and not instructions.strip():
        errors.append("the instructions must not be empty")
    if stage == "frd":
        errors += _validate_sections(meta.get("sections"))
    if stage == "quality":
        errors += _validate_quality(meta)
    if stage == "export":
        tpl = meta.get("template")
        if tpl not in ("builtin:neutral", "builtin:gost") and not (
                tpl == "template.docx" and folder and os.path.isfile(os.path.join(folder, "template.docx"))):
            errors.append("template: 'template.docx' in the skill folder (or a built-in template)")
        if meta.get("numbering", "dot") not in ("dot", "plain"):
            errors.append("numbering: 'dot' (1.2.) or 'plain' (1.2)")
    if errors:
        raise SkillError("; ".join(errors))


def _validate_sections(sections):
    if not isinstance(sections, list) or not sections:
        return ["sections: a list of document sections"]
    errors, keys = [], set()
    for i, sec in enumerate(sections, 1):
        if not isinstance(sec, dict):
            errors.append(f"section {i}: must have key and title")
            continue
        key = sec.get("key")
        if not isinstance(key, str) or not KEY_RE.match(key):
            errors.append(f"section {i}: key must be lowercase latin letters, digits, '_'")
            continue
        if key in keys:
            errors.append(f"section {i}: key '{key}' is used twice")
        keys.add(key)
        if not title_text(sec.get("title"), "ru").strip():
            errors.append(f"section '{key}': title must not be empty")
        if key not in FRD_KINDS and not str(sec.get("instructions") or "").strip():
            errors.append(f"section '{key}': say what the AI should write there (instructions)")
    missing = FRD_REQUIRED - keys
    if missing:
        errors.append("sections must include " + ", ".join(sorted(missing)) + " (requirements must have a place)")
    return errors


def _validate_quality(meta):
    errors = []
    words = meta.get("vague_words", {})
    if not isinstance(words, dict) or any(not isinstance(v, list) for v in words.values()):
        errors.append("vague_words: lists per language, e.g. ru: [быстр, удобн]")
    rules = meta.get("rules", [])
    if not isinstance(rules, list):
        errors.append("rules: a list of your own checks")
    else:
        seen = set()
        for r in rules:
            rid = r.get("id") if isinstance(r, dict) else None
            if not isinstance(rid, str) or not KEY_RE.match(rid) or rid in BUILTIN_RULES or rid in seen:
                errors.append("each rule needs a unique id (lowercase latin, digits, '_')")
                continue
            seen.add(rid)
            if not str(r.get("title") or "").strip() or not str(r.get("description") or "").strip():
                errors.append(f"rule '{rid}': needs a title and a description")
    return errors


def _load(folder, builtin):
    path = os.path.join(folder, "SKILL.md")
    fallback = os.path.basename(folder)
    try:
        with open(path, encoding="utf-8") as f:
            meta, body = parse(f.read())
        validate(meta, body, folder)
        if meta["name"] != fallback:
            raise SkillError(f"name '{meta['name']}' must match the folder name '{fallback}'")
        return Skill(meta["name"], str(meta["title"]), str(meta.get("description") or ""), meta["stage"], body,
                     meta, builtin, folder, None, int(meta.get("version") or 1))
    except (OSError, SkillError, ValueError, TypeError) as e:
        return Skill(fallback, fallback, "", "", "", {}, builtin, folder, str(e))


def all_skills():
    """Built-in first, then the user's own; broken ones are listed with their error (FR-SET-04 AC3)."""
    out = []
    for base, builtin in ((builtin_dir(), True), (custom_dir(), False)):
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            folder = os.path.join(base, entry)
            if os.path.isdir(folder) and os.path.isfile(os.path.join(folder, "SKILL.md")):
                out.append(_load(folder, builtin))
    return out


def get(name):
    for s in all_skills():                 # built-ins come first, so they win a name clash
        if s.name == name:
            return s
    raise SkillError(f"skill '{name}' not found")


def _custom(name):
    s = get(name)
    if s.builtin:
        raise SkillError("built-in skills can't be changed: make a copy first")
    return s


# ── the user's own skills ────────────────────────────────────────────────────

def _unique_name(base):
    base = re.sub(r"[^a-z0-9-]+", "-", base.lower()).strip("-")[:50] or "skill"
    if len(base) < 2:
        base = f"skill-{base}"
    taken = {s.name for s in all_skills()}
    name, n = base, 2
    while name in taken:
        name, n = f"{base}-{n}", n + 1
    return name


def _write(folder, meta, instructions):
    tmp = os.path.join(folder, "SKILL.md.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dump(meta, instructions))
    os.replace(tmp, os.path.join(folder, "SKILL.md"))


def create(from_name, title=None, name=None):
    """A new skill of your own, copied from any skill (built-in or yours)."""
    src = get(from_name)
    if src.error:
        raise SkillError(f"'{from_name}' has an error and can't be copied: {src.error}")
    new = _unique_name(name or f"{src.name}-copy")
    folder = os.path.join(custom_dir(), new)
    shutil.copytree(src.path, folder, ignore=shutil.ignore_patterns(".history", "*.tmp"))
    meta = dict(src.meta)
    meta.update(name=new, title=(title or f"{src.title} (копия)").strip(), version=1)
    if src.stage == "export" and str(meta.get("template", "")).startswith("builtin:"):
        from core import docx_export             # the built-in look becomes an editable Word file
        with open(os.path.join(folder, "template.docx"), "wb") as f:
            f.write(docx_export.starter(meta["template"].split(":", 1)[1]))
        meta["template"] = "template.docx"
    _write(folder, meta, src.instructions)
    return get(new)


def _snapshot(skill, suffix="md"):
    hist = os.path.join(skill.path, ".history")
    os.makedirs(hist, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
    src = os.path.join(skill.path, "SKILL.md" if suffix == "md" else "template.docx")
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(hist, f"{stamp}.{suffix}"))


def save(name, title=None, description=None, instructions=None, settings=None):
    """Update your own skill; the previous version goes to its history."""
    skill = _custom(name)
    meta = dict(skill.meta) if not skill.error else {"name": name}
    if title is not None:
        meta["title"] = title.strip()
    if description is not None:
        meta["description"] = description.strip()
    for key, value in (settings or {}).items():
        if key in ("name", "stage", "version"):
            continue
        meta[key] = value
    meta["version"] = int(meta.get("version") or 1) + 1
    body = skill.instructions if instructions is None else instructions
    validate(meta, body, skill.path)
    _snapshot(skill)
    _write(skill.path, meta, body)
    return get(name)


def history(name):
    skill = _custom(name)
    hist = os.path.join(skill.path, ".history")
    if not os.path.isdir(hist):
        return []
    out = []
    for fn in sorted(os.listdir(hist), reverse=True):
        stamp, _, ext = fn.rpartition(".")
        if ext in ("md", "docx"):
            out.append({"id": fn, "kind": "template" if ext == "docx" else "text",
                        "at": time.mktime(time.strptime(stamp[:15], "%Y%m%d-%H%M%S"))})
    return out


def history_text(name, entry):
    skill = _custom(name)
    path = _history_path(skill, entry)
    if not entry.endswith(".md"):
        raise SkillError("only text versions can be shown")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _history_path(skill, entry):
    if not re.match(r"^[0-9-]+\.(md|docx)$", entry or ""):
        raise SkillError("version not found")
    path = os.path.join(skill.path, ".history", entry)
    if not os.path.isfile(path):
        raise SkillError("version not found")
    return path


def restore(name, entry):
    """Bring back an earlier version (the current one is kept in history too)."""
    skill = _custom(name)
    path = _history_path(skill, entry)
    if entry.endswith(".md"):
        with open(path, encoding="utf-8") as f:
            meta, body = parse(f.read())
        meta["name"] = name
        validate(meta, body, skill.path)
        _snapshot(skill)
        meta["version"] = int(skill.version) + 1
        _write(skill.path, meta, body)
    else:
        _snapshot(skill, "docx")
        shutil.copy2(path, os.path.join(skill.path, "template.docx"))
    return get(name)


def delete(name):
    """Move your skill to a trash folder (recoverable with undelete)."""
    skill = _custom(name)
    dest = os.path.join(_trash_dir(), name)
    shutil.rmtree(dest, ignore_errors=True)
    shutil.move(skill.path, dest)


def undelete(name):
    src = os.path.join(_trash_dir(), name)
    if not os.path.isdir(src):
        raise SkillError("nothing to restore")
    if any(s.name == name for s in all_skills()):
        raise SkillError(f"a skill named '{name}' exists again")
    shutil.move(src, os.path.join(custom_dir(), name))
    return get(name)


def set_template(name, data):
    """Replace the Word template of your export skill (previous one kept in history)."""
    skill = _custom(name)
    if skill.stage != "export":
        raise SkillError("only export skills have a Word template")
    check_docx(data)
    _snapshot(skill, "docx")
    tmp = os.path.join(skill.path, "template.docx.tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, os.path.join(skill.path, "template.docx"))
    if skill.meta.get("template") != "template.docx":
        save(name, settings={"template": "template.docx"})
    return get(name)


def check_docx(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if "word/document.xml" not in z.namelist():
                raise SkillError("this is not a Word document (.docx)")
    except zipfile.BadZipFile:
        raise SkillError("this is not a Word document (.docx)")


def template_bytes(skill):
    tpl = skill.meta.get("template", "builtin:neutral")
    if str(tpl).startswith("builtin:"):
        from core import docx_export
        return docx_export.starter(tpl.split(":", 1)[1])
    with open(os.path.join(skill.path, "template.docx"), "rb") as f:
        return f.read()


def template_path(name):
    skill = _custom(name)
    return os.path.join(skill.path, "template.docx")


# ── sharing ──────────────────────────────────────────────────────────────────

def export_zip(name):
    skill = get(name)
    builtin_look = skill.stage == "export" and str(skill.meta.get("template", "")).startswith("builtin:")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(skill.path):
            dirs[:] = [d for d in dirs if d != ".history" and not d.startswith(".")]
            for fn in files:
                if fn.endswith(".tmp") or fn.startswith(".") or (builtin_look and fn == "SKILL.md"):
                    continue
                full = os.path.join(folder, fn)
                z.write(full, os.path.join(skill.name, os.path.relpath(full, skill.path)))
        if builtin_look:
            meta = dict(skill.meta, template="template.docx")          # share the look as a real file
            z.writestr(f"{skill.name}/SKILL.md", dump(meta, skill.instructions))
            z.writestr(f"{skill.name}/template.docx", template_bytes(skill))
    return buf.getvalue()


def import_file(filename, data):
    """Import a skill from a .zip (a folder with SKILL.md) or a single SKILL.md file."""
    if len(data) > MAX_IMPORT_BYTES:
        raise SkillError("the file is too large for a skill (20 MB at most)")
    if filename.lower().endswith(".md"):
        files = {"SKILL.md": data}
    else:
        files = _read_zip(data)
    try:
        meta, body = parse(files["SKILL.md"].decode("utf-8"))
    except UnicodeDecodeError:
        raise SkillError("SKILL.md must be UTF-8 text")
    if meta.get("stage") not in STAGES:
        raise SkillError(f"stage: one of {', '.join(STAGES)}")
    name = _unique_name(str(meta.get("name") or os.path.splitext(filename)[0]))
    meta["name"] = name
    staging = os.path.join(custom_dir(), f".import-{name}")
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging)
    try:
        for rel, content in files.items():
            dest = os.path.join(staging, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(content)
        if "template.docx" in files:
            check_docx(files["template.docx"])
        validate(meta, body, staging)
        _write(staging, meta, body)
        os.replace(staging, os.path.join(custom_dir(), name))
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return get(name)


def _read_zip(data):
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise SkillError("not a .zip file")
    entries = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")
               and not os.path.basename(i.filename).startswith(".")]
    if len(entries) > MAX_IMPORT_FILES:
        raise SkillError("too many files in the archive for a skill")
    if sum(i.file_size for i in entries) > MAX_IMPORT_BYTES:
        raise SkillError("the archive is too large for a skill (20 MB at most)")
    skill_md = [i.filename for i in entries if os.path.basename(i.filename) == "SKILL.md"]
    if not skill_md:
        raise SkillError("the archive has no SKILL.md")
    root = min(skill_md, key=lambda p: p.count("/")).rpartition("/")[0]
    files = {}
    for info in entries:
        name = info.filename
        if root:
            if not name.startswith(root + "/"):
                continue
            name = name[len(root) + 1:]
        parts = name.split("/")
        if name.startswith("/") or ".." in parts or ":" in name or "\\" in name:
            raise SkillError("the archive contains unsafe paths")
        if os.path.splitext(name)[1].lower() not in ALLOWED_FILES:
            continue                                           # skip scripts, binaries, anything unexpected
        files[name] = z.read(info)
    return files


# ── which skill is active ────────────────────────────────────────────────────

def _choices_file():
    return os.path.join(app_data_dir(), "skills.json")


def global_choices():
    try:
        with open(_choices_file(), encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if k in STAGES and isinstance(v, str)}
    except (OSError, ValueError):
        return {}


def set_global(stage, name):
    if stage not in STAGES:
        raise SkillError("unknown stage")
    skill = get(name)
    if skill.stage != stage or skill.error:
        raise SkillError(f"'{name}' is not a working {stage} skill")
    data = global_choices()
    data[stage] = name
    tmp = _choices_file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _choices_file())


def resolve(project_overrides=None):
    """{stage: Skill} in effect: project override → global choice → built-in default.
    A missing or broken choice falls back to the default, so work never stops."""
    by_name = {}
    for s in all_skills():
        if not s.error:
            by_name.setdefault(s.name, s)
    chosen = {**global_choices(), **(project_overrides or {})}
    out = {}
    for stage in STAGES:
        skill = by_name.get(chosen.get(stage))
        if skill is None or skill.stage != stage:
            skill = by_name.get(DEFAULTS[stage])
        out[stage] = skill
    return out


# ── prompts ──────────────────────────────────────────────────────────────────

def instructions(skill, language=None):
    text = skill.instructions if skill else ""
    return text.replace("{language}", language) if language else text


def compose(skillset, stage, contract="", language=None):
    """System prompt = the stage's skill + the app's contract + house rules."""
    parts = [instructions(skillset.get(stage), language).strip()]
    if contract.strip():
        parts.append("## Format (set by the app, always follow)\n" + contract.strip())
    house = instructions(skillset.get("global"), language).strip()
    if house:
        parts.append("## House rules (apply to everything)\n" + house)
    return "\n\n".join(p for p in parts if p)
