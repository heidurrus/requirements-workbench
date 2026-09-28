# Requirements Workbench 3.0: product review

**Reviewer stance:** senior PM, persona from spec §1.3: a BA running elicitation calls for one client project at a time, alone, on a laptop.
**Build:** 3.0.0, run against `frontend/e2e/fake_llm_server.py` (fake AI, in-memory fake Jira project `SBX`). No real Jira or Atlassian account was touched.
**How the data was made:**
- **Project "My project"** was filled by `e2e/export.mjs`: 1 transcript, 3 atoms, FRD v1, a backlog, and a push of `SBX-1..3`.
- **Project "CRM контакт-центра"** was filled through the API: 6 transcripts and 1 email, up to **586 atoms** and 6 conflicts.
- **First run** used two instances. One had an empty data folder. The other also had **no Anthropic key**, to see a real first run.
- Screens were captured at 1440×900 and 1024.

**Screenshots:** `docs/product/shots/`. The design review in `docs/design/` is taken as done. This document is about flows, value and friction, not visual polish.

---

## 1. Executive summary

1. **Re-pushing after a backlog rebuild duplicates every issue in Jira and orphans the old ones.** I reproduced it: `SBX-1..3` → edit an atom → rebuild the document → rebuild the backlog → the preview says "создать: 3" → the push creates `SBX-4..6`. This breaks the product's core promise ("re-pushing updates… instead of duplicating") (`core/store.py:1025-1035`, `core/jira.py:29`).
2. **Staleness doesn't flow downstream.** After an atom changes, the rail still shows *Выгрузка ✓* and the Jira preview says "без изменений: 3" (no changes). The BA is told everything is in sync when it isn't (`Rail.svelte:38`, `shots/05-export-docstale-preview-1440.png`).
3. **Conflicts don't stop "done".** "Все атомы разобраны" (all atoms reviewed) shows while a conflict is still open. "Выбрать все → Принять" accepts both sides of every conflict. Accepting a *question* silently marks its conflict as answered, and nowhere records what the answer was (`Atoms.svelte:338`, `app.py:1025`).
4. **The client loop isn't served at all.** Open questions, conflicts sent "В вопрос" (to the client), and the action items the extractor skips are the BA's real follow-up list. Today they are a filter chip, an FRD section and a toast count. There is no register and no follow-up draft, and an answer can't be recorded.
5. **Traceability stops one hop short in the UI.** Jira descriptions carry the quote, but the Backlog, the FRD and Atoms never show the Jira key. The transcript doesn't highlight which lines became atoms (spec FR-TR-03 is a *Must* and isn't implemented). The audit log exists in the API (`/api/audit`) but has no UI.
6. **Time to value is fine for an imported transcript (about 9 clicks to a DOCX), but poor for the main job, a recorded call.** Recording → transcription → *stop*: nothing extracts automatically. A first run with no AI configured fails only at step 2, with an English-first setup story. One file at a time. Progress text is in English ("Reading the source…").
7. **Steering the AI means forking a Markdown prompt.** A BA can't say "split less", "use the role *Супервизор*", or "why did you reject this?" at the point of review. Rejections have no reason, so review decisions never feed back into the skills.

---

## 2. Flow-by-flow critique

### 2.1 First run, setup and a first project with no data

**What works**
- The empty states say what to do next, and most of them have a button that takes you there: Document → "К атомам" (to atoms), Backlog → "К документу" (to the document). See `shots/01-firstrun-document-1440.png` and `01-firstrun-backlog-1440.png`.
- AI setup errors are localised and come with an "Открыть настройки" (open settings) button (`shots/01-nokey-summary-error-1440.png`).
- Settings explains in plain words what goes to Anthropic. The local model is sized to the machine ("подходит этому компьютеру", fits this computer).

**Friction**
- **No setup checklist.** A new user can import a file before the AI works. They find out at "Импортировать и суммировать" (import and summarise): the summary pane turns into an error. Then "Извлечь требования" (extract requirements) shows a second error toast (`01-nokey-extract-error-1440.png`). Meanwhile the rail's project card says "Облачный ИИ" (cloud AI) as if the AI were ready.
- **"Открыть настройки" is a one-way door.** After pasting the key, nothing brings the user back to the transcript they were on. They have to find it through the rail's "Транскрипт" item, which opens "last viewed", or through Sources.
- **The default project is "My project" in a Russian UI** (`core/store.py:273`). So the first document is titled "FRD — My project". The app never asks for a project or client name, even though the name goes on the DOCX title page and into Jira.
- The empty Atoms state says "Выберите источник ниже" (choose a source below), but below it is "Нет источников с текстом" (no sources with text). There's no button to Sources (`01-firstrun-atoms-1440.png`).
- **Nothing shows the whole pipeline or how long it takes.** The first 5 minutes are a Sources screen with a record button and a drop zone. The persona has no picture of the FRD/Jira payoff until they have done three steps.

