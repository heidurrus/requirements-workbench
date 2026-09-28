# Requirements Workbench: design review of the current UI

**Build reviewed:** v2.9.3, run against `frontend/e2e/fake_llm_server.py` with a fresh data folder, filled through the same steps as the e2e scripts: 2 sources, 9 atoms, 2 conflicts, FRD v1, a backlog and a Jira preview.
**Screenshots:** `docs/design/current/`. Each screen was captured at 1440 and 900 px wide, in light and dark (`<screen>-<width>-<scheme>.png`). Empty states are at 1440 light.

> **A note on the screenshots.** They are full-page captures, so the sticky rail (`height: 100vh`) sometimes appears halfway down the image. That happens because of how Playwright stitches the image. The real window doesn't do it. Some toasts in the images are real, though: they carry over from the previous screen (see P3).

---

## Summary

The current UI is calm, honest and already has good bones:

- a restrained palette
- a consistent 4-px spacing scale (`--s-*`)
- visible focus rings
- keyboard review on Atoms
- undo toasts
- a read-only Jira preview
- text on every status (never colour alone)

Most of the problems are about **hierarchy and emphasis**. Every section is the same white box with the same 14-px bold title, so none of them reads as the main thing. The screen's main task often starts below the fold. Actions on every row are always visible, so a list of 100 items shows about 300 icons. Tertiary text fails WCAG AA. The window also wastes a lot of space between 820 and 1100 px.

None of this needs a new framework. It needs a tighter token set, one toolbar pattern, a sidebar that collapses, and a few shared components.

---

## Problems ranked by impact

Impact is a rough score (1–5) for how many sessions the problem touches, multiplied by how badly it hurts in each. It's a judgement call, not a measurement.

| # | Problem | Where | Impact |
|---|---|---|---|
| P1 | Tertiary text and control borders fail WCAG AA | everywhere | 5 × 4 |
| P2 | The main work area is pushed below the fold. Every section is a same-weight card | Atoms, Sources, Transcript, Settings | 5 × 4 |
| P3 | Toasts carry over to other screens and cover the bulk bar | all, esp. Atoms | 4 × 4 |
| P4 | The primary action has no fixed place. Toolbars are crowded or empty | Document, Backlog, Transcript, Export | 4 × 3 |
| P5 | Row noise: per-row actions are always visible; the tree is flat | Atoms, Backlog, Export, Sources | 4 × 3 |
| P6 | Narrow widths: the rail stays 224 px until 820 px | 820–1100 px | 3 × 4 |
| P7 | Typography: a declared webfont that isn't bundled, mono used for meta, a flat scale, no reading mode | everywhere, Document | 3 × 3 |
| P8 | Keyboard support is hard to discover outside Atoms | Backlog, Document, Export, global | 3 × 3 |
| P9 | Dark mode: primary buttons look disabled, conflict blocks are heavy | dark | 3 × 3 |
| P10 | Empty, loading and error states are thin and sometimes contradictory | Document, Backlog, Transcript | 2 × 3 |
| P11 | The rail shows no pipeline state | rail | 3 × 2 |
| P12 | Consistency: page widths, link-like buttons, repeated tags | Skills, Settings, Export | 2 × 2 |

---

## P1: Contrast and non-text contrast (WCAG 2.1 AA, spec NFR-A11Y-01)

I measured the current tokens from `frontend/src/app.css`:

| Pair | Ratio | Needed | Used for |
|---|---|---|---|
| `--ink-3` #8A908B on `--panel` #FFF | **3.26** | 4.5 | block meta ("2", "7 фрагментов"), hints, timestamps, rail step numbers, "Подстановка: {language}", `.hint` |
| `--ink-3` on `--paper` #EDEFEC | **2.82** | 4.5 | rail step numbers, the "v2.9.3" line, "Галочка — выгружать…" hint on Backlog |
| `--rule-2` #C6CAC4 (input/select border) on `--panel` | **1.66** | 3.0 (1.4.11) | every input, select, checkbox and segmented control outline |
| `--rule` on `--paper` (card edge) | 1.16 | decorative | fine for decoration, but it's the only thing separating cards from the canvas |
| dark `--ink-3` #7C837E on `--panel` #1D2124 | 4.17 | 4.5 | the same meta text in dark |

The rest passes: `--ink-2` is 5.2–6.8, the accent is 6–8, and every tag pair is ≥ 4.7.

