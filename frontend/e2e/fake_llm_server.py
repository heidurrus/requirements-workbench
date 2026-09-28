"""Run the app with a deterministic stand-in for the AI model (for e2e/atoms.mjs).

Usage: WORKBENCH_DATA_DIR=<tmp> python frontend/e2e/fake_llm_server.py [port]
Extraction turns every transcript line into an atom quoting that line; the
duplicate check reports the first two new atoms as conflicting.
"""
import functools
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import app as app_module  # noqa: E402
from core import atoms  # noqa: E402


def fake_complete(system, user, schema, prefs, api_key, ollama_url):
    props = schema["properties"]
    reqs = re.findall(r"^((?:FR|NFR|Q)-\d+) \[\w+\] (.+?)(?:  \(conflicts.*)?$", user, flags=re.M)
    if "epics" in props:                                         # backlog: decomposition
        frs = re.findall(r"^(FR-\d+) \(section [\d.]+\): (.+)$", user, flags=re.M)
        nfrs = re.findall(r"^(NFR-\d+) \(section", user, flags=re.M)
        return {"epics": [{"title": "Работа оператора", "goal": "Быстрее обслуживать звонки", "stories": [
            {"title": t[:60], "story": f"Как оператор, я хочу {t.lower()}, чтобы работать быстрее", "refs": [r],
             "acceptance": [{"given": "звонок поступил", "when": "оператор открывает карточку", "then": "данные видны"},
                            {"given": "номер неизвестен", "when": "звонок поступил", "then": "открыт поиск"}],
             "subtasks": ["API", "Интерфейс"]} for r, t in frs]}],
            "nfr_links": [{"id": n, "stories_for": [frs[0][0]] if frs else []} for n in nfrs]}
    if "findings" in props:                                      # backlog: INVEST
        return {"findings": [{"id": "S1", "letter": "S", "reason": "История слишком большая для спринта.",
                              "fix": "Разделить на просмотр карточки и поиск по номеру."}]}
    if "groups" in props:                                        # FRD: full build
        return {"purpose": "Документ описывает требования к карточке клиента.", "context": "Операторы колл-центра.",
                "assumptions": [], "out_of_scope": [],
                "groups": [{"title": "Карточка клиента", "ids": [r for r, _ in reqs if r.startswith("FR-")]}],
                "items": [{"id": r, "text": "Требование: " + t} for r, t in reqs], "issues": []}
    if "items" in props:                                         # FRD: rebuild of changed atoms
        return {"items": [{"id": r, "text": "Требование: " + t, "group": "Карточка клиента"} for r, t in reqs],
                "issues": []}
    if "statement" in props:                                     # FRD: quality fix
        return {"statement": "Карточка открывается не дольше [уточнить: N секунд]"}
    if "duplicates" in props:
        new = re.findall(r"^(N\d+) ", user, flags=re.M)
        return {"duplicates": [], "conflicts": [{"a": new[0], "b": new[1], "description": "Разные требования к сроку"}]
                if len(new) > 1 else []}
    found = []
    for idx, text in re.findall(r"^\[S(\d+)\] (?:\[[^\]]*\] )?(.+)$", user, flags=re.M):
        kind = "nfr" if "секунд" in text else "question" if "?" in text else "functional"
        found.append({"type": kind, "statement": "Система: " + text, "evidence": [{"segment": int(idx), "quote": text}]})
    return {"atoms": found}


app_module.extract_atoms = functools.partial(atoms.extract_atoms, complete=fake_complete)
atoms.extract_candidates = functools.partial(atoms.extract_candidates, complete=fake_complete)
app_module.frd.build = functools.partial(app_module.frd.build, complete=fake_complete)
app_module.backlog.build = functools.partial(app_module.backlog.build, complete=fake_complete)
app_module.backlog.invest = functools.partial(app_module.backlog.invest, complete=fake_complete)
app_module.frd.suggest_fix = functools.partial(app_module.frd.suggest_fix, complete=fake_complete)
app_module.settings.secret = lambda name: "fake-key"

# Jira: a fake Atlassian sign-in and an in-memory Jira project "SBX". Nothing real is ever contacted.
from core.fake_jira import FakeJira  # noqa: E402

FAKE_JIRA = FakeJira(project_key="SBX", site="https://sandbox.atlassian.net")


class FakeAuth:
    def __init__(self):
        self.ok = False

    def connected(self):
        return self.ok

    def start(self, redirect_uri):
        return redirect_uri + "?state=s&code=c"

    def finish(self, state, code):
        self.ok = True

    def disconnect(self):
        self.ok = False

    def access_token(self, force_refresh=False):
        return "fake"


app_module.jira_auth = FakeAuth()
app_module._jira_session = lambda: FAKE_JIRA

# Pretend to be another machine for screenshots: FAKE_GPU="none" or a size in GB.
if os.getenv("FAKE_GPU"):
    fake = {} if os.environ["FAKE_GPU"] == "none" else {"name": "NVIDIA GeForce RTX 2060", "backend": "Vulkan0",
                                                        "memory": int(float(os.environ["FAKE_GPU"]) * 1024 ** 3)}
    app_module.local_llm.gpu_info = lambda refresh=False: fake

if __name__ == "__main__":
    app_module.app.run(host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 5098, threaded=True)