**Proposal**
- **A "Начало работы" (getting started) card on Sources until it's done, with four rows:**
  1. Name the project (client or system).
  2. AI: Claude key *or* local model, with a **Проверить** (check) button.
  3. Speaker separation (optional).
  4. Jira (optional, later).
  Each row has a status dot and closes itself when done.
- Settings opened from an error gets a **"← Вернуться к «Интервью»"** (back to the source) link.
- A sample project ("Демо: CRM контакт-центра") that the user can open and delete. It shows the whole chain (atoms → FRD → backlog → Jira preview) before they commit their own data.

### 2.2 Capture: recording, import, transcript and summary

**What works**
- Recording on separate channels, crash-safe streaming, and partial-channel warnings are solid engineering.
- Import handles the formats BAs actually get: Teams VTT, docx, eml and msg.
- Speaker rename propagates everywhere.
- Clicking an atom's quote jumps to the segment and flashes it.

**Friction**
- **Recording → atoms isn't one flow.** `stopRecording` calls `transcribeSaved()` and stops there (`Sources.svelte:121`). For a 60-minute call on CPU, the BA must come back later, open the transcript and press "Извлечь требования". There's no ETA and no OS notification when transcription finishes. The progress text comes from the backend in English: "Transcribing segments… 12/40" and "Queued — waiting for 1 job(s)…" (`app.py:196`, `app.py:228`, shown in the Sources row, `Sources.svelte:291`).
- **One file per drop.** `pickFile(e.dataTransfer.files[0])` (`Sources.svelte:209, 212`). A BA arriving on a project with 8 emails and 3 old specs has to import them one by one.
- **There's no consent reminder before recording** (spec FR-SRC-02, "Should"). For a tool whose selling point is compliant local capture, this is a trust gap.
- **The transcript can't be corrected.** An ASR error such as "АХТ" for AHT goes straight into the quote. Since quotes are "evidence", a wrong quote is worse than none (FR-TR-06).
- **The transcript doesn't show its atoms.** No highlights, no "this line produced FR-3", no jump to the atom (FR-TR-03 *Must*). The only link is the "45 атомов →" button (`Transcript.svelte:199`, `250-272`, `shots/02-transcript-1440.png`). So "verify a source" (spec flow 4) only works in one direction.
- **The summary is a dead end.** It's Markdown in a side panel (`Transcript.svelte:277-288`). You can't send it to the client as meeting minutes, it isn't linked to the atoms, and its "action items" section isn't connected to the action items the extractor drops.
- **"Транскрипт" in the rail is a pseudo-step.** It opens "the last source viewed" (`Rail.svelte:21`). With 7 sources, the rail item means something different every time.

**Proposal**
- A per-project setting, "После распознавания: суммировать и извлечь требования" (after transcription: summarise and extract), **on by default**, plus a desktop notification: "Созвон 3 готов · 45 атомов на ревью" (call 3 ready, 45 atoms to review).
- Multi-file drop that goes into the existing queue.
- A consent confirmation the first time you record in a session, stored in the audit log.
- Transcript highlights coloured by atom status. Clicking one opens the atom.
- Inline segment editing. After an edit, the app re-checks the quotes of the atoms that cite that segment.
- **"Сводка → письмо-резюме"** (summary → recap email): copy the summary as a client-ready email.
- Remove "Транскрипт" from the pipeline group. The transcript is a detail view of a source, not a stage.

### 2.3 Atom review at scale

I tested with 586 atoms from 7 sources. **Performance is not the problem:** first render took 232 ms, 20× `J` took 161 ms, and accept took about 300 ms, even with 2,930 buttons in the DOM. The problems are about triage and meaning.

**What works**
- The keyboard loop (J/K/A/X/E) goes straight to the next pending atom.
- Bulk selection with shift-range and ⌘A, with one undo for the whole batch.
- A source filter.
- "В конфликтах: 6" in the bulk bar (`shots/03-atoms-bulk-all-1440.png`).