The failures matter because `--ink-3` is the colour of nearly all *secondary information a BA scans for*: counts, timestamps, source meta, hints. The disabled primary button ("Распознать" on Sources, "Собрать документ" on the empty Document screen) uses `opacity: .5` on the accent. It reads as a pale *enabled* button (see `01-sources-empty-1440-light.png`, `04-document-empty-1440-light.png`).

Other a11y observations:

- Native checkboxes are 13 px, with no larger hit area (`03-atoms-*`, `05-decomposition-*`, `06-export-preview-*`). WCAG 2.2's 24×24 target size is missed on the most-clicked controls in the app.
- The focus ring (2 px accent, 2 px offset) is good and consistent. Keep it.
- Colour isn't the only signal: statuses carry text ("готово", "конфликт"). Keep this (NFR-A11Y-02).
- `02-transcript-1440-light.png`: the summary error reads *"Anthropic rejected the API key. Check it in Settings."* It is English in a Russian UI, with no action button. That's an i18n gap and a dead end.

## P2: Everything is a card of the same weight, and the main work starts below the fold

- **Atoms** (`03-atoms-1440-light.png`): the *Conflicts* block comes first and is fully expanded. At 1440×900 the first atom row starts at about y = 720 px. With 2 conflicts, the list the user came to review is almost entirely below the fold. Conflicts need attention, but they should be a *summary with a way in*, not a wall.
- **Sources** (`01-sources-1440-light.png`): the page is 5 stacked blocks: record card, upload card, "Параметры распознавания", "Все источники", and a list row. All have the same white panel, the same radius and the same 14 px/600 title. The list of sources, which is what you come back to 20 times a day, is the last thing on the page.
- **Transcript** and **Settings**: every block is a `<details>` with a chevron. Collapsing is useful for long settings, but on Transcript it's just noise ("Участники", "Транскрипт" and "Сводка" are all collapsible).
- `.screen-title` is 20 px and `.block-title` is 14 px, both 600, with nothing in between. The page title and the section titles don't separate strongly enough, and the 1-px `--rule-2` underline under the header is the heaviest line on the page.

## P3: Toasts carry over to other screens and cover the bulk bar

- `03-atoms-bulk-1440-light.png`: the toast "2 новых атома · 1 конфликт [Открыть атомы]" sits **on top of the bulk bar** and hides the *Принять* button. That is the single most important button in bulk review.
- Toasts outlive navigation: "Jira подключена" shows on Skills (`07-skills-1440-light.png`), "Собрано 6 историй" on Export (`06-export-connect-1440-dark.png`), and "Собрана версия 1" over the document text.
- Only one toast is shown at a time, so a new toast replaces an *undo* toast before the user can act on it.
- In dark mode the toast is an inverted light pill (`--ink` background). It's the brightest thing on screen and looks like an error.

## P4: The primary action has no fixed place

| Screen | Header actions | Where's the primary? |
|---|---|---|
| Sources | one "GPU" tag | inside the upload card ("Распознать"), which is disabled until a file is chosen |
| Transcript | "7 атомов" (primary) · Суммировать · Копировать · Скачать .txt | a count styled as a primary |
| Atoms | none | the per-row ✓, or the bulk bar |
| Document | Пересобрать · Собрать заново · template select · **Экспорт DOCX** · К декомпозиции → | six controls of mixed style in one row. The subtitle wraps to 2 lines at 1440 (`04-document-1440-light.png`) |
| Backlog | Пересобрать · **Проверить по INVEST** | INVEST is primary, but the next step "К выгрузке в Jira" is a second primary at the very bottom |
| Export | a "Jira · MCP" tag | "Выгрузить 7 задач" at the bottom of card 3, far below the fold with 21 rows |

Users can't form a habit ("the next step is always top-right"). Link-like ghost buttons ("Собрать заново", "В вопрос", "Изменить", "Отключить") sit right next to bordered buttons, so it's unclear which is which.

## P5: Row noise and a flat tree

