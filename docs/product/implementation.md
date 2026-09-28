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

Legend: ✅ done · 🟡 partly done (see note) · ⏭ deliberately not done (see note)

| ID | Item | Status | Note |
|---|---|---|---|
| PM-07 | Rebuild keeps Jira identity | ✅ | `Store._match_backlog`, `replace_backlog`; tests in `test_jira.py` |
| PM-24 | Orphaned Jira issues | ✅ | `Store.jira_orphans`, listed in the preview |