**Friction**
- **Conflicts open by default push the list below the fold.** `conflictsOpen` defaults to `true` (`Atoms.svelte:250`). At 1024×768, with 3 conflicts, **zero atoms are visible** (`shots/03-atoms-scale-1024.png`). At 1440 the first atom starts at y≈750 (`03-atoms-scale-1440.png`). The changelog says conflicts are "a one-line summary that expands", and that's only true after the first click.
- **"Done" ignores conflicts.** The done state checks `!stats.pending` only (`Atoms.svelte:338`), so "Все атомы разобраны · Принято 3 из 3" shows next to an open conflict. The FRD then carries a red "1 конфликт не разрешён" (1 conflict not resolved) banner, and the push to Jira goes ahead with both contradictory requirements (`shots/04-small-atoms-1440.png`, `05-doc-stale-1440.png`).
- **Bulk accept doesn't treat conflicted atoms differently.** "Выбрано: 136 · в конфликтах: 6 → Принять" accepts both A and B.
- **Accepting a question has two meanings.** Accepting a question atom (a) keeps it for the FRD "Открытые вопросы" (open questions) section, and (b) marks any conflict it came from as *answered* (`app.py:1025-1026`, `store.py:785`). The answer itself is never recorded, and A and B both stay. A bulk accept of all questions therefore closes every conflict awaiting the client, without a word.
- **At 500+ atoms there's no search, no grouping (by source, theme, speaker) and no sort.** The only way to cut the list is status × type × one source dropdown. "Reject everything about reporting" is impossible without scrolling.
- **Reject has no reason.** "Not a requirement", "duplicate", "out of scope" and "wrong" all look the same. *Out of scope* is a real FRD section (5, "Вне рамок проекта") that is always "В источниках не указано" (not stated in the sources), because there is no way to route an atom there.
- **The BA can't add an atom.** There's no create route, so the BA's own knowledge, or a line from a chat, can't become a requirement except through a fake source file.
- **Merged atoms and skipped action items disappear.** `status != "merged"` is filtered out (`app.py:1013`). Skipped action items show only as a toast count (`lib/atoms.js:19`).
- **The undo window varies.** Single accept/reject undo lasts 6 s (the default in `state.svelte.js:126`); bulk actions last 10 s. Spec A-12 says ≥ 10 s. With `Backspace` as a delete key (`Atoms.svelte:232`), 6 s is short.

**Proposal**
- Collapse conflicts to one line by default. Add a **"Конфликты"** (conflicts) status pill, so conflicts become a filter and don't sit as a wall above the list.
- Done state: "Все атомы разобраны, но 1 конфликт ждёт решения" (all atoms reviewed, but 1 conflict needs a decision), with the CTA "Разобрать конфликт" (resolve the conflict) instead of "Собрать документ".
- Bulk accept: a "Принять 130 · пропустить 6 в конфликтах" (accept 130, skip 6 in conflicts) split button.
- Split the question lifecycle into **Открыт → Задан клиенту → Отвечен (ответ + источник)**, that is open → sent to the client → answered, with the answer and its source. An answer can close a conflict *and* update the winning atom.
- Search, plus "Группировать: по источнику / по разделу FRD / по спикеру" (group by source, FRD section or speaker).
- Reject reasons, with *Вне рамок* (out of scope) as a status that feeds FRD section 5.
- A **"＋ Атом"** (new atom) action, with an optional "источник: заметка BA" (source: BA's note).
- Keep action items as a third tab: "Поручения" (action items).

### 2.4 Building and iterating the FRD

**What works**
- The document reads like a document.
- Stale detection names sections ("разделы 3.1 устарели", sections 3.1 are out of date).
- The diff v1→v2 is clear and per requirement (`shots/05-doc-diff-1440.png`).
- Pinned free text survives rebuilds.
- Quality findings sit next to the text, with "Починить" (fix).
- The language-mismatch banner is a thoughtful touch.

**Friction**
- **Two near-synonyms in the toolbar.** "Пересобрать" and "Собрать заново" (`i18n.js:262-263`) both mean "rebuild", but they do very different things: only the changed parts vs rewrite everything. The difference is only in a `title` tooltip. "Собрать заново" also turns up in the language banner, one click away from rewriting approved prose.
- **The quality-fix loop takes three steps.** "Починить" → edit the proposal → accept. That changes the atom, which marks the section stale, which shows a yellow banner, which needs "Пересобрать", which makes a new version. One vague word costs a version. With 20 findings, the BA either makes 20 versions or batches the fixes and rebuilds once, and nothing tells them that.
- **Banners stack above the paper.** Stale, conflict and language warnings pile up at the top (`shots/05-doc-quality-1440.png`). At 1024 the text starts below the fold (`05-doc-quality-1024.png`).
- **There's no document lifecycle.** Versions exist, but nothing marks v3 as "sent to client 12.03" or "approved". Real change after sign-off, where the client asks for a change and you need a CR against the baseline, has no home. The diff is always against the previous version, not against the approved baseline.
- **Export is DOCX only.** There's no Markdown, Confluence or PDF, and no traceability appendix (source → atom → FR → story → Jira). When the client reviews the Word file with comments, those comments can only come back as a new generic "document" source.

**Proposal**
- Rename the buttons to **"Обновить изменённое (1)"** (update what changed) as the primary and **"Пересобрать весь документ…"** (rebuild the whole document) behind a confirmation. The confirmation says what is kept: pinned text and stable IDs.
- "Починить" should **patch the block in place**: fix the atom and regenerate only that block without a full version. Or offer "Применить все исправления и обновить" (apply all fixes and update) at the top of the Quality panel.
- Merge the banners into one "3 вещи требуют внимания" (3 things need attention) strip, with each item linking to its place.
- Add a document status (Черновик → На согласовании → Согласовано vN, that is draft → in review → approved), a baseline diff, and a "Запросы на изменение" (change requests) list after approval. See bet 4.1.
- Add export targets: a traceability matrix (XLSX or a DOCX appendix), Markdown, and a Confluence page.

### 2.5 Decomposition, the Jira push, and re-pushes after changes

**What works**
- Every FR gets a story. Missing ones are added, so no requirement is lost.
- NFRs start unticked, with a one-click "move into criteria".
- The preview is read-only and says so.
- The confirmation names the site and project.
- Failed rows can be retried.
- `rw-` labels recover issues after a crash.

**Friction (this is the flow where the product breaks)**
- **A backlog rebuild destroys Jira identity.**
  - `replace_backlog` soft-deletes every unpinned item, *including items with a `jira_key`*, and inserts new UUIDs (`core/store.py:1031-1045`).
  - The Jira label is the item id (`core/jira.py:29`), so the label search can't find the old issues either.
  - Result, reproduced: the preview shows **"создать: 3"** for requirements that already exist as `SBX-1..3`, and the push creates **`SBX-4..6`** (`shots/05-export-after-rebuild-1440.png`, `05-export-duplicate-push-1440.png`). Items `SBX-1..3` stay in Jira with no link and no warning.
  - The Backlog screen's own hint says "Правки закрепляются: пересборка их не перезапишет" (edits are pinned: a rebuild won't overwrite them). That's true for edits and false for Jira links.
  - The only way to avoid this today is to edit every story by hand before rebuilding, so it gets pinned.