- **Atoms:** every row always shows ✓ ✎ ✕. Twelve rows give 36 icons, plus the checkbox, the type tag and a full conflict strip (a pink box inside each row). Three layers of colour compete in each row: the tag, the conflict box and the selection tint.
- **Backlog** (`05-decomposition-1440-dark.png`): each story row has 5 always-on icons (＋ ↑ ↓ ✎ 🗑), and each sub-task has 4. The tree is mostly indentation plus a thin left rule, so epics, stories and sub-tasks look alike. Acceptance criteria are a run-on line ("Дано звонок поступил Когда оператор открывает карточку Тогда данные видны") that is hard to scan. The "сгенерировано" tag is repeated on every sub-task.
- **Export preview:** a flat list of 21 rows with two tags each. No column headers, no count per group, and no way to filter "only what will change".
- **Document:** each requirement block has a heavy 2-px coloured left border *and* a meta line *and* a sources line. Conflict notes are full-width pink bars. The paper reads as a form, not a document.

Some of the text duplication ("Требование: Система: …", titles cut at 60 characters) comes from the fake LLM. But the UI should never cut titles in the middle of a word: it should use CSS ellipsis on a full title.

## P6: Narrow widths

- The rail collapses to a top bar only at ≤ 820 px. At 900 px (`*-900-*.png`) it still takes 224 px, which leaves about 620 px for content. Atom statements wrap to 3–4 lines, conflict A/B cards become tall columns, and the Document contents column squeezes the paper.
- On the 900-px Atoms screenshot the toast overlaps row content, and the filter pills wrap to 3 lines.
- Nothing hides progressively. Toolbars keep all their buttons, so they wrap under the title.

## P7: Typography

- `--sans` starts with **"IBM Plex Sans"**, but the font isn't bundled. The spec (§ UI) says the app uses Plex, yet machines without it fall back to `-apple-system` / Segoe UI. So the app looks different on different machines, and none of the metrics were designed for the fallback.
- **Mono is used for meta:** dates, "транскрипт · 13 с · 2 спикера", atom provenance and step numbers. Mono at 12 px with wide spacing makes ordinary metadata look like code and doubles the texture of every row.
- The scale is 12 / 13 / 14 / 16 / 20, with only 600 weight for emphasis. There is no display size and no reading size. The document "paper" uses the same 14 px UI text as the forms around it, so a BA reading a 20-page FRD gets no reading mode.
- Tabular numbers aren't enabled, so counts and timestamps jiggle as they update ("6/14", "43%").

## P8: Keyboard support is hard to discover

- The good shortcuts exist only on Atoms (j/k/a/x/e, space, ⌘A, Esc). The hint strip is at the *bottom of the list*, below the fold on arrival.
- The Backlog tree, the Document quality findings, the Export preview and the rail have no shortcuts and no hints. Screens can't be switched with the keyboard (⌘1…⌘6), and there's no shortcut sheet (`?`).
- In Atoms, "focused" and "selected" look similar: both give a tinted background with a left bar. After shift-selecting, you can't tell which row the keyboard is on.

## P9: Dark mode

