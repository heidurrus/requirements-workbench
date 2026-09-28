# Acting on the PM review

This file tracks how each item in [`pm-review.md`](pm-review.md) was handled. The product owner asked for the whole report to be handled without further questions, so the open questions (§6) got default answers. They are recorded here as decisions and can be overruled.

## Decisions on the open questions (§6)

| # | Question | Decision (default, can be overruled) |
|---|---|---|
| 1 | Jira identity | Each Jira issue stays tied to its **backlog item**. On a rebuild, the item carries over to its successor, matched by FR reference: stories and NFRs by their first FRD ref, epics by title or by the origin of their stories, sub-tasks by parent and title. When a requirement is removed, its issue becomes an **orphan**. The preview lists orphans and the BA decides what to do with them. The app never closes or deletes issues in Jira by itself. |
| 2 | Sign-off | The BA sets a status per FRD version: *Черновик → На согласовании → Согласовано* (draft → in review → approved). The approved version becomes the **baseline**. After that, every change against the baseline is listed as a change request, with its impact on stories and Jira. |
| 3 | Quotes in Jira | A per-project policy: **full quote / link only / nothing**. *Local only* projects default to **link only** (FRD reference and source title, no verbatim text). The Settings copy now says exactly what leaves the computer. |
| 4 | Questions | Questions get their own lifecycle: **open → asked → answered**. An answer is text plus an optional source. Recording an answer to a conflict question resolves the conflict explicitly (A, B or merged), never silently. Accepting a question now only means "keep it in the FRD". |
| 5 | Action items | The extractor no longer throws them away. They become **Поручения** (action items, with owner and due date if spoken). They are listed on Atoms and in the client follow-up, and they never go into the FRD. |
| 6 | Scale | Designed for about 1,000 atoms per project: search, group by source / FRD section / speaker, and filters saved per project. |
| 7 | Transcript editing | Allowed. The original text is kept in the audit log, the segment shows "исправлено" (corrected), and the quotes of atoms citing that segment are re-checked. |
| 8 | Priority | Atoms and stories get **MoSCoW** (Must / Should / Could / Won't). It carries into the stories and is pushed to Jira as a label (`moscow-must`, …), because the Jira priority scheme differs from site to site. |
| 9 | Consent | Before the first recording in a session, a confirmation that the participants were told. It is recorded in the audit log with a timestamp. No per-participant tracking. |
| 10 | Readers | A traceability matrix (XLSX) and a Markdown export of the FRD. Client comments can come back as an imported DOCX review. |

## Status

Legend: ✅ done · 🟡 partly done (see the note) · ⏭ deliberately not done (see the note)

| ID | Item | Status | Where |
|---|---|---|---|
| PM-01 | Rebuild silently drops Jira links | ✅ | No longer needed as a stopgap: PM-07 fixes the cause. After a rebuild, a toast says how many issues kept their link and how many were orphaned. |
| PM-02 | "Done" with open conflicts; bulk accept takes both sides | ✅ | The done state names open conflicts ("Разобрать конфликты"). Bulk "Принять" skips atoms in a conflict; "+ конфликтные" takes them too. |
| PM-03 | Staleness doesn't cascade | ✅ | `/status` chains atoms → document → backlog → Jira. Sidebar badges go amber downstream. Export shows a stale banner. `jira.local_status` counts what is pending. |
| PM-04 | Local-only projects push verbatim quotes | ✅ | Per-project "Что уходит в Jira" setting: auto / quotes / references / nothing. Auto means references for local-only projects. The Settings copy is corrected. |
| PM-05 | Recording consent reminder | ✅ | Asked once per session and logged (`/api/consent`). |
| PM-06 | Conflicts hide the list | ✅ | Collapsed by default. There is an "в конфликте" (in conflict) filter chip. |
| PM-07 | A rebuild loses Jira identity (P0) | ✅ | `Store._match_backlog` and `replace_backlog`. Tests: `test_rebuilt_backlog_updates_the_same_issues_instead_of_duplicating`. |
| PM-08 | English progress text in the RU UI | ✅ | `lib/progress.js`, hooked into `pollJob`. |
| PM-09 | "Транскрипт" is a pseudo-step | ✅ | Removed from the pipeline. Sources stays highlighted while a transcript is open. ⌘1–⌘5. |
| PM-10 | 6 s undo, Backspace deletes | ✅ | Undo lasts ≥ 10 s everywhere, and ⌘Z undoes the last action. |
| PM-11 | Jira keys not visible upstream | ✅ | Chips on backlog rows and on FRD requirements. Atoms reach their key through the FRD. |
| PM-12 | "Пересобрать" vs "Собрать заново" | ✅ | Now "Обновить изменённое (N)" (update what changed) and "Пересобрать весь документ…" (rebuild the whole document). The second one asks first and says what is kept. |
| PM-13 | Recording → nothing extracts | ✅ | A per-project "Сразу извлекать требования" (extract right away) switch, on by default. The server starts extraction; Sources follows it. |
| PM-14 | One file per drop | ✅ | Multi-file drop or pick, imported one after another into the queue. |
| PM-15 | No client follow-up | ✅ | "Письмо заказчику" (email to the client) on the "Для заказчика" tab. Once sent, its questions are marked as asked. |
| PM-16 | BA can't add an atom | ✅ | "＋ Атом" (new atom), with an optional note. It is audited as `origin: ba`. |
| PM-17 | Transcript doesn't show its atoms | ✅ | Lines are marked by atom status. Chips open the atom. |
| PM-18 | No search or grouping at scale | ✅ | Search over statements and quotes; grouping by source or speaker; filters saved per project. |
| PM-19 | Action items vanish | ✅ | Stored in `action_items`, with owner and due date when said. Listed on "Для заказчика" and included in the email. |
| PM-21 | Accepting a question closes its conflict | ✅ | Questions go open → asked → answered. Recording an answer can settle the conflict as A, B or merged. |
| PM-20 | "My project" default | ✅ | Now "Мой проект". The setup checklist asks for the real name. |
| PM-22 | Reject has no reason | ✅ | Reasons can be set per atom and in bulk. "Вне рамок" (out of scope) feeds FRD section 5. |
| PM-23 | Audit log has no UI | ✅ | A history per atom, and "С прошлого раза" (since last time) on the project home, from `/api/projects/<id>/activity`. |
| PM-24 | Orphaned Jira issues invisible | ✅ | Listed in the preview. "Разобрался" (handled) removes one from the list. The app never deletes anything in Jira. |
| PM-25 | ASR errors can't be fixed | ✅ | A line can be corrected in place. The original is kept and the edit is audited. Atoms whose quote no longer matches are flagged. |
| PM-26 | First run finds the missing AI too late | ✅ | A "Начало работы" (getting started) checklist with "Проверить" (`/api/ai/check`), plus "Вернуться: …" (back to …) in Settings. |
| PM-27 | One version per fixed finding | ✅ | "Исправить всё и обновить" (fix all and update): fixes every finding, then does one update. |
| PM-28 | No traceability report | ✅ | `traceability.xlsx`: quote → atom → FR → story → Jira. |
| PM-29 | No project home | ✅ | "Дальше: …" (next) from the pipeline state, plus "since last time", at the top of Sources. |
| PM-30 | No ETA, no notification | ✅ | An ETA in the source row. A macOS notification when a job finishes while the app is in the background. |
| PM-31 | Project can't be handed over | ✅ | Export and import a project as one `.rwproject.zip`, with audio included. |
| PM-32 | Steering needs a prompt fork | ✅ | "Уточнить…" (refine), a one-off instruction for extraction, the document and the backlog. |
| PM-33 | "Попробовать" shows output, not impact | ✅ | Trying an extraction skill shows new vs. disappearing atoms against the current ones. |
| PM-34 | No document lifecycle | ✅ | Черновик / На согласовании / Согласовано (draft / in review / approved) per version. The baseline gives a list of change requests with their Jira impact. |
| PM-35 | DOCX only; review doesn't come back | 🟡 | Markdown export, and import of a reviewed DOCX (its comments become a source tied to FR IDs). Confluence and PDF are not done: a second Atlassian surface is its own project, and PDF comes from Word. |

## Bigger bets (§4)

| Bet | Status | What shipped |
|---|---|---|
| 4.1 Change-safe delivery | 🟡 | Identity carried over by FR ref (PM-07), orphans (PM-24), baseline and change requests with Jira impact (PM-34). There is no manual "this is the same story" override yet. |
| 4.2 The client loop | 🟡 | The "Для заказчика" hub, question states, action items, the follow-up email. Matching an imported client reply (.eml) to questions is not done: it needs an LLM and a confirmation UI. |
| 4.3 Steer by review | ✅ | Reject reasons and rewrites become rule suggestions (`core/suggest.py`). "Добавить правило" (add rule) writes into the project's own copy of the extraction skill. |
| 4.4 Review round-trips | 🟡 | A reviewed DOCX comes back as a source, with each comment tied to the nearest FR ID. There is no Confluence yet. |

## "What not to do" (§5)

All of it was respected: no chat panel, no free-text FRD editing, no auto-accept, no two-way Jira sync, no multi-user, no new pipeline steps (the rail went from 6 steps to 5), and no model knobs.