- **Staleness doesn't cascade.**
  - After an atom changes, Document goes amber, but Backlog stays "3" and Export stays **✓** (`shots/05-doc-stale-1440.png`).
  - The Export preview in that state says "без изменений: 3" (`05-export-docstale-preview-1440.png`). That is true against the backlog and misleading against reality.
  - `Rail.svelte:38` shows ✓ whenever *anything* was ever pushed.
- **Jira keys aren't visible upstream.** Backlog, Document and Atoms never show `SBX-2`. A BA asked by a developer "where did SBX-2 come from?" has to open Jira and read the description.
- **Orphans are invisible.** `plan()` only iterates the current backlog items (`core/jira.py:151-214`). Issues whose item was deleted or rebuilt never show up as "есть в Jira, нет в бэклоге" (in Jira, not in the backlog).
- **The preview is manual every time.** "Показать предпросмотр" (show preview) has to be pressed after every visit. It's cheap (read-only), so it could just run.
- **There's no prioritisation.** Atoms and stories have no priority or MoSCoW field, so the Jira backlog lands unordered. The BA re-sorts it in Jira, and a re-push doesn't touch the order, which is at least safe.

**Proposal**
- **P0 fix:** on rebuild, match new stories to old ones by FR ref (plus a fallback on title similarity), and carry `jira_key`, `jira_hash` and `id` across. Until that ships, the rebuild must warn: "3 истории уже в Jira (SBX-1..3). Пересборка создаст новые задачи. Продолжить / Отмена" (3 stories are already in Jira; rebuilding will create new issues; continue or cancel).
- Make staleness a chain: atoms → FRD → backlog → Jira. The rail badges go amber downstream. Export shows "Документ изменился после сборки бэклога — пересоберите, чтобы выгрузить актуальное" (the document changed after the backlog was built; rebuild to push the current version).
- Show `SBX-n` chips on backlog rows and FRD blocks.
- Add orphan rows to the preview: "в Jira, но нет в бэклоге → оставить / закрыть с комментарием" (in Jira but not in the backlog → keep, or close with a comment).
- Auto-run the preview when the screen opens and the target is set.

### 2.6 Skills and AI control

**What works**
- Every AI step is inspectable.
- The contract is shown read-only.
- "Попробовать" (try) runs a draft on a real source without saving.
- History, .zip sharing, and a per-project choice.
- This is more control than most competitors offer (`shots/06-skill-try-1440.png`, `06-skill-contract-1440.png`).

**Friction**
- **Steering is far from the output.** To stop the extractor splitting "поиск по номеру и ФИО" (search by number and name) into two atoms, the BA must:
  1. go to Skills,
  2. find "Извлечение требований" (extract requirements),
  3. press "Сделать копию" (make a copy),
  4. edit prose instructions,
  5. try it,
  6. activate it,
  7. go back to Sources and press "Извлечь заново" (extract again) for each source.

  That's seven steps and a prompt-engineering skill set, for what is really feedback on one output.
- "Попробовать" shows the new result, but not **the difference from what the BA already has**: which atoms would appear or disappear.
- There's no one-off instruction per run: "Собери документ, но раздел 3 сгруппируй по ролям" (build the document, but group section 3 by role).
- Review decisions (rejects, edits, merges) are a strong signal of what the BA wants. None of them feed back.
- Nine stages, eleven built-in skills and two Word templates are exposed in one list. A BA who only wants "our house terminology" doesn't know that *Общие инструкции* (general instructions) is the place.