- The dark primary is `--accent` #8FBBD6 with dark text (`06-export-connect-1440-dark.png`, `05-decomposition-1440-dark.png`). Light-blue-on-dark reads as *disabled* or *secondary*, which is the opposite of primary.
- Conflict strips (`--danger-bg` #3A2622 with salmon text) inside every conflicting row are heavy in dark mode. Four of them turn the list red.
- Surfaces have a green tint (#15181A / #1D2124). It's fine alone, but it clashes with the blue accent and with native form controls, which Chrome renders in neutral grey.
- The rail and the canvas are the same colour, so only a 1-px line separates navigation from content.

## P10: Empty, loading and error states

- **Document empty** (`04-document-empty-1440-light.png`): "Пока нечего собирать [К атомам]" in the middle of the page, while the header shows a *disabled* primary "Собрать документ". Two calls to action contradict each other.
- The Atoms "all done" state is a green note, with the next step ("Собрать документ") a separate button. Good content, weak moment: finishing a review is the most rewarding moment in the app.
- Loading is a 12-px spinner plus text. Extraction progress ("6/14") appears only in the source row. The rail doesn't show that work is running.
- Errors show as red notes without a recovery action (the Transcript summary error; "Не удалось обработать").

## P11: Navigation has no pipeline state

- The rail is a list of 6 numbered labels and 2 tools. It doesn't say *where the work is*: "9 на ревью", "документ устарел", "выгружено". The pipeline is the product's core idea, and the rail is the best place to show it.
- The project switcher looks like a disabled input (grey fill, small "проект" label). The *Local only* lock tag only appears for local projects, and there's no equivalent "cloud allowed" hint.
- "Транскрипт" opens the *last* source. That's reasonable, but the item looks the same as the others.
- There is no way to collapse the rail (HIG: *consider letting people hide the sidebar*).

## P12: Consistency

- Content widths differ: Settings is about 720 px, Skills about 1150 px, other screens 1040 px (`07-skills-*`, `08-settings-*`).
- The Skills list repeats "используется" + "встроенный" tags on every item (24 tags), so the actual names are hard to find.
- Segmented controls on Settings stretch to full width ("Claude | Встроенная | Ollama" at 686 px), while elsewhere they fit their content.
- The destructive "Отправить в архив" is a low-contrast neutral button in the middle of a form.

---

## Screen-by-screen notes

### Источники (Sources): `01-sources-*`
- ✔ The big record button is clear and friendly. The drop zone lists formats.
- ✖ The primary action is disabled most of the time ("Распознать"). Recording has no persistent indicator once you leave the screen. The source list is at the bottom. "Параметры распознавания" is a whole block for 3 settings. At 900 px, record and upload stack into 2 tall cards before any content.
- **Proposal:** a toolbar with **Записать звонок** as the primary and *Импорт…* as secondary. A compact capture strip (record and drop side by side). The list becomes a real table with status, atoms and progress. Recording becomes a floating HUD that stays visible on every screen.

### Транскрипт (Transcript): `02-transcript-*`
- ✔ The speaker rename is inline and immediate. Timestamps are aligned.
- ✖ The time and speaker chip are stacked in a 130-px left column. The atom count is styled as the primary button. The summary error is in English with no action. No player appears for this imported source. Atom highlights inside the transcript are missing (the spec calls for them).
- **Proposal:** a player on top, a 3-column grid (time · speaker · text), `mark` highlights that link to the atom, and the summary as a side column with an update action.

### Атомы (Atoms): `03-atoms-*`
- ✔ Keyboard review, shift-range, ⌘A, a sticky bulk bar, undo, type and status filters, a source dropdown. The best-developed screen.
- ✖ Conflicts push the list below the fold (P2). Row actions are always on (P5). Toasts cover the bulk bar (P3). Focus and selection are confusable (P8). The status and type filter pills look identical but are two different kinds of filter. The hint strip is at the bottom.
- **Proposal:** a status *segmented control* plus type *chips*, with a "В конфликте" chip. A one-line conflict banner that expands in place. Hover or focus reveals row actions. An inspector pane at ≥ 1240 px shows the evidence quote in context. A floating HUD bulk bar, with toasts stacked above it. A clear "focus" ring that differs from the selection tint.

### Документ (Document): `04-document-*`
- ✔ Contents, stable IDs (FR-n), source links, pinned free text, and quality findings with a real *Починить* flow, versions and diff.
- ✖ The header is crowded (P4). The paper uses UI type. Every block has a 2-px left rule plus meta. Conflict bars are full-width. Quality findings live in a block at the top instead of next to the text they refer to.
- **Proposal:** a reading-size paper (15/24, a 70-character line), IDs hanging in the left margin, sources as small chips, quality findings as margin notes at ≥ 1360 px (inline above the paper when narrower), a split *Экспорт DOCX ▾* button (template in the menu), and *Пересобрать ▾* (holding *Собрать заново*).

### Декомпозиция (Decomposition): `05-decomposition-*`
- ✔ Include checkboxes cascade. Edits are pinned. NFRs are handled as a separate group with a "move into criteria" action.
- ✖ A flat tree with 4–5 always-on icons per row. Run-on Дано/Когда/Тогда text. "сгенерировано" everywhere. Two primaries.
- **Proposal:** a tree table (checkbox · disclosure · type glyph · title | criteria count | INVEST | FRD ref | hover actions) with ←/→/space keys. Stories expand into a statement ("**Как** … **я хочу** … **чтобы** …") and a 3-column criteria table. INVEST findings are inline, with *Разделить*.

### Выгрузка (Jira export): `06-export-*`
- ✔ An explicit read-only preview. A confirmation that names the project and site. Links to created issues. A private-window sign-in.
- ✖ The preview has no header or grouping. Finished steps take a whole card each. The push button is at the very bottom. The connect state is a lone card on an empty page.
- **Proposal:** a stepper (✓ Подключение — ✓ Проект и типы — 3 Предпросмотр). Finished steps collapse into a two-line summary with *Изменить*. The preview is a table with a segmented filter by action (Создать 6 · Обновить 1 · Без изменений 1 · Пропустить 14). A sticky push bar sits at the bottom of the table, and a confirmation sheet lists the facts.

### Скиллы (Skills): `07-skills-*`
- ✔ Clear built-in vs custom, copy-to-edit, try-it without saving, and a sections editor with RU/EN names.
- ✖ The list is noisy with tags. The editor is one long page (instructions, then sections, try, contract, history), so "Попробовать" is 1500 px down. Usage is a tag plus a switch that don't read as a choice.
- **Proposal:** a compact list with a green dot for "используется" and "встр./свой" in muted text. The editor gets tabs (Инструкции · Разделы · Попробовать · История · Что добавляет приложение) and a radio choice for *Использование*.

### Настройки (Settings): `08-settings-*`
- ✔ Plain language about where data goes ("В Anthropic уходит только текст…"). Model download cards that fit the machine.
- ✖ Every section is collapsible. Segmented controls stretch. Hints sit far below their controls. The archive action is buried.
- **Proposal:** a macOS-style grouped form with the label and hint on the left and the control on the right, plus an explicit *Оформление* (theme) row.

---

## Research: references and what to borrow

`godly.website` now redirects to **recent.design**. Its gallery is rendered client-side, so I couldn't list its entries reliably. So I picked references from the tool-like, calm, editorial sites that godly featured, looked at their public sites or design write-ups, and combined that with Apple's HIG (fetched from `developer.apple.com/tutorials/data/design/human-interface-guidelines/*.json`). Nothing is copied, and no brand assets are used.

| Reference | What it does well | What to borrow (specifically) |
|---|---|---|
| **Linear** (app + "How we redesigned the Linear UI") | Three-variable themes (base, accent, contrast) generated in LCH. Darker text in light mode and lighter in dark. Less chrome colour. Dense but aligned sidebar | A **small semantic token set** instead of ad-hoc colours. Neutral surfaces with a *single* accent. Sidebar rows at 30 px with a 20-px icon column. Increase text contrast in both themes rather than adding borders |
| **Raycast** | Keyboard-first. Shortcut hints printed next to actions. The HUD-style action panel | `kbd` chips **inside** buttons ("Принять A"). A dark HUD material for transient bars (bulk bar, recording, toasts). A future ⌘K command palette |
| **Things 3** | Calm "paper" whitespace, purposeful unfolding animation, very few colours, generous line height for reading | Expand-in-place transitions (180–240 ms, ease-out). A reading-size body for the Document paper. Celebrate "done" states (the Atoms "Все атомы разобраны" empty state) |
| **Vercel / Geist** | A 10-step colour scale with steps assigned to roles: 100–300 backgrounds, 400–600 borders, 900–1000 text | Map **every** token to a role (`surface`, `line`, `line-control`, `text-3`), so borders and text have their own tokens and contrast is checked per role |
| **Arc** | A sidebar that collapses fully. Content-first window with minimal chrome | **Collapse to an icon rail** at ≤ 1120 px and let the user toggle it (⌘\). Status dots on collapsed items |
| **Notion** | Editorial documents in an app: comfortable measure, hover-revealed block handles, inline comments | Hover and focus-revealed row actions. Hanging IDs in the margin. **Margin notes** for quality findings |
| **Height** (archived) | Tree tables with inline expansion and per-column meta; clear parent/child glyphs | The Backlog **tree table** with type glyphs (E/S/·) and columns for criteria, INVEST and FRD ref |
| **Apple Mail / Notes** (HIG reference) | A sidebar with at most 2 levels, a toolbar with one prominent trailing action, grouped settings forms | Toolbar: title leading, **one `.prominent` action trailing**. A grouped Settings form. Destructive defaults avoided in sheets |

**HIG points that apply directly:**

- **macOS type:** the body text style is 13 pt/16, headline 13 bold, title 3 15 pt/20, title 2 17/22, title 1 22/26, large title 26/32. The minimum size is 10 pt (default 13).
- **Sidebars:** show no more than two levels, auto-hide as the window narrows, let people hide the sidebar, and keep critical actions out of the bottom of the sidebar.
- **Toolbars:** use only one prominent action and put it on the trailing side. Define which items move to overflow as the window narrows. Prefer symbols without borders.
- **Materials:** use thicker, more opaque materials behind text. Don't put glass in the content layer.
- **Colour:** give every custom colour light, dark and increased-contrast variants, and apply colour sparingly: status and primary actions only.
- **Accessibility:** meet WCAG AA contrast, support text enlargement up to 200 %, and make motion optional.