**Proposal**
- Add **"Уточнить…"** (refine) next to each AI action: Извлечь, Собрать, Разбить на истории (extract, build, split into stories). It takes a one-off note and can save it as a rule in the project's skill.
- "Попробовать" on a whole project shows a diff against the current atoms or document.
- After N rejects with the same reason, suggest a rule: "Вы отклонили 12 атомов как «процесс, не система». Добавить правило в скилл?" (you rejected 12 atoms as "process, not system"; add a rule to the skill?). See bet 4.3.
- Add a "Глоссарий проекта" (project glossary) entry point that writes into *Общие инструкции*.

### 2.7 Cross-cutting

- **Where am I, and what's next?** The rail badges help (136 to review, v2, ✓). But the ✓ and the missing downstream amber teach the wrong lesson (see 2.5). Each screen has a next-step CTA, which is good. There's no project home that answers "what changed since yesterday, and what needs me?"
- **Multi-project work.**
  - You can switch projects from the rail menu. Archiving needs at least two projects.
  - There's no delete, no project export or import, and no per-project overview.
  - Filters are stored globally in localStorage (`wb.atoms.status`), so "принятые" (accepted) carries over from project A to project B.
- **Collaboration and sharing.**
  - Only skills are shareable.
  - A project can't be handed to a colleague or backed up as one file.
  - The FRD reaches the client only as DOCX, and review comments can't come back.
  - D-01 says single user, which is fine. But "hand over the project" and "client reviews the doc" are single-user jobs too.
- **The local vs cloud privacy story.**
  - The Settings copy says *"в облако ничего не уходит"* (nothing goes to the cloud) for local-only projects (`i18n.js:117`).
  - Yet the Jira push (`app.py:1521`) has no `local_only` check, and it sends **verbatim client quotes with speaker and date** into every issue description (`core/jira.py:98-112`).
  - For an NDA project, that's the most sensitive data going to the widest audience: the whole dev team.
  - Nothing tells the user *before* an AI action which provider will get the text, or how much of it.
- **RU/EN.**
  - The UI strings are complete in both languages.
  - The leaks are backend progress messages (`core/atoms.py:152`, `app.py:142-335`), the default project name, the skill titles in the EN UI ("Word — ГОСТ", "Word — обычный", `shots/07-en-document-1440.png`), and one Russian error in the English API ("Отметь хотя бы одну строку", tick at least one row, `app.py:1531`).
- **Accessibility.**
  - Keyboard review is excellent on Atoms.
  - Row actions still appear only on hover. The tree and preview checkboxes are reachable, but the Delete and Backspace shortcuts plus a 6 s undo are risky for keyboard users.
  - Toasts carry the undo. There's no persistent "Отменить последнее" (undo last) such as ⌘Z outside Atoms.
- **Performance perception.**
  - The UI itself is fast (see 2.3).
  - The slow parts are ASR and LLM calls. There the UI shows a percentage and English text, but no ETA, no "you can leave this screen" hint, and no notification when the job finishes.

---

## 3. Prioritised improvement backlog

The score is RICE-style: **Reach** (1–5, share of sessions touched) × **Impact** (H=3, M=2, L=1) × **Confidence** (0.5–1) ÷ **Effort** (S=1, S/M=2, M=3, M/L=5, L=8). Effort is estimated from the code. **QW** marks a quick win (S effort, score ≥ 3).

> **Note:** PM-07 is P0 whatever its score. It's a data-integrity bug in the product's headline promise. PM-01 is the one-day stopgap for it.

| ID | Problem | Proposal | Impact | Effort | Score | Files / screens |
|---|---|---|---|---|---|---|
| PM-01 **QW** | Backlog "Пересобрать" silently drops Jira links, so the next push duplicates | Confirm before a rebuild when any item has `jira_key`: "N задач уже в Jira; пересборка создаст новые" (N issues are already in Jira; rebuilding will create new ones). Offer "пересобрать только новые FR" (rebuild only new FRs) | H | S | 12.0 | `Backlog.svelte:127`, `core/store.py:1025` |
| PM-02 **QW** | "Все атомы разобраны" shows with open conflicts; bulk accept takes both sides | The done state counts open conflicts. The bulk bar offers "Принять N · пропустить M в конфликтах" | H | S | 10.8 | `Atoms.svelte:338, 460-470` |
| PM-03 **QW** | Staleness doesn't cascade; Export ✓ and "без изменений" while the document is stale | Rail: amber downstream of any stale stage, ✓ only when Jira matches the latest FRD. Export shows a "бэклог/документ устарел" (backlog or document out of date) banner | H | S | 9.0 | `Rail.svelte:31-40`, `Export.svelte`, `app.py:866` |
| PM-04 **QW** | A local-only project still pushes verbatim client quotes to Jira; the copy says "ничего не уходит" | Per project: "Цитаты в Jira: полностью / только ссылка / нет" (quotes in Jira: full / link only / none), defaulting to *ссылка* (link only) for local-only projects. Fix the copy | H | S | 5.4 | `core/jira.py:80-115`, `i18n.js:117`, Settings |
| PM-05 **QW** | No recording consent reminder (FR-SRC-02) | Acknowledge once per session, logged to the audit log | M | S | 5.4 | `Sources.svelte:90` |
| PM-06 **QW** | Conflicts open by default hide the list (0 atoms visible at 1024) | Collapsed by default. Add a "Конфликты" status pill | L | S | 5.0 | `Atoms.svelte:250, 279` |
| PM-07 **P0** | A backlog rebuild creates new ids, so Jira identity is lost (reproduced: `SBX-4..6` duplicates `SBX-1..3`) | Match rebuilt stories to previous ones by FR ref (fallback: title similarity). Carry `id`/`jira_key`/`jira_hash`. Make the label independent of the item uuid | H | M | 4.0 | `core/store.py:1025-1051`, `core/backlog.py:81-152`, `core/jira.py:29` |
| PM-08 **QW** | Progress and queue text in English in the RU UI | Send progress codes plus parameters and translate them in `i18n.js` | L | S | 4.0 | `core/atoms.py:152,184`, `app.py:142-335`, `core/frd.py`, `core/backlog.py` |
| PM-09 **QW** | "Транскрипт" is a pseudo-step whose target changes | Drop it from the pipeline and make the transcript a detail view of Sources. ⌘2 → Atoms | L | S | 4.0 | `Rail.svelte:12-24` |
| PM-10 **QW** | The single-atom undo lasts 6 s (spec ≥ 10 s), while Backspace deletes | Undo at ≥ 10 s everywhere, plus ⌘Z for the last action on Atoms, Backlog and Document | L | S | 4.0 | `state.svelte.js:126`, `Atoms.svelte:95` |
| PM-11 | Jira keys aren't visible upstream | `SBX-n` chips on backlog rows, FRD blocks and atoms, linking to Jira | M | S/M | 3.6 | `Backlog.svelte`, `Document.svelte`, `/api/.../document` |
| PM-12 **QW** | "Пересобрать" vs "Собрать заново" is ambiguous and the risky one is a click away | "Обновить изменённое (N)" plus "Пересобрать весь документ…" with a confirmation stating what's kept | L | S | 3.6 | `Document.svelte:215-223, 298-300`, `i18n.js:262-263` |
| PM-13 | Recording → transcription stops; extraction is manual | A per-project option (on by default): after transcription, summarise and extract. Desktop notification when done | M | S/M | 3.2 | `Sources.svelte:121`, `lib/atoms.js`, `app.py` |
| PM-14 **QW** | One file per drop or pick | Multi-file drop and pick into the existing queue | L | S | 3.0 | `Sources.svelte:24-47, 209, 212` |
| PM-15 | No client follow-up: open questions, awaiting conflicts and action items are scattered | "Письмо заказчику" (email to the client): a generated follow-up listing the questions and confirmations. Copy it or save it as .eml | H | M | 2.8 | new, on Atoms or a project home |
| PM-16 | The BA can't add their own requirement | "＋ Атом" with type, optional source "заметка BA" (BA's note), audited | M | S/M | 2.7 | `app.py` (new POST), `Atoms.svelte` |
| PM-17 | The transcript doesn't show which lines became atoms (FR-TR-03 *Must*) | Highlights by atom status. Click → atom | M | M | 2.4 | `Transcript.svelte:250-272`, `/api/sources/<id>` |
| PM-18 | No search or grouping at 500+ atoms | Search, plus group by source / FRD section / speaker. Saved filter per project, not global | M | M | 2.4 | `Atoms.svelte:16-21, 51-54` |
| PM-19 | Skipped action items vanish | Keep them as "Поручения" (action items) with owner and date. Export them with the meeting recap | M | M | 2.1 | `core/atoms.py:174-191`, Atoms |
| PM-20 **QW** | "My project" default; never asks for the client or system name | Name the project on first run. A localised default | L | S | 2.0 | `core/store.py:273`, Rail |
| PM-21 | "Accept question" closes its conflict and the answer is never recorded | Question states: open → asked → answered (text + source). The answer resolves the conflict and updates the chosen atom | H | M/L | 1.9 | `app.py:1025`, `core/store.py:755-791`, Atoms |
| PM-22 | Reject has no reason; "out of scope" can't be expressed | Reject reasons. *Вне рамок* feeds FRD §5 | M | M | 1.9 | `Atoms.svelte`, `core/frd.py:234-262`, store |
| PM-23 | The audit log exists but has no UI | "История" (history) on atom, block and story, plus a project activity feed | M | S/M | 1.8 | `app.py:956`, new panel |
| PM-24 | Orphaned Jira issues are invisible | Preview rows for `rw-`-labelled issues not in the backlog: keep / close with a comment | M | M | 1.6 | `core/jira.py:151-214`, `Export.svelte` |
| PM-25 | ASR errors can't be fixed but become quotes | Inline segment edit with quote re-verification and an audit entry | M | M | 1.6 | `Transcript.svelte`, store |
| PM-26 | A first run finds the missing AI only on failure | A setup checklist card on Sources, with a "Проверить" test, and "back to where you were" after Settings | H | M | 1.6 | `Sources.svelte`, `Settings.svelte`, `lib/errors.js` |
| PM-27 | Fix → stale → rebuild = one version per vague word | Patch the block in place, or "Применить все и обновить" (apply all and update) | M | M | 1.6 | `Document.svelte:131-150`, `core/frd.py:494` |
| PM-28 | No traceability report | Matrix export: quote → atom → FR → story → Jira (XLSX, or a DOCX appendix) | M | M | 1.6 | `core/docx_export.py`, new endpoint |
| PM-29 | No project home: what changed, what needs me | An overview with stage status, "since your last session", and the next action | M | M | 1.4 | new screen or the Sources header |
| PM-30 | Long jobs: % only, no ETA, no notification | ETA from audio length × measured speed. OS notification. "Можно уйти с экрана" (you can leave this screen) | L | S/M | 1.2 | `Sources.svelte:288-293`, `app.py` jobs |
| PM-31 | A project can't be handed over or backed up | Export and import a project as a .zip (sources, atoms, doc versions, backlog, audit) | M | M | 1.1 | `core/store.py`, Settings → Проект |
| PM-32 | Steering needs a prompt fork | "Уточнить…" one-off note on Извлечь / Собрать / Разбить, with "сохранить как правило" (save as rule) | M | M/L | 1.0 | `Transcript.svelte`, `Document.svelte`, `Backlog.svelte`, `core/skills.py` |
| PM-33 | "Попробовать" shows output, not impact | Try on the whole project, with a diff against current atoms or the document | M | M | 0.9 | `Skills.svelte`, `app.py:1745` |
| PM-34 | No document lifecycle or change requests after sign-off | Status plus baseline plus CR list (see bet 4.1) | H | L | 0.7 | `Document.svelte`, store (documents) |
| PM-35 | Client review happens outside the app and doesn't come back | Markdown / Confluence / PDF export. Import DOCX comments as review items tied to FR ids | M | M/L | 0.7 | `core/docx_export.py`, `/transcribe` import |

35 items, 13 of them marked quick wins. Ship first, in about a week: PM-01, PM-02, PM-03, PM-04, PM-06, PM-08 and PM-12. Then PM-07.

---

## 4. Bigger bets

### 4.1 Change-safe delivery: requirement identity from quote to Jira, through sign-off

- **Rationale.** The pipeline is built for the *first* pass. Real projects spend most of their time in pass 2..n: new calls, client changes, a signed-off baseline, development already under way in Jira. Today every later pass risks duplicate issues (PM-07), gives misleading sync signals (PM-03), and has no idea of "approved". The bet is to make **FR-n the durable identity**: atoms → FR-n → story → Jira key, surviving rebuilds. Then add a baseline (Согласовано v3, approved v3). After it, changes become **change requests** with a diff against the baseline and an impact list: "FR-4 изменилось → истории SBX-12, SBX-13 → обновить в Jira" (FR-4 changed → stories SBX-12 and SBX-13 → update in Jira).
- **Risks.**
  - Matching rebuilt stories to old ones by FR ref will sometimes be wrong, for example when one FR splits into two stories. That needs a manual "это та же история" (this is the same story) override.
  - The status and CR model adds concepts to a deliberately linear product.
- **First small experiment.** Ship PM-07 (carry `jira_key` by FR ref), and log for two weeks of dogfooding how many rows the preview shows as create, update and orphan after rebuilds. Success: zero duplicate issues, and at least 80% of rebuilt stories matched automatically.

### 4.2 The client loop: an open-items hub and follow-up drafts

- **Rationale.** The BA's week is a loop: call → open questions → email the client → answer → update requirements → next call. The product captures the first step brilliantly and drops the rest. Several pieces already exist but are scattered or thrown away:
  - question atoms,
  - "В вопрос" conflicts,
  - the summary's action items,
  - the skipped action items.

  One **"Открытые пункты"** (open items) view would collect questions, confirmations and action items with a status. **"Письмо заказчику"** would draft the follow-up. **Importing the client's reply (.eml)** would propose which items it answers. That turns the tool from "document generator" into the BA's working memory for the project. **Meeting prep** falls out of it for free: an agenda built from what's still open, plus coverage gaps (NFR categories nobody mentioned: security, audit, availability).
- **Risks.**
  - It creeps into CRM or task-tracker territory. Keep it per project and tied to requirement items, with no people management.
  - Matching answers to questions is LLM-dependent and needs the BA to confirm each match.
- **First small experiment.** A "Скопировать вопросы для заказчика" (copy the questions for the client) button on Atoms. It makes plain text from the pending and accepted question atoms plus the awaiting conflicts, grouped by topic. Measure how often it's used per project, and ask 3 BAs whether they sent it largely unchanged.

### 4.3 Steer by review: turn decisions into skill rules

- **Rationale.** Skills are powerful, but they need prompt-writing, and they sit on a different screen from the output. The BA already teaches the system hundreds of times a session, by rejecting, editing, merging and retyping. With reject reasons (PM-22) and edits, the app can propose rules. For example: "Вы 9 раз переписали «Система должна…» в «Оператор может…». Добавить в общие инструкции?" (you rewrote "the system must…" as "the operator can…" 9 times; add it to the general instructions?). The app shows the rule with a try-it diff (PM-33), and the BA accepts. Steering then happens where the work happens.
- **Risks.**
  - Suggested rules may overfit to one project. Scope them to the project by default.
  - The loop is invisible without enough data.
- **First small experiment.** Log reject reasons and edit pairs for a month, with no suggestions shown yet. Then hand-write the rules the data implies and test them with "Попробовать" on the same sources. If rejects drop by ≥ 30% on a re-extract, build the suggestion UI.

### 4.4 Review-ready sharing without leaving local-first

- **Rationale.** The FRD's readers are the client and the dev lead, not the BA. Today the only channel is a DOCX, and comments come back as unstructured text. The bet has two parts. First, add **structured round-trips**: DOCX or Confluence export with FR ids as anchors. Second, **import the reviewed DOCX**, so each comment lands as a review item on its FR, which the BA accepts into atoms (with the client as the source of the quote). No server needed, and the local-first promise holds.
- **Risks.**
  - DOCX comment anchoring is brittle when the client edits heavily.
  - Confluence adds a second Atlassian surface to secure.
- **First small experiment.** Import a DOCX that has comments, and list each comment with the nearest FR-id. Measure the share correctly anchored on 5 real review rounds.

---

## 5. What not to do

- **A chat side panel ("спросите ИИ о проекте", ask the AI about the project).** Tempting and fashionable, but it bypasses the propose → decide → trace model that makes the product trustworthy. Put targeted "Уточнить…" notes on each AI action instead (PM-32).
- **Free rich-text editing of the FRD.** It would make the FRD feel like Word, and it would break traceability and stable IDs. Keep D-07: prose changes only through atoms or pinned blocks. Make those paths faster instead (PM-27).
- **Auto-accepting atoms above a confidence threshold.** It speeds up review but erodes "the human decides", and the BA carries the blame when a wrong requirement reaches the client. Faster triage (grouping, bulk with conflict exclusion, reasons) wins without that risk.
- **Full two-way Jira sync (statuses, sprint, estimates, comments back into the FRD).** It's large, fragile, and outside the BA's job. Do identity, orphans and "changed in Jira" first (PM-07, PM-24). Status read-back can come later as a read-only chip.
- **Real-time multi-user or cloud sync now.** It contradicts the local-first positioning and D-01. Project .zip handover (PM-31) and review round-trips (4.4) meet the actual single-user jobs.
- **More pipeline steps in the rail** (a separate Conflicts screen, Questions screen or Traceability screen). The rail's strength is six linear stages. New jobs belong as tabs or filters in existing screens, or on a project home.
- **More model knobs in Settings** (temperature, max tokens, per-stage model pickers). BAs steer through content, not sampling parameters, and every knob is a support ticket.

---

## 6. Open questions for the product owner

1. **Jira identity.** Is the duplicate-on-rebuild known (PM-07)? Should a Jira issue be tied to the *backlog item* or to the *FR-id*? What should happen to issues whose requirement was removed: close them, comment on them, or leave them?
2. **Sign-off.** Does anything happen after the client approves an FRD version: a baseline, change requests, re-approval? Who approves: the client in Word, or someone in the app?
3. **Quotes in Jira.** For NDA or local-only projects, may verbatim client quotes (with speaker and date) go into Jira descriptions seen by the whole dev team? Should that be a per-project policy?
4. **Questions.** Is "accept" on a question meant to mean "answered"? Where should the answer live, and should an answer be allowed to change the related atoms automatically?
5. **Action items.** Are meeting action items intentionally out of scope, or just not built yet? They're the BA's most-used output after a call.
6. **Real scale.** How many sources, atoms and stories does a typical engagement reach? That decides whether search and grouping (PM-18) or a project home (PM-29) matter more.
7. **Transcript editing.** Given that quotes are "evidence", may the BA correct ASR errors, and must the original be kept alongside?
8. **Priority.** Should atoms and stories carry priority (MoSCoW or a Jira priority) so the pushed backlog arrives ordered?
9. **Consent (Q-10 is still open).** Is a reminder enough, or must consent be recorded per participant, and under which jurisdiction (152-FZ, GDPR)?
10. **Readers.** Besides the BA, who needs to see the FRD or the traceability without Jira: the client, the tech lead, QA? That decides how much of bet 4.4 is worth building.

---

*Method notes:*
- Every claim tagged "reproduced" was tried in the running app with the fake AI and the fake Jira. The screenshots are in `shots/`.
- Claims tagged with `file:line` come from reading the code.
- The fake LLM produces repetitive wording ("Требование: Система: …", titles cut at 60 characters). That's test data, not a product finding, and I ignored it.
