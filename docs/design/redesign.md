# Requirements Workbench 4.0: redesign specification

Status: proposal, ready to implement. Backend and API stay as they are.
Prototype: `docs/design/prototype/index.html` (open the file in a browser; no build step).
Prototype screenshots: `docs/design/prototype/shots/<screen>-<width>-<theme>.png`.
Screenshots of today's app (3.3.3, demo data, fake AI): `docs/design/redesign-before/<screen>-<width>-<theme>.png`.

This document replaces `docs/design/design-system.md`. Where the two disagree, this one wins.

Contents

1. Diagnosis
2. Concept and principles
3. Information architecture and navigation
4. Visual system (tokens)
5. Components
6. Keyboard
7. Responsive rules
8. Screens
9. The main flow, step by step
10. Microcopy
11. Implementation plan
12. What the e2e suites depend on
13. Not verified

---

## 1. Diagnosis

The current UI is a web page with a sidebar. It is tidy, and that is the problem: every screen is a single scrolling column of cards with a fixed or capped width, so the window size changes nothing except the amount of grey around the column.

### 1.1 Problems on every screen

| # | Problem | Where to see it |
|---|---|---|
| D1 | **The page scrolls, not the panes.** Toolbar, filters and inspector scroll away with the list. After 10 atoms the actions and the filter bar are gone. | `redesign-before/atoms-1280-light.png` |
| D2 | **Wide windows get emptiness.** At 2560 px the Sources list uses the top 40% of the window and the rest is blank; the document is a 750 px column with 500 px of nothing on each side; the transcript stops at 1190 px and the summary panel shows one line. | `sources-2560-light.png`, `document-2560-light.png`, `source-2560-light.png` |
| D3 | **Cards inside cards, borders around everything.** Lists, blocks, banners and panels each have a 1 px border and a radius. Hierarchy comes from boxes, so nothing stands out. | `atoms-2560-light.png`, `backlog-1728-light.png` |
| D4 | **Banners stack above the work.** Atoms opens with a conflict banner, a blue notice, two rows of filters and a source select before the first atom (first row at y = 325 of 800). Document opens with a status control, a red banner and a note. | `atoms-1280-light.png`, `document-1728-dark.png` |
| D5 | **Bare icon buttons.** Source toolbar: two unlabeled squares (copy, download). Atom row: clock, check, cross, pencil, bin with no labels, the bin one click from the pencil. Backlog row: plus, pencil, bin. | `source-2560-light.png`, `atoms-2560-light.png`, `backlog-1728-light.png` |
| D6 | **Controls that do not say what they are.** "Приоритет…" is a select that looks like text. "В декомпозицию" is a switch with no explanation of what it switches. The type filter and the status filter look the same. "Word — обычный" is welded to "Экспорт DOCX" and its text is clipped. | `atoms-2560-light.png`, `document-2560-light.png` |
| D7 | **No place that says where the project stands.** The sidebar badges (`2`, `5`, `v1`, `7`) are numbers without nouns. "v1" does not say the document is a draft; "7" does not say seven of what. | every screenshot, sidebar |
| D8 | **Switching sources and documents takes a trip.** To open another source you go back to Sources. Documents are tabs that exist only on the Document screen. | `source-2560-light.png` |
| D9 | **The bulk bar is three rows of mixed controls** over the list: selects, buttons and a delete in one dark box, 520 px wide at any window width. | `atomsbulk-1280-light.png` |
| D10 | **Type tags are six pastel pills.** With status, conflict and priority next to them, a row has four to five coloured things. | `atoms-2560-light.png` |

### 1.2 Screen by screen

**Sources** (`sources-1728-light.png`). The top third is two large cards (record, drop zone) that are used a few times a week, and a collapsed "Параметры распознавания". The list, which is what the BA opens the screen for, starts at y = 365 and has four columns of information with 900 px of blank row between the title and the status. No preview: to learn what a call was about you must open it.

**Source** (`source-2560-light.png`). "Участники" is a full-width card with three inputs that is needed once per recording and occupies the top of the screen forever. The transcript is a card with a 1 px border; lines run to 1000 px. The summary sits in a panel with no height of its own. The player is not visible in the default state. The atom chips under each line are truncated at 40 characters and coloured by status, not type, so the legend must be learned.

**Atoms** (`atoms-1280-light.png`, `atoms-2560-light.png`). The inspector appears only above 1240 px and is a card that scrolls away with the page (D1). It repeats the row (type, status, statement) before adding the one thing the row lacks, the quote in context. Conflicts are a banner that expands into more cards above the list. "Для заказчика" is a tab that looks like a filter. History is an ordered list with raw timestamps to the second.

**Document** (`document-2560-light.png`, `document-1728-dark.png`). Four horizontal strips above the paper: tabs, "Берёт: …" tags with the unexplained switch, the status segmented control, banners. Contents float in the left gutter without a pane. Quality findings, versions and compare are reachable only through the "…" menu or by scrolling. The primary button is "Экспорт DOCX" even when the document is stale and the right action is to update it.

**Backlog** (`backlog-1728-light.png`). Every story is expanded, so one screen shows three stories. Acceptance criteria are a table with 250 px columns regardless of width. Sub-tasks are full-height rows with a "сгенерировано" tag each. There is no way to see the whole backlog at once.

**Export** (`export-1728-light.png`). A three-step wizard header over one card, then a blank page. DOCX, the traceability workbook and the follow-up letter are not here at all; they hide in menus on other screens, although the sidebar item is called "Выгрузка".

**Skills** (`skilledit-2560-light.png`). The closest thing to a real desktop layout, and it shows the ceiling of the current approach: the list is a fixed narrow card with wrapped names, "встроенный" repeated sixteen times, and the instructions are a read-only grey box 1460 px wide with 190-character lines. "Где используется" is below the fold of the editor.

**Settings** (`settings-2560-light.png`). One 770 px column in the middle of a 2560 px window, title right-aligned over it, with project, AI, ASR, Jira and appearance in one scroll.

### 1.3 What is good and stays

The pipeline model, the keyboard loop on Atoms (J/K/A/X/E), undo in toasts, source chips on requirements, the confirmation before a Jira push, the language-mismatch warning, system fonts, and AA contrast.

---

## 2. Concept and principles

**Concept.** Requirements Workbench becomes a three-pane desktop document app, in the family of Mail, Notes and Xcode: a translucent sidebar that is both navigation and a live picture of the pipeline; a content pane that holds the thing being worked on (a list, a transcript, a page, a tree); and an inspector that explains the selected item and carries its actions. Panes scroll on their own, the toolbar never leaves, and as the window grows the app adds panes and columns (first the inspector, then a context pane with the source of the selected item) instead of margins. Colour is reserved for one accent and for state; structure comes from type weight, spacing and hairlines, not from boxes.

**Principles**

1. **Panes, not pages.** The window never scrolls. Each pane scrolls by itself. Toolbar, filter bar and action bar are fixed.
2. **Select, then act.** Clicking a row selects it; the inspector shows everything about it and owns its actions, with labels and keys. Rows show only two text buttons on hover.
3. **Width buys information.** Every screen defines what appears at 900, 1200, 1800 and 2800 px of workspace. Text is capped at 72 characters per line; panes are not.
4. **One accent, one primary.** Blue means "this moves the work forward" and "this is selected". One filled blue button per screen, always the rightmost in the toolbar.
5. **State is a word.** Every status is a glyph plus a word ("Устарел", "На ревью"), never a colour or a number alone.
6. **Hairlines and type, not boxes.** A border is allowed around a control and around a floating surface. Lists are separated by 1 px inset hairlines. Cards are used only for objects that can be picked up as a whole: the paper, a finding, a conflict.
7. **Nothing above the work.** At most one banner per pane, 36 px high. Everything else (notices, migrations, hints) goes to the inspector or the Overview.
8. **Keyboard first, shown.** Keys are printed on the buttons. ⌘K reaches every screen, source, requirement and command.
9. **Quiet motion.** 140 to 320 ms, ease-out, only to show where something came from.

---

## 3. Information architecture and navigation

### 3.1 Decisions

| Question | Decision |
|---|---|
| Is a left sidebar right? | Yes, but as a macOS source list, not a menu. It holds the project, the pipeline with state, and the project's sources and documents as children. |
| Five pipeline steps? | Five steps stay, in order: Источники, Требования, Документы, Бэклог, Выгрузка. "Атомы" is renamed **Требования** in the UI (RU) and **Requirements** (EN); "atom" stays an internal word. "Декомпозиция" is renamed **Бэклог** / **Backlog**. A new item **Обзор** / **Overview** sits above the pipeline and is the start screen. |
| How does the user know where the pipeline stands? | Each step has a **stage ring** (§5.17) and a status in words on the right: `6`, `10 на ревью`, `устарел`, `11 историй`, `5 из 14`. Staleness flows downstream: a changed requirement turns Документы, Бэклог and Выгрузка amber. |
| How does the user know the next action? | The toolbar's single primary button is always the next step of the pipeline from this screen, with its count ("Разобрать 10 требований →", "Обновить изменённое · 2", "К выгрузке в Jira · 10 →"). Overview repeats it as the "Следующий шаг" strip. |
| Switching projects | The project button at the top of the sidebar opens a popover: search field, list of projects with their next step, "Новый проект…", "Импортировать проект…", "Архив". ⌘⇧P opens it. |
| Switching sources | Sidebar children under Источники show the 3 most recent sources (5 at window height ≥ 1000 px); ⌘K finds any source by name; on the Source screen ⌥↑/⌥↓ go to the previous/next source. |
| Switching documents | Sidebar children under Документы list every document with its version and a state dot. The Document screen keeps a tab strip (`.doc-tabs`) so the tabs the BA knows stay. |
| Three-pane model | Yes: sidebar, content, inspector. A fourth **context** pane appears at workspace ≥ 1800 px. |
| Inspector | Yes, on Sources, Source, Requirements, Documents, Backlog and Skills. Toggle: ⌥⌘I or the toolbar button. State is remembered per screen. |
| Unified toolbar | Yes, 52 px, one per window, content supplied by the screen. |
| Command palette | Yes, ⌘K (Ctrl+K on Windows). Replaces nothing, reaches everything. |
| Keyboard-first review | Yes, extended: see §6. |
| Settings and Skills | Bottom of the sidebar. Not part of the pipeline. |
| Transcript | Not a step. A source opened from Sources, shown in the toolbar as `Источники › <name>`. |

### 3.2 Shell

```
┌──────────────┬──────────────────────────────────────────────────────────────────┐
│ ПД Портал…  ⌄│ ▯  Title                         [action] [action] [Primary →] ◐ ▯│  toolbar 52
│ 🔍 Поиск… ⌘K │    status line                                                    │
│              ├───────────────────────────────┬─────────────────┬────────────────┤
│ ⌂ Обзор      │ scope bar 40                  │ inspector head  │ context head   │
│ Конвейер     ├───────────────────────────────┤                 │                │
│ ● Источники 6│                               │                 │                │
│    source 1 •│  content pane                 │  inspector      │  context       │
│    source 2 ◌│  (scrolls)                    │  (scrolls)      │  (scrolls)     │
│ ◐ Требования │                               │                 │                │
│ ◉ Документы  │                               │                 │                │
│    SRS · v2 •│                               ├─────────────────┤                │
│ ◔ Бэклог     │                               │ action bar      │                │
│ ○ Выгрузка   │                               │                 │                │
│              │                               │                 │                │
│ [job card]   │                               │                 │                │
│ ≡ Скиллы     │                               │                 │                │
│ ⚙ Настройки  │                               │                 │                │
└──────────────┴───────────────────────────────┴─────────────────┴────────────────┘
  sidebar         content                         inspector         context ≥1800
```

### 3.3 Routes

Routes do not change (`#/sources`, `#/source/<id>`, `#/atoms`, `#/document`, `#/backlog`, `#/export`, `#/skills`, `#/skills/<name>`, `#/settings`). One route is added: `#/overview`. The empty hash opens `#/overview` when the project has at least one source, otherwise `#/sources` (which shows the first-run state).

### 3.4 Long jobs

A running job (transcription, extraction, document build, backlog build, model download) shows in three places, all fed from the existing `/job/<id>` polling:

1. The **job card** at the bottom of the sidebar: name, bar, percent, time left, queue length.
2. A spinner in place of the state dot on the sidebar child it belongs to.
3. The row or pane it is changing shows an inline status ("Распознаётся · 42%").

The BA can leave the screen; the card stays. When the job ends the card turns into a 6-second "Готово: 12 требований · Открыть" and the app calls `/api/notify`.

---

## 4. Visual system

All values are in `docs/design/prototype/tokens.css`. The block below is that file, verbatim. Copy it to `frontend/src/tokens.css`.

```css
/* Requirements Workbench — design tokens (redesign.md §4). Paste as-is into frontend/src/tokens.css. */

:root {
  color-scheme: light;

  /* ---------- Surfaces ---------- */
  --c-window:        #E9E9EC;                 /* behind everything; visible only under translucent sidebar */
  --c-sidebar:       rgba(244, 244, 246, .80);/* sidebar material (with --blur-sidebar) */
  --c-sidebar-solid: #F2F2F4;                 /* fallback when backdrop-filter is unavailable */
  --c-content:       #FFFFFF;                 /* primary pane: lists, paper, editors */
  --c-pane:          #FAFAFB;                 /* secondary panes: inspector, context, outline */
  --c-raised:        #FFFFFF;                 /* popovers, menus, sheets, selected segment */
  --c-toolbar:       rgba(255, 255, 255, .78);/* toolbar material */
  --c-toolbar-solid: #FFFFFF;
  --c-fill-1:        rgba(0, 0, 0, .04);      /* hover */
  --c-fill-2:        rgba(0, 0, 0, .06);      /* pressed, segmented track, wells, kbd */
  --c-fill-3:        rgba(0, 0, 0, .10);      /* pressed on a well */
  --c-scrim:         rgba(0, 0, 0, .28);

  /* ---------- Text ---------- */
  --c-text:          #1D1D1F;
  --c-text-2:        #4A4A4F;
  --c-text-3:        #6B6B70;                 /* lightest text allowed; placeholders too */
  --c-text-on-accent:#FFFFFF;

  /* ---------- Lines ---------- */
  --c-line:          rgba(0, 0, 0, .08);      /* hairlines between rows and panes */
  --c-line-strong:   rgba(0, 0, 0, .14);      /* edges of raised surfaces */
  --c-line-control:  #85858B;                 /* boundaries of inputs, checkboxes, switches (3.67:1) */

  /* ---------- Accent (the only brand colour) ---------- */
  --c-accent:        #0B63CE;                 /* fills: primary button, switch on, selection bar */
  --c-accent-hover:  #0957B7;
  --c-accent-press:  #084CA0;
  --c-accent-text:   #0A5BBF;                 /* links, selected icons */
  --c-accent-tint:   rgba(11, 99, 206, .10);  /* selected row, info banner */
  --c-accent-tint-2: rgba(11, 99, 206, .16);  /* selected row, hover */
  --c-focus:         #0B63CE;

  /* ---------- Status ---------- */
  --c-ok:            #1B7338;
  --c-ok-tint:       rgba(27, 115, 56, .10);
  --c-warn:          #8F5200;
  --c-warn-tint:     rgba(143, 82, 0, .10);
  --c-warn-mark:     #E0930A;                 /* dots and rings only, never text */
  --c-danger:        #BE3120;
  --c-danger-tint:   rgba(190, 49, 32, .10);
  --c-danger-fill:   #C2331F;                 /* destructive button in a confirmation sheet */
  --c-rec:           #E5372A;                 /* record button, recording pill */

  /* ---------- Atom types: a 6 px dot plus the code in this colour. Never a filled pill. ---------- */
  --c-type-br:       #5546C0;                 /* business        BR  */
  --c-type-fr:       #0A5BBF;                 /* functional      FR  */
  --c-type-nfr:      #0C6F68;                 /* non-functional  NFR */
  --c-type-rsk:      #AD4515;                 /* risk            RSK */
  --c-type-as:       #6A5A36;                 /* current state   AS  */
  --c-type-q:        #94389A;                 /* question        Q   */

  /* ---------- Speakers (dot + name) ---------- */
  --c-spk-1:         #0A5BBF;
  --c-spk-2:         #1B7338;
  --c-spk-3:         #8F5200;
  --c-spk-4:         #94389A;
  --c-spk-5:         #0C6F68;

  /* ---------- Evidence and diff ---------- */
  --c-mark:          #FFF0B3;                 /* quoted evidence in transcript and inspector */
  --c-ins:           rgba(27, 115, 56, .14);
  --c-del:           rgba(190, 49, 32, .12);

  /* ---------- HUD (bulk bar, toasts, recording pill): dark in both themes ---------- */
  --c-hud:           rgba(42, 42, 45, .92);
  --c-hud-solid:     #2A2A2D;
  --c-hud-text:      #F5F5F7;
  --c-hud-text-2:    #B9B9BF;
  --c-hud-line:      rgba(255, 255, 255, .14);

  /* ---------- Typography ---------- */
  --font:      -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, Roboto, "Noto Sans", sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif;
  --font-mono: ui-monospace, "SF Mono", SFMono-Regular, "Cascadia Mono", Consolas, Menlo, monospace;

  /* size / line-height / weight / tracking */
  --t-caption:  11px; --lh-caption:  14px;  /* 500  +0.01em  section labels, column heads, kbd */
  --t-foot:     12px; --lh-foot:     16px;  /* 400  0        meta lines, hints, badges */
  --t-body:     13px; --lh-body:     18px;  /* 400  0        default UI; 500 for buttons and labels */
  --t-item:     14px; --lh-item:     20px;  /* 500  -0.003em the thing under review: atom, story, segment */
  --t-read:     15px; --lh-read:     24px;  /* 400  -0.005em document body, summary, inspector statement */
  --t-title-3:  15px; --lh-title-3:  20px;  /* 600  -0.01em  toolbar title, pane title */
  --t-title-2:  17px; --lh-title-2:  22px;  /* 600  -0.012em document H3, sheet title */
  --t-title-1:  22px; --lh-title-1:  28px;  /* 600  -0.016em document H2, empty-state title */
  --t-large:    28px; --lh-large:    34px;  /* 700  -0.02em  document title, overview title */
  --t-mono:     12px; --lh-mono:     18px;  /* 400/500 0     ids, timestamps, code */

  --w-regular: 400; --w-medium: 500; --w-semibold: 600; --w-bold: 700;

  /* ---------- Space (4 px grid) ---------- */
  --s-1: 2px;  --s-2: 4px;  --s-3: 6px;  --s-4: 8px;  --s-5: 12px; --s-6: 16px;
  --s-7: 20px; --s-8: 24px; --s-9: 32px; --s-10: 40px; --s-11: 56px; --s-12: 72px;

  /* ---------- Sizes ---------- */
  --h-ctl-sm:  24px;   /* row buttons, segmented items inside rows */
  --h-ctl:     28px;   /* default control */
  --h-ctl-lg:  36px;   /* the one call to action in an empty state or sheet */
  --h-toolbar: 52px;
  --h-scope:   40px;   /* filter / scope bar under the toolbar */
  --h-row:     32px;   /* sidebar and outline rows */
  --gutter:    clamp(16px, 1.6vw, 32px);      /* pane padding; grows with the window */

  --w-sidebar:     clamp(220px, 15vw, 300px);
  --w-sidebar-rail: 60px;
  --w-inspector:   clamp(320px, 32cqw, 480px);  /* of the workspace, see §7 */
  --w-context:     clamp(380px, 25cqw, 640px);
  --w-outline:     clamp(208px, 16cqw, 320px);  /* document contents, settings categories */
  --w-list:        clamp(264px, 20cqw, 400px);  /* master list of a master-detail screen: skills, export */
  --w-measure:     72ch;                        /* longest line of running text */
  --w-paper:       860px;                       /* document page, including its margins */

  /* ---------- Radius ---------- */
  --r-xs: 4px;   /* checkbox, kbd, inline code */
  --r-sm: 6px;   /* buttons, inputs, rows */
  --r-md: 8px;   /* segmented track, banners, wells */
  --r-lg: 12px;  /* popovers, cards, paper */
  --r-xl: 16px;  /* sheets, HUD */
  --r-full: 999px;

  /* ---------- Elevation ---------- */
  --e-0: none;
  --e-1: 0 0 0 0.5px rgba(0,0,0,.12), 0 1px 2px rgba(0,0,0,.06);                          /* buttons, selected segment */
  --e-2: 0 0 0 0.5px rgba(0,0,0,.10), 0 2px 6px rgba(0,0,0,.05), 0 12px 32px rgba(0,0,0,.08); /* paper */
  --e-3: 0 0 0 0.5px rgba(0,0,0,.14), 0 4px 12px rgba(0,0,0,.08), 0 16px 40px rgba(0,0,0,.14); /* menus, popovers */
  --e-4: 0 0 0 0.5px rgba(0,0,0,.16), 0 12px 28px rgba(0,0,0,.14), 0 32px 80px rgba(0,0,0,.24); /* sheets, palette, HUD */

  /* ---------- Materials ---------- */
  --blur-sidebar: saturate(1.8) blur(30px);
  --blur-toolbar: saturate(1.8) blur(20px);
  --blur-hud:     saturate(1.6) blur(24px);

  /* ---------- Motion ---------- */
  --d-instant: 80ms;    /* press */
  --d-fast:    140ms;   /* hover, focus ring, row actions */
  --d-base:    220ms;   /* disclosure, segmented thumb, switch, pane content fade */
  --d-slow:    320ms;   /* pane slide, sheet, palette, toast, bulk bar */
  --ease-out:    cubic-bezier(.2, .8, .2, 1);      /* entering, moving */
  --ease-in:     cubic-bezier(.4, 0, 1, 1);        /* leaving */
  --ease-spring: cubic-bezier(.34, 1.36, .64, 1);  /* thumb of switch and segmented control only */

  /* ---------- Focus ---------- */
  --ring:       0 0 0 2px var(--c-content), 0 0 0 4px var(--c-focus);
  --ring-inset: inset 0 0 0 2px var(--c-focus);
  --ring-field: 0 0 0 3px rgba(11, 99, 206, .28);
}

/* Dark: follows the system unless the user forces light; data-theme="dark" forces dark. */
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  color-scheme: dark;
  --c-window: #101011; --c-sidebar: rgba(28, 28, 30, .76); --c-sidebar-solid: #18181A;
  --c-content: #1C1C1E; --c-pane: #222225; --c-raised: #2C2C2F;
  --c-toolbar: rgba(28, 28, 30, .78); --c-toolbar-solid: #1C1C1E;
  --c-fill-1: rgba(255,255,255,.05); --c-fill-2: rgba(255,255,255,.08); --c-fill-3: rgba(255,255,255,.13);
  --c-scrim: rgba(0,0,0,.52);
  --c-text: #F5F5F7; --c-text-2: #B9B9BF; --c-text-3: #9A9AA1; --c-text-on-accent: #FFFFFF;
  --c-line: rgba(255,255,255,.08); --c-line-strong: rgba(255,255,255,.14); --c-line-control: #77777D;
  --c-accent: #1F6FD9; --c-accent-hover: #2F7DE4; --c-accent-press: #1A60BE; --c-accent-text: #6FB2FF;
  --c-accent-tint: rgba(64, 140, 255, .18); --c-accent-tint-2: rgba(64, 140, 255, .26); --c-focus: #4C9AFF;
  --c-ok: #5FD082; --c-ok-tint: rgba(95,208,130,.14);
  --c-warn: #F0B548; --c-warn-tint: rgba(240,181,72,.14); --c-warn-mark: #F0B548;
  --c-danger: #FF8B7B; --c-danger-tint: rgba(255,139,123,.14); --c-danger-fill: #C9402D; --c-rec: #FF5A4D;
  --c-type-br: #ADA0FF; --c-type-fr: #6FB2FF; --c-type-nfr: #52D0C4;
  --c-type-rsk: #FFA06E; --c-type-as: #CDB98C; --c-type-q: #E590EA;
  --c-spk-1: #6FB2FF; --c-spk-2: #5FD082; --c-spk-3: #F0B548; --c-spk-4: #E590EA; --c-spk-5: #52D0C4;
  --c-mark: #4D4218; --c-ins: rgba(95,208,130,.18); --c-del: rgba(255,139,123,.18);
  --c-hud: rgba(50, 50, 54, .92); --c-hud-solid: #323236;
  --e-1: 0 0 0 0.5px rgba(255,255,255,.14), inset 0 0.5px 0 rgba(255,255,255,.10);
  --e-2: 0 0 0 0.5px rgba(255,255,255,.10), 0 12px 32px rgba(0,0,0,.40);
  --e-3: 0 0 0 0.5px rgba(255,255,255,.16), 0 8px 24px rgba(0,0,0,.50);
  --e-4: 0 0 0 0.5px rgba(255,255,255,.18), 0 24px 64px rgba(0,0,0,.64);
  --ring-field: 0 0 0 3px rgba(76, 154, 255, .36);
} }
:root[data-theme="dark"] {
  color-scheme: dark;
  --c-window: #101011; --c-sidebar: rgba(28, 28, 30, .76); --c-sidebar-solid: #18181A;
  --c-content: #1C1C1E; --c-pane: #222225; --c-raised: #2C2C2F;
  --c-toolbar: rgba(28, 28, 30, .78); --c-toolbar-solid: #1C1C1E;
  --c-fill-1: rgba(255,255,255,.05); --c-fill-2: rgba(255,255,255,.08); --c-fill-3: rgba(255,255,255,.13);
  --c-scrim: rgba(0,0,0,.52);
  --c-text: #F5F5F7; --c-text-2: #B9B9BF; --c-text-3: #9A9AA1; --c-text-on-accent: #FFFFFF;
  --c-line: rgba(255,255,255,.08); --c-line-strong: rgba(255,255,255,.14); --c-line-control: #77777D;
  --c-accent: #1F6FD9; --c-accent-hover: #2F7DE4; --c-accent-press: #1A60BE; --c-accent-text: #6FB2FF;
  --c-accent-tint: rgba(64, 140, 255, .18); --c-accent-tint-2: rgba(64, 140, 255, .26); --c-focus: #4C9AFF;
  --c-ok: #5FD082; --c-ok-tint: rgba(95,208,130,.14);
  --c-warn: #F0B548; --c-warn-tint: rgba(240,181,72,.14); --c-warn-mark: #F0B548;
  --c-danger: #FF8B7B; --c-danger-tint: rgba(255,139,123,.14); --c-danger-fill: #C9402D; --c-rec: #FF5A4D;
  --c-type-br: #ADA0FF; --c-type-fr: #6FB2FF; --c-type-nfr: #52D0C4;
  --c-type-rsk: #FFA06E; --c-type-as: #CDB98C; --c-type-q: #E590EA;
  --c-spk-1: #6FB2FF; --c-spk-2: #5FD082; --c-spk-3: #F0B548; --c-spk-4: #E590EA; --c-spk-5: #52D0C4;
  --c-mark: #4D4218; --c-ins: rgba(95,208,130,.18); --c-del: rgba(255,139,123,.18);
  --c-hud: rgba(50, 50, 54, .92); --c-hud-solid: #323236;
  --e-1: 0 0 0 0.5px rgba(255,255,255,.14), inset 0 0.5px 0 rgba(255,255,255,.10);
  --e-2: 0 0 0 0.5px rgba(255,255,255,.10), 0 12px 32px rgba(0,0,0,.40);
  --e-3: 0 0 0 0.5px rgba(255,255,255,.16), 0 8px 24px rgba(0,0,0,.50);
  --e-4: 0 0 0 0.5px rgba(255,255,255,.18), 0 24px 64px rgba(0,0,0,.64);
  --ring-field: 0 0 0 3px rgba(76, 154, 255, .36);
}

/* No translucency: solid fallbacks. */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  :root { --c-sidebar: var(--c-sidebar-solid); --c-toolbar: var(--c-toolbar-solid); --c-hud: var(--c-hud-solid); }
}
@media (prefers-reduced-transparency: reduce) {
  :root { --c-sidebar: var(--c-sidebar-solid); --c-toolbar: var(--c-toolbar-solid); --c-hud: var(--c-hud-solid);
          --blur-sidebar: none; --blur-toolbar: none; --blur-hud: none; }
}
@media (prefers-contrast: more) {
  :root { --c-text-2: var(--c-text); --c-text-3: var(--c-text-2); --c-line: var(--c-line-strong); --c-line-strong: var(--c-line-control); }
}
@media (prefers-reduced-motion: reduce) {
  :root { --d-instant: 1ms; --d-fast: 1ms; --d-base: 1ms; --d-slow: 1ms; --ease-spring: linear; }
}
```

### 4.1 Colour rules

- One accent, blue. It is used for: the primary button, the selected row tint, the focus ring, links, the "needs you" count in the sidebar, the switch when on. Nothing else is blue.
- Atom types are shown as a 6 px dot plus the code (`FR-12`) in the type colour, in mono. No filled pills. A row therefore has at most one coloured word on the left and one status on the right.
- Status colours are text colours on the surface, not fills. A tinted fill (`--c-*-tint`) is allowed for one banner per pane and for badges inside the paper.
- Backlog glyphs keep Jira's meaning: epic `#7A5AC8`, story `#2F8F55`, task `#3F7DC0`, white letter, 16 px, radius 4 px. They are the only fixed colours outside the tokens.
- `--c-text-3` is the lightest text. On a hovered or selected row, tertiary text is promoted to `--c-text-2`.
- Disabled: `opacity: .4` and `pointer-events: none`. A disabled primary must have a sentence next to it that says why.

### 4.2 Contrast (WCAG 2.1, computed)

| Foreground | Background | Light | Dark | Needs |
|---|---|---|---|---|
| `--c-text` | `--c-content` | 16.83 | 15.63 | 4.5 |
| `--c-text-2` | `--c-content` | 8.81 | 8.71 | 4.5 |
| `--c-text-3` | `--c-content` | 5.30 | 6.09 | 4.5 |
| `--c-text-3` | `--c-sidebar-solid` | 4.74 | 6.34 | 4.5 |
| `--c-text-2` | selected row | 7.60 | 7.01 | 4.5 |
| `--c-accent-text` | `--c-content` | 6.44 | 7.69 | 4.5 |
| white | `--c-accent` | 5.69 | 4.85 | 4.5 |
| white | `--c-danger-fill` | 5.55 | 4.94 | 4.5 |
| `--c-ok` | `--c-content` | 5.91 | 8.78 | 4.5 |
| `--c-warn` | `--c-content` | 6.22 | 9.24 | 4.5 |
| `--c-danger` | `--c-content` | 5.75 | 7.48 | 4.5 |
| `--c-danger` | danger tint | 4.92 | 5.61 | 4.5 |
| `--c-type-br` | `--c-content` | 6.95 | 7.49 | 4.5 |
| `--c-type-fr` | `--c-content` | 6.44 | 7.69 | 4.5 |
| `--c-type-nfr` | `--c-content` | 6.02 | 9.06 | 4.5 |
| `--c-type-rsk` | `--c-content` | 5.77 | 8.51 | 4.5 |
| `--c-type-as` | `--c-content` | 6.71 | 8.84 | 4.5 |
| `--c-type-q` | `--c-content` | 6.38 | 7.70 | 4.5 |
| every type colour | selected row | ≥ 4.98 | ≥ 6.02 | 4.5 |
| `--c-text` | `--c-mark` | 14.72 | 9.15 | 4.5 |
| `--c-hud-text` | `--c-hud-solid` | 13.14 | 11.72 | 4.5 |
| `--c-line-control` | `--c-content` | 3.67 | 3.82 | 3.0 |
| `--c-focus` | `--c-content` | 5.69 | 5.97 | 3.0 |

Translucent tints were measured as their solid equivalent over `--c-content`. Recompute in phase 0 if any token changes.

### 4.3 Typography

| Style | Size / line | Weight | Tracking | Used for |
|---|---|---|---|---|
| Caption | 11 / 14 | 500 | +0.01em | pane section labels, column heads, keys |
| Footnote | 12 / 16 | 400, 500 for status | 0 | meta lines, hints, badges, sidebar counts |
| Body | 13 / 18 | 400; 500 buttons and labels; 600 pane titles | 0 | default UI |
| Item | 14 / 20 | 500 | −0.003em | requirement statement, story title, source name |
| Item text | 14 / 22 | 400 | 0 | transcript lines |
| Reading | 15 / 24 | 400 | −0.005em | document body, story text |
| Title 3 | 15 / 20 | 600 | −0.01em | toolbar title, section titles on Overview |
| Title 2 | 17 / 22 (24 in inspector) | 600 | −0.012em | inspector statement, H3 on paper, sheet title |
| Title 1 | 22 / 28 | 600 | −0.016em | H2 on paper, skill name, empty state title, large numbers |
| Large | 28 / 34 | 700 | −0.02em | document title, project name on Overview |
| Mono | 12 / 18 | 500 (600 for type codes) | 0 | ids, timestamps, Jira keys, skill names |
| Code | 12.5 / 20 | 400 | 0 | skill instructions |

Rules: sentence case everywhere; no uppercase labels; `font-variant-numeric: tabular-nums` on counts, times and versions; mono only for identifiers, timestamps and code; `text-wrap: pretty` on statements and paragraphs, `balance` on the document title; minimum size 11 px. Font sizes do not scale with the window.

### 4.4 Space, size, radius

4 px grid. Pane padding is `--gutter` = `clamp(16px, 1.6vw, 32px)`: 16 px at 1024, 20 at 1280, 28 at 1728, 32 from 2000. Inspector and context panes use a fixed 20 px (`--s-7`) inside.

Radii are concentric: inner radius = outer radius − padding. Control 6, well 8, card and popover 12, sheet and HUD 16.

### 4.5 Elevation and materials

| Level | Used for |
|---|---|
| `--e-0` | everything that lies in a pane |
| `--e-1` | default buttons, the selected segment |
| `--e-2` | the paper |
| `--e-3` | menus, popovers, tooltips |
| `--e-4` | sheets, command palette, bulk bar, toasts, overlay inspector |

Materials, three in total:

- **Sidebar**: `--c-sidebar` with `backdrop-filter: var(--blur-sidebar)`. In pywebview on macOS the window background is `--c-window`; if the window is later made vibrant (`NSVisualEffectView`), set `--c-window: transparent` and nothing else changes.
- **Toolbar and player**: `--c-toolbar` with `--blur-toolbar`, so content scrolling under reads as depth.
- **HUD** (bulk bar, toasts, recording pill): `--c-hud` with `--blur-hud`, dark in both themes.

No translucency inside content. Fallbacks are in the tokens (`@supports not`, `prefers-reduced-transparency`).

### 4.6 Motion

| What | Property | Duration | Curve |
|---|---|---|---|
| Hover, row actions, focus ring | background, opacity, box-shadow | 140 ms | `--ease-out` |
| Press | transform scale(.98), background | 80 ms | `--ease-out` |
| Segmented thumb, switch thumb | transform, background | 220 ms | `--ease-spring` |
| Disclosure, tree twist, tab underline | transform, height | 220 ms | `--ease-out` |
| Screen change | opacity 0 → 1, no movement | 220 ms | `--ease-out` |
| Inspector or context pane appears | grid column width, content opacity | 320 ms | `--ease-out` |
| Overlay inspector, sheet, palette | translate 24 px / −8 px + opacity | 320 ms in, 220 ms out | `--ease-out` in, `--ease-in` out |
| Bulk bar, toast | translateY 24 / 16 px + opacity | 320 ms in, 220 ms out | same |
| Menu | scale .96 → 1 from its anchor corner + opacity | 140 ms | `--ease-out` |
| Progress bar | width | 320 ms | `--ease-out` |
| Row accepted or rejected | row fades to 0 over 140 ms, list closes the gap over 220 ms | | `--ease-out` |
| Evidence jump (open source at quote) | the segment background flashes `--c-mark` for 1200 ms | | linear |

Loops: spinner (800 ms), recording dot (1600 ms opacity .4 to 1). Nothing else loops. With `prefers-reduced-motion`, durations become 1 ms and the spinner slows to 2400 ms.

### 4.7 Focus, selection, scrollbars

- Focus: `box-shadow: var(--ring)` on `:focus-visible` for controls; `var(--ring-inset)` for rows; `var(--ring-field)` plus `border-color: var(--c-focus)` for text fields. Never removed.
- Focused row (keyboard cursor) = 3 px accent bar on the left edge. Selected rows (checkbox) = `--c-accent-tint` fill. A row can be both.
- Text selection: `--c-accent-tint-2` background, text colour unchanged.
- Scrollbars: 10 px track, thumb `--c-fill-3` inset by 3 px, `--c-text-3` on hover, track transparent. Only panes with class `.scroll` scroll.

---

## 5. Components

Class names match the prototype (`app.css`). States listed once where they are shared: every interactive element has default, hover (`--c-fill-1` or 4% darker), pressed (`--c-fill-2` or 9% darker, scale .98), focus-visible (ring), disabled (opacity .4).

### 5.1 Buttons `.btn`

| Variant | Look | Use |
|---|---|---|
| default | `--c-raised`, `--e-1`, 28 px, radius 6, weight 500, padding 0 12 | secondary actions |
| `.primary` | `--c-accent`, white; hover `--c-accent-hover`; pressed `--c-accent-press` | one per screen, rightmost in toolbar; one per inspector action bar |
| `.ghost` | transparent, `--c-text-2`; hover `--c-fill-1` | tertiary, toolbar icon buttons |
| `.danger` | default with `--c-danger` text; label always ends with "…" because it opens a confirmation | delete, archive |
| danger fill | `--c-danger-fill`, white | only inside a confirmation sheet |
| `.sm` | 24 px, 12 px text, padding 0 8 | rows, findings, conflict card |
| `.lg` | 36 px, 14 px text, radius 8 | empty state, sheet, "Следующий шаг" |
| `.icon` | 28 × 28 | only: sidebar toggle, inspector toggle, theme, back, play. Always `aria-label` and `title` with the key |
| `.rec` | default with a 10 px `--c-rec` dot | "Записать звонок" |
| pop-up `.popbtn` | `--c-fill-2`, label in `--c-text-3` + value in `--c-text` + up-down chevron | a choice with a current value: status, type, priority, source, speed |
| split | default button + 24 px chevron part, 1 px `--c-line` between | "Экспорт в Word ⌄" (template) |
| `.loading` | label hidden, 12 px spinner centred, width unchanged | while the request runs; never for jobs longer than 2 s (those use §5.16) |

A key hint `.kbd` sits after the label: `Принять A`. Icon before label, 16 px, 6 px gap. A trailing arrow means "goes to another screen".

### 5.2 Segmented control `.seg`

One of N. Track `--c-fill-2`, radius 8, 2 px padding; segments 24 px high, padding 0 12; selected segment `--c-raised` + `--e-1`; count after the label in `--c-text-3` (danger colour for conflicts). Keyboard: one tab stop, ←/→ move. Used for: requirement status filter, view switches in pane heads, language, provider, document status in narrow inspectors. If the options do not fit, the last ones collapse into a `.popbtn` "Ещё".

### 5.3 Tabs `.tabs`

Sections of one object, across a pane. 40 px high, 20 px gap, label weight 500, selected label `--c-text` with a 2 px accent underline, count in `--c-text-3`. Used for: documents (`.doc-tabs`), skill editor. Not used for filters.

### 5.4 Switch `.switch` and checkbox `.cb`

Switch 34 × 20, thumb 16, off `--c-fill-3` with a 0.5 px control line, on `--c-accent`. A switch always has a label on the left and one sentence under the label saying what happens when it is on. Checkbox 16 px, radius 4, 1 px `--c-line-control`; checked and indeterminate `--c-accent`. Hit area 28 px. In lists the checkbox is hidden until the row is hovered, focused, or any row is checked.

### 5.5 Fields `.field`, `.search`

Field: 28 px, 1 px `--c-line-control`, radius 6, `--c-content`. Hover border `--c-text-3`. Focus border `--c-focus` + `--ring-field`. Invalid border `--c-danger` with a 12 px message under it in `--c-danger`. Placeholder `--c-text-3`. Every field has a visible label or an `aria-label`.
Search: a well (`--c-fill-2`, no border), leading icon, trailing key `/`. Focus: background `--c-content` + `--ring-field`. Width `clamp(160px, 20cqw, 320px)`.
Code editor `.code`: mono 12.5/20, `--c-pane`, inset 1 px line, radius 8, max 110 characters per line. Read-only state: a lock line above ("Встроенный скилл нельзя менять · Сделать копию"), text `--c-text-2`.

### 5.6 Menus and popovers `.menu`

`--c-raised`, radius 12, `--e-3`, 4 px padding; rows 28 px, radius 6; hovered or keyboard-focused row `--c-accent` with white text; section label in caption style; separator 1 px. Opens from the anchor corner, 4 px gap, flips to stay in the window. Keyboard: ↑/↓, type to find, Enter, Esc. A selected value has a check on the left. Destructive items are last, after a separator, in `--c-danger`.

### 5.7 Type marker `.type`, status `.status`, badge `.badge`, chip `.chip`

- `.type`: 6 px dot + code, mono 12/600, in the type colour. `title` carries the full type name.
- `.status`: 12 px glyph + word, 12/500, coloured text, no background. `ok` Принято / Разобран / Годится, `accent` На ревью / Ждёт ревью / Новая, `warn` Устарел / Черновик / Замечание, `danger` Конфликт, neutral Отклонено / Без изменений.
- `.badge`: 18 px, radius 4, tint + coloured text, 11/500. Only inside the paper and tree rows, for one flag per item.
- `.chip`: 22 px pill, `--c-fill-1`, 12 px. For links to a source (icon, name, time) and Jira keys. Clickable chips darken on hover.

### 5.8 List row `.row`

Grid. Narrow (list pane < 1000 px): `checkbox 20 | type 52 | body 1fr | status 112`. Wide (≥ 1000 px): `checkbox | type | body | source 220 | speaker 120 | priority 96 | status 112`, and the source leaves the meta line.
Body: statement (Item style, max 96 characters per line), quote in «…» (Body, `--c-text-2`, 2 lines max), meta line (Footnote, `--c-text-3`: source, time, conflict in `--c-danger` with glyph, reject reason).
Vertical padding 10 px. Separator: 1 px hairline inset from the type column to the right edge. States: hover `--c-fill-1`; focused (cursor) 3 px accent bar; selected `--c-accent-tint`; rejected: statement struck through in `--c-text-3`. Hover or focus shows two `.btn.sm` at the right: "Принять" and "Отклонить". Sticky column header 28 px; sticky group header 28 px (`--c-pane`) when grouping is on.
Loading: 6 skeleton rows (statement bar 60% wide, quote bar 80%, `--c-fill-2`, no shimmer). Empty: §5.18. Error: a danger banner at the top of the pane with "Повторить".

### 5.9 Table `.table`

Header 28 px, caption style, sticky. Rows 44 px, 1 px hairline. First and last cells are padded with `--gutter`. Columns have priorities: `.c-wide` appears at workspace ≥ 1300 px, `.c-xwide` at ≥ 2000 px. Hover `--c-fill-1`, selected `--c-accent-tint`. Click selects; double-click or Enter opens.

### 5.10 Tree `.tree`, `.node`

`role="tree"`. Narrow: `checkbox | title 1fr | Jira 88`. Wide (≥ 900 px): adds Критерии 96, INVEST 96, Требование 120, Приоритет 88. Indent 24 px per level. Epic 14/600 with its goal in `--c-text-3` after the title; story 14/500; sub-task 13/400 `--c-text-2`, row 32 px. Twist chevron rotates 90° in 220 ms. Unticked nodes are dimmed. Stories are collapsed by default; details live in the inspector.

### 5.11 Cards

Only three kinds:

- **Paper** `.paper`: `--c-content`, radius 12, `--e-2`, max width 860 px, padding 72 / 80 / 96 / 104 px (top, right, bottom, left; the left margin holds the ids), scaled down with the pane by `cqw`.
- **Finding** `.finding` and **evidence** `.evidence`: `--c-content`, 1 px `--c-line` ring, radius 8. Selected finding: 2 px accent ring.
- **Conflict** `.conflict`: `--c-danger-tint`, radius 8; sides A and B on `--c-content`.

Form groups use `.form-card`: `--c-pane`, inset 1 px line, radius 12, rows separated by hairlines.

### 5.12 Banner `.banner`

36 px minimum, radius 8, icon, bold lead, one sentence, one button on the right. Variants: neutral (`--c-fill-1`), `info`, `warn`, `danger`. One per pane. A second problem goes into the same banner as a count ("3 вещи требуют внимания") with a menu.

### 5.13 Toast `.toast`

HUD material, 40 px, radius 12, bottom centre of the window, 24 px from the edge, or 96 px when the bulk bar is up. Text plus at most one button (`Отменить ⌘Z`). Lives 10 s, pauses on hover, at most 2 stacked, cleared on screen change. Errors are not toasts; they are banners or inline field messages.

### 5.14 Bulk bar `.bulk`

HUD, one row, 48 px, radius 16, centred in the list pane, 24 px from its bottom. Contents: `Выбрано: 3`, `в конфликтах: 1`, separator, **Принять 2 A** (primary, conflicts skipped), Отклонить X, Тип…, Приоритет…, separator, Снять выбор esc. "Тип…" and "Приоритет…" hide at workspace < 1100 px and move to a "Ещё" menu. Delete is in "Ещё" only. The list has 96 px bottom padding so the bar never covers the last row.

### 5.15 Sheet `.sheet`, command palette `.palette`

Sheet: 480 px, radius 16, `--e-4`, 16vh from the top, scrim `--c-scrim`. Title is the question with the number ("Выгрузить 12 задач в проект DLR?"), one sentence of consequence, a facts list (`dl.kv`), then Отмена (default focus) and the primary with the verb and the object ("Да, выгрузить в DLR ⌘↵"). Esc and scrim click cancel. Focus is trapped.
Palette: 640 px, radius 16, 14vh from the top, input 52 px with 17 px text, results in groups (Действия, Перейти, Требования, Источники, Документы, Истории), rows 36 px, max height 384 px. ↑/↓, Enter, Esc. Empty query shows actions for the current screen first.

### 5.16 Progress for long jobs

| Where | Look |
|---|---|
| Sidebar job card | name with spinner, 4 px bar, "42% · осталось около 6 мин", queue length |
| Row or table cell | `.status.accent` with 12 px spinner: "Распознаётся · 42%" |
| Pane being rebuilt (document, backlog) | content stays visible at 60% opacity, a neutral banner on top: "Обновляю раздел 3.2 · 1 из 2 · Остановить" |
| First result of a new object | skeleton of the future layout, not a spinner |
| Download (local model) | bar with "1,6 из 2,6 ГБ" and "Отменить" |
| Recording | HUD pill at the top centre of the window on every screen: pulsing dot, timer, level meter, "Остановить" |

Percent only when the backend reports one. Time left only after 10 s of measured speed. Every job line ends with what the user may do meanwhile when the job is longer than a minute: "Можно работать дальше".

### 5.17 Sidebar `.sidebar`, stage ring `.ring`

Width `--w-sidebar`. Rows 32 px, radius 6, 8 px inner padding; children 28 px, 12 px text, indented 32 px. Current row: `--c-fill-2`, label 600, icon in accent. Section label in caption style.
Stage ring, 16 px: **empty** (1.5 px `--c-line-control` ring) = not started; **active** (accent ring with a pie filled to the share done) = work waits for the BA; **stale** (amber ring, full amber disc) = built, but upstream changed; **done** (green disc with a white check) = nothing to do. The trailing text says the same in words.
Collapsed (rail, 60 px): icons and rings only, centred, 36 px rows; children, labels, job card hidden; tooltips on hover after 400 ms; a running job shows as a 2 px accent arc around the project mark.

### 5.18 Empty state `.empty`

Centred in its pane: 56 px glyph tile (radius 14, `--c-fill-2`), Title 1, one or two sentences (14/20, max 44 characters per line), one `.btn.lg.primary`. The toolbar primary is hidden while the empty state shows the same action.

### 5.19 Inspector and context panes

Pane head 40 px: what the pane shows (type + id, or a title), status on the right. Body: padding 20 px, sections separated by 20 px, each with a caption label. Key/value list `dl.kv`: 104 px label column. Action bar at the bottom: 12 px padding, top hairline, primary first. With nothing selected the inspector shows a summary of the list (counts by type and status) and no action bar. With several rows checked it shows "Выбрано: N" and the shared properties.

### 5.20 Toolbar `.toolbar`

52 px. Left: sidebar toggle, back button (Source only), title (Title 3) with a breadcrumb prefix in `--c-text-3`, status line (Footnote). Right: secondary actions, the primary, a 1 px separator, theme, inspector toggle. Priorities: `.tb-opt` actions hide at window < 1400 px and move to the palette and the "Ещё" menu; `.tb-opt2` actions lose their label at < 1180 px (only allowed for actions whose icon has a tooltip and which also live in the palette). The primary never hides and never loses its label.

---

## 6. Keyboard

On Windows, ⌘ is Ctrl and ⌥ is Alt. Keys are ignored while typing in a field, except ⌘-combinations and Esc.

**Global**

| Keys | Action |
|---|---|
| ⌘K | command palette |
| ⌘0 | Overview |
| ⌘1 … ⌘5 | Источники, Требования, Документы, Бэклог, Выгрузка |
| ⌘6 | Скиллы |
| ⌘, | Настройки |
| ⌘\ | sidebar |
| ⌥⌘I | inspector |
| ⌘⇧P | project switcher |
| ⌘⇧L | theme |
| ⌘R | record a call |
| ⌘O | import files |
| ⌘Z | undo the last decision (any screen) |
| ⌘↵ | the screen's primary action |
| / | search in the current pane |
| ? | list of keys |
| Esc | close overlay, else clear selection, else leave field |

**Requirements**: J/↓ and K/↑ move; ⇧ with them extends the selection; Space toggles the checkbox; ⌘A selects all shown; A accept; X reject (X then 1…4 picks the reason); E edit; T type menu; P priority menu; C open the conflict card; ↵ open the source at the quote; Space on the context pane's player plays the quote; 1…5 switch the status filter.

**Source**: Space play/pause; ←/→ 5 s; J/K previous/next segment; E edit the segment; ↵ on a requirement chip opens it; ⌥↑/⌥↓ previous/next source.

**Documents**: `[` and `]` previous/next finding; F accept the fix of the focused finding; ⌘E export to Word; ⌘D compare with the previous version; ⌥↑/⌥↓ previous/next section; ⌘⇧[ and ⌘⇧] previous/next document.

**Backlog**: ↑/↓ move; →/← expand/collapse (← on a collapsed row goes to the parent); Space toggles "выгружать"; E edit; ⌥↑/⌥↓ reorder; N new story in the current epic.

**Export**: ⌘↵ opens the confirmation with focus on Отмена; ⌘↵ again confirms.

**Skills**: ⌘S save; ⌘↵ run "Попробовать".

---

## 7. Responsive rules

The rules are written for the **workspace**: the window minus the sidebar. Panes use container queries on `.workspace` (`container-type: inline-size`), so collapsing the sidebar gives the width to the content.

| Window | Sidebar | Workspace |
|---|---|---|
| 1024 | rail 60 | 964 |
| 1280 | 220 | 1060 |
| 1440 | 220 | 1220 |
| 1728 | 259 | 1469 |
| 1920 | 288 | 1632 |
| 2560 | 300 | 2260 |
| 3840 | 300 | 3540 |

### 7.1 Rules

1. **Sidebar**: `clamp(220px, 15vw, 300px)`. Below 1180 px of window it becomes the 60 px rail by itself; ⌘\ overrides in both directions and the choice is remembered.
2. **Inspector**: `clamp(320px, 32% of workspace, 480px)`. Shown when the workspace is ≥ 900 px. Below that it is an overlay from the right (`min(400px, 92%)`, `--e-4`), opened by selecting a row or ⌥⌘I, closed by Esc.
3. **Context pane**: `clamp(380px, 25% of workspace, 640px)`. Shown when the workspace is ≥ 1800 px and the inspector is on.
4. **Outline pane** (document contents, settings categories): `clamp(208px, 16%, 320px)`. **Master list** (skills, export destinations): `clamp(264px, 20%, 400px)`. Shown at workspace ≥ 900 px. At 900 to 1199 px a screen with both an outline and an inspector keeps the inspector and moves the outline into a pop-up button in the scope bar; screens with a master list keep the list and turn the inspector into a tab of the detail.
5. **Content pane** takes what is left, never less than 480 px. It is not capped. Inside it, text is capped: statements 96 characters, running text 72 characters, code 110 characters, paper 860 px.
6. **Lists become tables.** When the list pane is ≥ 1000 px (tree: ≥ 900 px) the row gains columns (§5.8, §5.10). Tables gain `.c-wide` columns at workspace ≥ 1300 px and `.c-xwide` at ≥ 2000 px.
7. **The paper does not stretch.** Extra width around it goes to the outline, the inspector and the context pane. In compare mode the context pane gives its place to the second page; below 1400 px of workspace compare is inline (insertions and deletions in one page).
8. **Overview and Settings reflow in columns**: Overview 1 column below 1100 px, 2 from 1100, 3 from 1800; Settings groups in `repeat(auto-fit, minmax(560px, 1fr))`, each group at most 880 px.
9. **Gutter** grows from 16 to 32 px (`--gutter`).
10. **Toolbar** drops actions by priority (§5.20); filter bars drop `.opt` controls below 1100 px of workspace.
11. **Height**: below 700 px of window the job card collapses to one line and sidebar children are hidden.
12. **Pane widths can be dragged.** Each divider is a 9 px invisible handle on the hairline; double-click resets. Limits are the `clamp` bounds above. Stored per screen in `localStorage` (`wb.pane.<screen>.<pane>`).

### 7.2 What each width shows

| Screen | 1024 | 1280 | 1728 | 2560 | 3840 |
|---|---|---|---|---|---|
| Overview | 1 column | 2 columns | 2 columns | 3 columns | 3 columns, max 2200 px |
| Sources | table 4 columns + preview | same | + Участники, Объём | + Разбор bar + requirements of the source | same, wider |
| Source | transcript + summary | same | same | + requirements of the source | same |
| Requirements | list + inspector | same | same | table columns + inspector + source context | same |
| Documents | paper + inspector | paper + inspector | contents + paper + inspector | + source context, or two pages in compare | same |
| Backlog | tree + story | same | tree with columns + story | + requirement context | same |
| Export | destinations + preview | same | + Требование, Приоритет | same | same |
| Skills | list + editor | same | list + editor + details | editor and try-out side by side | same |
| Settings | categories + form | same | same | 2 columns of groups + system state | 3 columns |

---

## 8. Screens

Each screen: layout, hierarchy, actions, states, keys. Wireframes show the workspace (the sidebar is left out). "Narrow" is 1280, "wide" is 2560.

### 8.1 Overview (new) `#/overview`

Prototype: `shots/overview-*.png`.

```
narrow                                          wide
┌──────────────────────────────────────┐        ┌──────────────────────────────────────────────────────────┐
│ Портал дилера                        │        │ Портал дилера                                            │
│ client · counts                      │        │ ┌ Следующий шаг ──────────────────────── [Начать ревью]┐ │
│ ┌ Следующий шаг ──── [Начать ревью]┐ │        │ Конвейер        │ Для заказчика     │ С прошлого раза    │
│ Конвейер          │ Для заказчика   │        │ 5 stage rows    │ questions, tasks  │ activity           │
│ 5 stage rows      │ questions       │        │ Документы       │ Требования по     │ Недавние источники │
│ С прошлого раза   │ Документы       │        │                 │ типам             │                    │
└──────────────────────────────────────┘        └──────────────────────────────────────────────────────────┘
```

- Hierarchy: project name (Large), then the one next step, then the pipeline.
- "Следующий шаг" is computed from `/api/projects/<id>/status` in this order: AI not set up → set up; no sources → import; job running → wait (shows progress, no button); requirements to review → review; open conflicts → resolve; no document → build; document stale → update; findings open → fix; no backlog or backlog stale → build or update; items not pushed → push; else "Всё готово" with "Составить письмо заказчику".
- Primary: the next step. Secondary: Импортировать…, Записать звонок.
- Sections: Конвейер (ring, name, one sentence of state, one button), Для заказчика (open questions, action items, "Составить письмо"), С прошлого раза (from `/api/projects/<id>/activity`), Документы, Требования по типам (six bars: accepted, to review, rejected), Недавние источники.
- States. Empty project: see §8.10. Loading: skeleton of the three section titles with 3 rows each. Error: banner "Не удалось загрузить проект · Повторить".

### 8.2 Sources `#/sources`

Prototype: `shots/sources-*.png`.

```
narrow                                                    wide
┌─────────────────────────────┬──────────────┐            ┌───────────────────────────────┬────────────┬─────────────┐
│ Источник  Дата  Треб. Сост. │ preview of   │            │ + Участники Объём Разбор      │ preview    │ requirements│
│ rows 44                     │ the selected │            │                               │            │ of the      │
│ ...                         │ source       │            │                               │            │ source      │
│ [drop zone]                 │              │            │ [drop zone]                   │            │             │
└─────────────────────────────┴──────────────┘            └───────────────────────────────┴────────────┴─────────────┘
```

- The record and import cards are gone. **Записать звонок** and **Импортировать…** are toolbar buttons; the whole window is a drop target (a full-pane overlay "Отпустите, чтобы добавить 3 файла" appears on drag); a one-line drop hint stays under the table. Several files at once.
- Recording: the button opens a popover (microphone pop-up button, "Системный звук" switch with its one-sentence hint, consent line, **Начать запись**). While recording, the HUD pill is on every screen. "Параметры распознавания" moves to Settings → Запись и распознавание.
- Table columns: Источник (kind icon, name, kind), Участники, Дата, Объём, Требования ("17 · 1 на ревью"), Разбор (bar), Состояние.
- Click selects and fills the preview; double-click or ↵ opens. The preview: name, **Открыть транскрипт ↵**, summary, facts, "Удалить источник…".
- Primary: "К требованиям →" (or "Разобрать N требований →" when some wait).
- Row states: Распознаётся · 42% (spinner), В очереди · 2-й, Извлекаю требования · 6 из 14, Ждёт ревью, Разобран, Ошибка ("Не распознан: нет ffmpeg" in danger colour with **Повторить** in the row).
- Empty: §8.10.

### 8.3 Source `#/source/<id>`

Prototype: `shots/source-*.png`.

```
narrow                                                  wide
┌─[Все реплики|Только с требованиями]─🔍─┬──────────┐    ┌────────────────────────────┬───────────┬──────────────┐
│ 02:48 • Анна     text                  │ Сводка | │    │ transcript, lines ≤ 72 ch  │ Сводка    │ Требования   │
│ 03:30 • Ирина    text with ▓mark▓      │ Участники│    │                            │ Участники │ из источника │
│        [BR-1 …]                        │          │    │                            │           │              │
│ ...                                    │ summary  │    │                            │           │              │
├────────────────────────────────────────┤          │    ├────────────────────────────┤           │              │
│ ▶ 08:15 ▁▂▃▅▂▁▁▂▃ 52:04        1,25×   │          │    │ ▶ player                   │           │              │
└────────────────────────────────────────┴──────────┘    └────────────────────────────┴───────────┴──────────────┘
```

- Transcript line: time (mono), speaker (dot + name in the speaker colour), text (14/22). No card, no borders; 8 px between lines. The quoted part of a line has `--c-mark`; under the line, a chip per requirement made from it (type dot, id, statement, truncated at 44 characters). A rejected requirement's chip is struck through.
- The playing line has the accent bar and tint. Clicking a time seeks. The player is always visible at the bottom of the transcript pane: play, position, waveform, duration, speed. For sources without audio (documents, emails) the player is absent and times are replaced by page or paragraph numbers.
- "Участники" is a segment of the inspector: one row per speaker (dot, detected label, name field, share of talk time). Renaming applies everywhere.
- "Исправить текст" puts the focused line into a field; saving re-checks the quotes that use it.
- Inspector "Сводка": the summary as prose (max 72 characters per line), **Скопировать как письмо**, and under it **Обновить сводку**.
- Primary: "Требования из источника · 17 →" (opens Requirements filtered by this source). Before extraction the primary is "Извлечь требования"; while extracting, the pane shows the inline progress.
- States. Transcribing: the pane shows the skeleton of lines and the banner "Распознаю · 42% · осталось около 6 мин · Можно работать дальше". Summary error: a danger banner inside the inspector with "Открыть настройки". Summary missing: "Сводки ещё нет · Сделать сводку".

### 8.4 Requirements `#/atoms`

Prototype: `shots/atoms-*.png`, `shots/atoms-select-*.png`.

```
narrow                                                       wide
┌[На ревью 10|Принятые|Конфликты 2|Все]──🔍─┬────────────┐    ┌──────────────────────────────────┬────────────┬─────────────┐
│☐ Тип   Требование                 Статус │ NFR-3  ◷   │    │ + Источник  Спикер  Приоритет    │ inspector  │ source      │
│▌ NFR-3 Statement                  ◷ На   │ Statement  │    │                                  │            │ transcript  │
│        «quote»                    ревью  │ ┌conflict┐ │    │                                  │            │ at the      │
│        source · 21:03 · ⚠ конфликт       │ Свидет.    │    │                                  │            │ quote       │
│  NFR-7 ...                               │ Свойства   │    │                                  │            │             │
│                                          │ История    │    │                                  │            ├─────────────┤
│        ┌ Выбрано: 3 · Принять 2 A … ┐    ├────────────┤    │                                  ├────────────┤ ▶ 21:03     │
│                                          │[Принять A] │    │                                  │ [actions]  │             │
└──────────────────────────────────────────┴────────────┘    └──────────────────────────────────┴────────────┴─────────────┘
```

- Toolbar: view switch **Требования 20 | Для заказчика 3** (segmented), Добавить, primary "Собрать документ →" / "Обновить документ →". "Уточнить типы" moves to the palette and to a one-time inspector notice.
- Scope bar: status segmented control with counts (На ревью, Принятые, Отклонённые, **Конфликты**, Все), pop-up buttons Тип and Источник, Группировать (in "Ещё" below 1100 px), search. The screen opens on "На ревью" when anything waits, otherwise on "Все". Filters are stored per project.
- Conflicts are a filter, not a banner. A conflicted row says "Конфликт с NFR-7" in its meta line. The inspector shows the **conflict card** above the evidence: both sides A and B with speaker and date, and four buttons: Оставить A, Оставить B, Объединить…, Спросить заказчика.
- Inspector sections: statement (Title 2), conflict card, Свидетельство (source header, line before, the quoted line with `mark`, line after), Свойства (Тип and Приоритет as pop-up buttons, Спикер, В документах, Модель), История (date to the minute, action, author).
- Action bar: **Принять A**, Отклонить X (opens the reason menu: Не требование, Дубль, Вне рамок проекта, Ошибка распознавания), Править E. For a question: **Записать ответ**, Отправлен заказчику.
- Editing happens in the inspector: the statement becomes a field, "Исходная формулировка:" appears under it, Сохранить ⌘↵ / Отмена esc.
- After a decision the cursor moves to the next row that waits for review; the row leaves the list in 140 + 220 ms; a toast offers undo for 10 s.
- "Done" state (nothing to review and no open conflicts): the list pane shows the empty state "Все требования разобраны · Принято 19 из 20" with **Собрать документ**. With open conflicts: "Остался 1 конфликт" with **Разобрать конфликт**.
- **Для заказчика** view: list of questions, confirmations and action items (type, text, state: Открыт, Отправлен, Отвечен), inspector with the answer field and the source; primary "Составить письмо" opens the letter in the content pane with **Скопировать** and **Сохранить .eml**.
- States. No requirements: "Требований пока нет" with "К источникам". Extraction running: banner with progress, rows appear as they arrive. Error: banner with "Повторить".

### 8.5 Documents `#/document`

Prototype: `shots/document-*.png`, `shots/document-compare-*.png`.

```
narrow                                            wide
┌ SRS v2 • | BRD v1 | Реестр рисков v1 | + ───┐    ┌ tabs ─────────────────────────────────────────────────────────────┐
├──────────────────────────────┬──────────────┤    ├──────────┬──────────────────────┬──────────────┬─────────────────┤
│                              │[Качество 3|  │    │Содержание│                      │ Качество 3 … │ Откуда          │
│   ┌──────── paper ────────┐  │ Изменения|   │    │ 1 …      │   ┌──── paper ────┐  │ findings     │ требование FR-1 │
│   │ kicker                │  │ Сведения]    │    │ 3.2 •    │   │               │  │              │ transcript at   │
│   │ Title                 │  │ banner       │    │Версии    │   │               │  │              │ the quote       │
│ FR-2 text                 │  │ finding      │    │ v2 draft │   │               │  ├──────────────┤                 │
│   │ [source 08:15][DLR-1] │  │ finding      │    │ v1 sent  │   └───────────────┘  │[Применить все]│                │
└──────────────────────────────┴──────────────┘    └──────────┴──────────────────────┴──────────────┴─────────────────┘
```

- Tab strip `.doc-tabs`: one tab per document (short name, version, state dot), "+ Новый документ" opens a popover with the document types and what each takes ("SRS: функциональные, нефункциональные, вопросы"). The "Берёт: …" strip and the "В декомпозицию" switch move to the inspector segment **Сведения**, the switch with the label "Использовать для бэклога" and the sentence "Истории строятся из требований этого документа".
- Toolbar: Статус pop-up button (Черновик, На согласовании, Согласовано; the version number is in the status line), Сравнить с v1, Экспорт в Word ⌄ (menu: template, Markdown, Матрица трассировки), primary. The primary is **Обновить изменённое · N** when stale, else **К бэклогу →**. "Пересобрать весь документ…" is in the palette and in the Сведения segment, behind a sheet that says what is kept.
- Outline pane: Содержание (number, title, state dot: amber = stale or has a finding, red = conflict), then Версии (version, status, date, what happened). Clicking a version opens it read-only with a banner "Вы смотрите версию 1 · Вернуться к версии 2".
- Paper: kicker (Footnote), title (Large), H2 (Title 1), H3 (Title 2), body (Reading). Requirement block: id hangs in the left margin in the type colour; text; under it source chips and the Jira key chip, and at most one badge (stale, vague, conflict, fixed). Hover tints the block; click selects it, scrolls the inspector to its finding, and loads its evidence into the context pane. Stale block: 2 px amber rule on the left. Pinned own text: 2 px grey rule, `--c-fill-1`, caption "Свой текст · закреплён, пересборка его не изменит".
- Inspector segments: **Качество** (the single stale banner, then findings: kind, id, one sentence, the AI's proposed text, **Принять исправление**, Изменить…, Скрыть), **Изменения** (what changed since the previous version, from `/api/documents/<id>/changes`), **Сведения**. Action bar: **Применить все и обновить**, which accepts every proposed fix and rebuilds once.
- Accepting a fix patches the block in place and marks it "Исправлено"; the version number changes only on "Обновить" or "Применить все и обновить".
- Compare: two pages, older on the left, each under a label with version and status; changed blocks carry `ins`/`del` marks; scrolling is linked. Below 1400 px of workspace: one page with inline marks.
- States. No accepted requirements: empty state "Пока нечего собирать" with "К требованиям". Ready to build: "Можно собирать: 19 принятых требований" with **Собрать документ**. Building: skeleton page with the banner "Пишу документ · раздел 3 из 6". Updating: page at 60% opacity with the banner. Language mismatch: neutral banner with "Собрать на английском…". Error: danger banner, the last good version stays.

### 8.6 Backlog `#/backlog`

Prototype: `shots/backlog-*.png`.

```
narrow                                          wide
┌[Все 11|К выгрузке 10|С замечаниями 2]──────┬──────────┐   ┌──────────────────────────────────────────┬──────────┬────────────┐
│☑ Задача                         Jira       │ S История│   │☑ Задача   Критерии INVEST Треб. Приор. Jira│ story    │ Требование │
│☑ ⌄ E Epic title                 DLR-101    │ Title    │   │                                          │          │ FR-2 в     │
│☑   ⌄ S Story                    DLR-102    │ Как … я  │   │                                          │          │ документе  │
│☑       T sub-task               DLR-103    │ хочу …   │   │                                          │          │ + evidence │
│☐   › S Story                    —          │ Критерии │   │                                          │          │            │
│                                            ├──────────┤   │                                          ├──────────┤            │
│                                            │[Править] │   │                                          │[actions] │            │
└────────────────────────────────────────────┴──────────┘   └──────────────────────────────────────────┴──────────┴────────────┘
```

- The tree is an outline: one line per item. Epics open, stories closed. The whole backlog fits on a screen.
- Inspector for a story: title, story text ("**Как** … **я хочу** … **чтобы** …", Reading), INVEST finding as a warn banner with **Разделить**, Критерии приёмки (one card, each criterion as three lines Дано / Когда / Тогда with a 56 px label column), Свойства (Эпик, Требование with link, Приоритет, Выгружать switch, "Правки закреплены"), sub-tasks. Action bar: Править E, Подзадача, Удалить….
- Inspector for an epic: goal, its stories with states, NFRs linked with "В критерии".
- The checkbox column means "выгружать в Jira" and its header says so in a tooltip and in the inspector's switch label. Unticking an epic unticks its stories and says so in a toast with undo.
- Scope bar: Все, К выгрузке, С замечаниями; one warn banner when stories were built from changed requirements, with **Обновить истории**.
- Primary: "К выгрузке в Jira · 10 →". Secondary: Проверить по INVEST, История (new), Уточнить… (tb-opt). "Пересобрать…" is in the palette; when items have Jira keys the sheet lists them.
- States. No document: "Сначала нужен документ" with "К документам". Ready: "Можно собирать бэклог из документа v2" with **Собрать бэклог**. Building: skeleton tree with the banner "Пишу истории · 4 из 11".

### 8.7 Export `#/export`

Prototype: `shots/export-*.png`.

```
┌ Куда выгружать ─────┬──────────────────────────────────────────────────────────┐
│ ◆ Задачи в Jira     │ 10 создать  2 обновить  5 без изменений  6 пропустить  1 │
│   10 к выгрузке     │ ┌ info: предпросмотр ничего не меняет ────────────────┐  │
│ W Документы в Word  │ ☑ Задача          Тип  Требование Приоритет Ключ Действие│
│ ▦ Матрица трассир.  │ ☑ E Epic          Эпик                    DLR-101 Без изм.│
│ ✉ Письмо заказчику  │ ☑   S Story       История FR-2  Must      —       + Создать│
└─────────────────────┴──────────────────────────────────────────────────────────┘
```

- One place for everything that leaves the app. Master list of four destinations, each with its state in words.
- **Задачи в Jira**. Not connected: the detail pane is an empty state "Подключите Jira" with one sentence on what happens and **Подключить Jira**. Connected, no target: a form card (Сайт, Проект, the four issue types mapped by meaning) with **Сохранить**. Target set: the preview runs by itself; counts as large numbers with nouns; the table; orphans as rows with "Оставить" / "Закрыть с комментарием". The wizard header is removed; connection and target live in the pane's "Подключение" disclosure.
- Primary: "Выгрузить 12 задач в DLR ⌘↵" → sheet (§5.15) → result banner "Готово: 10 создано, 2 обновлено" and the Ключ column fills with links. Failed rows stay ticked with the reason and **Повторить**.
- **Документы в Word**: table of documents (name, version, status, template pop-up button, **Экспортировать**), "Экспортировать все".
- **Матрица трассировки**: a preview of the first 20 rows (Цитата, Требование, Раздел, История, Jira) and **Сохранить .xlsx**.
- **Письмо заказчику**: the letter, editable, with **Скопировать**, **Сохранить .eml**, "Отметить как отправленное".
- Stale upstream: warn banner "Документ изменился после сборки бэклога · Обновить истории".

### 8.8 Skills `#/skills`, `#/skills/<name>`

Prototype: `shots/skills-*.png`.

```
narrow                                         wide
┌ list ────────┬──────────────────────────┐    ┌ list ──────┬───────────────────────────────────────────┬──────────┐
│ Общее        │ Извлечение требований    │    │            │ title, description                        │ Сведения │
│  Общие инстр.│ [Свой] версия 3          │    │            │ Инструкции | Правила | Попробовать | …    │ Где      │
│ Источники    │ Инструкции|Правила|…     │    │            │ ┌ instructions ───┐ ┌ try-out: diff ────┐ │ использ. │
│  Сводка      │ ┌ instructions ────────┐ │    │            │ │                 │ │ + Появится        │ │ О скилле │
│  Извлечение ●│ │                      │ │    │            │ │                 │ │ − Исчезнет        │ │ История  │
│ Документы    │ └──────────────────────┘ │    │            │ └─────────────────┘ └───────────────────┘ │          │
└──────────────┴──────────────────────────┘    └────────────┴───────────────────────────────────────────┴──────────┘
```

- List grouped by where the skill works, in pipeline order: Общее, Источники, Документы, Бэклог, Шаблоны Word. Row: name, second line (Встроенный / Своя копия · изменён 22 сент. / Не используется), badge "Свой" for the user's skills only. "Встроенный" is not a badge.
- Editor: name (Title 1), badges, one paragraph of what the skill does and at which step. Tabs: Инструкции, Правила, Попробовать, Контракт, История (document types add Разделы; Word templates show Шаблон instead of Инструкции).
- Built-in skill: the editor is read-only with a lock line and the primary becomes **Сделать копию**.
- **Попробовать**: source pop-up button, **Запустить ⌘↵**, then the result as a diff against what the project has: Появится, Исчезнет, Без изменений. At workspace ≥ 2000 px the instructions and the try-out sit side by side, so a change can be tested without leaving the text.
- Inspector: **Где используется** (one switch per scope with a sentence: this project, other and new projects), О скилле, История with "Вернуть эту версию", "Удалить скилл…". Below 1200 px of workspace these are the tab **Сведения**.
- Primary: Сохранить ⌘S (disabled with no changes; "Есть несохранённые изменения" above the editor when there are). Leaving with changes opens a sheet: Сохранить, Не сохранять, Отмена.

### 8.9 Settings `#/settings`

Prototype: `shots/settings-*.png`.

- Outline with categories: Проект, Модель ИИ, Запись и распознавание, Jira, Вид и язык, О программе. The form pane shows the chosen category and the ones after it, scrolling; the outline follows the scroll.
- Form groups are `.form-card`s: label (500) and one sentence (Footnote) on the left, control on the right, 52 px minimum row.
- Модель ИИ: provider segmented control (Claude · облако, Встроенная, Ollama); each option shows its own rows. Key field with **Проверить** and the result in words under it. Local models as rows with size, memory need, "Подходит этому компьютеру", and **Скачать 6,5 ГБ** → progress → "Установлена · Удалить…".
- Context pane at workspace ≥ 1800 px: **Состояние системы** (computer, acceleration, free disk, ASR model, speaker separation, ffmpeg, data folder, version). Below that width it is the category "О программе".
- No primary button: every control saves on change and confirms with a toast "Сохранено". Keys and tokens save on **Проверить**.
- Arriving from an error ("Открыть настройки"): the toolbar shows a back button "Вернуться: Интервью…", the needed row is scrolled into view and ringed for 1200 ms.

### 8.10 Onboarding and first run

First run is not a wizard and not a separate screen. `#/sources` of an empty project shows, in the content pane, a single column 560 px wide:

```
        [glyph]
   С чего начать
   Три шага, около двух минут.

   1  Назовите проект          [ Портал дилера        ]          ✓
   2  Выберите, где работает ИИ  (Claude · облако | Встроенная)   [Проверить]
   3  Добавьте первый источник   [Записать звонок] [Импортировать…]

   Или откройте пример: «Демо: CRM контакт-центра»
```

- Each step is a row; a done step shows a green check and collapses to one line. Step 3 is disabled until step 2 passes, with the sentence "Сначала проверьте ИИ: без него не будет сводки и требований".
- The sidebar shows the pipeline with empty rings from the first second, so the whole path is visible.
- The example project is read-only data shipped with the app; it opens like any project and can be deleted.
- After the first source is added the screen becomes the normal Sources table and the start screen becomes Overview.
- Optional set-up (speaker separation token, Jira) is never asked up front. It appears where it is first needed, as an inspector notice with one button.

---

## 9. The main flow, step by step

| # | The BA does | The app does | Screen after |
|---|---|---|---|
| 1 | Drops `call.m4a` on the window (or ⌘O, or ⌘R to record) | Adds the source, starts transcription; job card shows progress; row says "Распознаётся · 12%" | Sources |
| 2 | Keeps working elsewhere | When transcription ends: summary and extraction run by themselves (project setting); system notification "Созвон готов · 12 требований на ревью" | any |
| 3 | Clicks the primary "Разобрать 12 требований →" (or ⌘2) | Opens Requirements on "На ревью", cursor on the first row, inspector filled | Requirements |
| 4 | Reads statement and quote; presses A, X (then a reason), or E | Row leaves, cursor moves on, toast with undo; counts in scope bar, toolbar and sidebar update | Requirements |
| 5 | Reaches a conflict (or presses 4 for "Конфликты") | Inspector shows A and B | Requirements |
| 6 | "Оставить B" or "Спросить заказчика" | Resolves; the question appears in "Для заказчика" | Requirements |
| 7 | Nothing left to review: presses ⌘↵ "Собрать документ →" | Popover with document types if none exists, else goes on | Documents |
| 8 | Chooses "SRS", **Собрать** | Skeleton page with progress; then the page; the quality check runs by itself; inspector opens on "Качество 3" | Documents |
| 9 | Presses `]` to go through findings; F accepts a fix, or "Изменить…" | The block is patched in place and marked "Исправлено" | Documents |
| 10 | "Применить все и обновить" | One rebuild, one new version | Documents |
| 11 | Sets Статус → "На согласовании"; "Экспорт в Word" | Saves the file; version is marked as sent | Documents |
| 12 | Primary "К бэклогу →", then **Собрать бэклог** | Skeleton tree with progress; then the outline | Backlog |
| 13 | Goes down the stories with ↓, reads each in the inspector; Space unticks what should not go to Jira; "Проверить по INVEST" | Findings appear in the INVEST column and in the inspector | Backlog |
| 14 | Primary "К выгрузке в Jira · 10 →" | Preview runs by itself | Export |
| 15 | ⌘↵, reads the sheet, ⌘↵ | Pushes; result banner; keys appear in Export, Backlog and on the paper | Export |
| 16 | "Письмо заказчику" → **Скопировать** | Letter with open questions and action items | Export |

Clicks from a dropped file to issues in Jira, with no edits: 9 (steps 3, 7, 8, 10, 12 twice, 14, 15 twice), plus one key per requirement.

---

## 10. Microcopy

### 10.1 Rules for both languages

1. **A button is a verb plus its object**: "Собрать документ", "Export to Word". Not "OK", "Да", "Готово", "Submit".
2. **No bare icons** for anything destructive or not universally known. Bare icons are allowed only for: sidebar, inspector, theme, back, play/pause, close. Each has `aria-label` and a tooltip.
3. **Destructive and outgoing actions end with "…"** and open a sheet: "Удалить источник…", "Отправить в архив…", "Пересобрать весь документ…". The confirming button repeats the verb and the target: "Да, выгрузить в DLR".
4. **Counts go on the button** when the action applies to a number of things: "Разобрать 10 требований", "Обновить изменённое · 2".
5. **An arrow after the label** means another screen. No arrow means the action happens here.
6. **Status is an adjective or a participle, one or two words, capitalised**: Принято, На ревью, Устарел, Draft, Out of date.
7. **Tooltips**: appear after 400 ms; say what the control does in up to 6 words, then the key after " · ": "Скрыть или показать инспектор · ⌥⌘I". A tooltip never holds information that is needed to use the control.
8. **Every switch and every choice has one sentence under its label** that says what changes.
9. **Errors say what happened, then what to do**, and carry the button: "Anthropic отклонил ключ. Проверьте его в настройках. [Открыть настройки]". No codes, no "Ошибка:".
10. **Empty states say what will be here and how to get it.** One action.
11. **Numbers**: RU uses a comma for decimals and a narrow no-break space for thousands ("6,5 ГБ", "180 000 ₽"); EN uses a point and a comma. Dates: RU "24 сент., 10:42", EN "24 Sep, 10:42". Today and yesterday are words. Seconds are never shown.
12. **Plurals** go through the i18n plural function for every count (RU one / few / many: "1 требование, 3 требования, 10 требований").
13. **Sentence case.** No full stop in labels, buttons, tooltips and statuses. Full stop in sentences.
14. **Progress text is translated in the frontend** from the backend's message (`lib/progress.js`), never shown raw.
15. **Internal words stay inside**: no "атом", "скилл-стадия", "job", "MCP", "FRD" in labels. "Atom" → "требование" / "requirement". Skill stays "скилл" / "skill" (it is the product's word).

### 10.2 Renames

| Today (RU) | New (RU) | New (EN) |
|---|---|---|
| Атомы, Атомы требований | Требования | Requirements |
| Декомпозиция | Бэклог | Backlog |
| Выгрузка в Jira (screen) | Выгрузка | Export |
| N атомов → (button) | Требования из источника · N → | Requirements from this source · N → |
| Суммировать | Сделать сводку / Обновить сводку | Summarise / Update summary |
| Извлечь заново | Извлечь заново… | Extract again… |
| Экспорт DOCX | Экспорт в Word | Export to Word |
| Пересобрать (document) | Обновить изменённое · N | Update changes · N |
| К декомпозиции | К бэклогу | To backlog |
| В декомпозицию (switch) | Использовать для бэклога | Use for the backlog |
| Уточнить типы | Уточнить типы требований… | Re-check requirement types… |
| Разобрать (conflicts banner) | filter "Конфликты N" + "Разобрать конфликт" | "Conflicts N" + "Resolve conflict" |
| встроенный (tag) | Встроенный (second line) | Built-in |
| функц., нефункц. (tags) | FR, NFR (codes; full name in tooltip and inspector) | FR, NFR |
| Облачный ИИ | Claude · облако | Claude · cloud |
| готово (source status) | Разобран / Ждёт ревью | Reviewed / Waiting for review |

Strings the e2e suites look for (§12) keep their exact text unless the table above renames them; renamed ones are updated in the suites in the same commit.

---

## 11. Implementation plan

Each phase ends with a working app, `npm run build`, and the e2e suites green. Do not start a phase before the previous one is merged. No change to `app.py`, `core/` or the API in any phase.

### Phase 0. Tokens and base (1 to 2 days)

| File | Change |
|---|---|
| `frontend/src/tokens.css` (new) | paste §4 |
| `frontend/src/app.css` | import tokens; keep the old variable names as aliases (`--paper: var(--c-window)`, `--panel: var(--c-content)`, `--sunk: var(--c-fill-1)`, `--ink: var(--c-text)`, `--ink-2: var(--c-text-2)`, `--ink-3: var(--c-text-3)`, `--rule: var(--c-line)`, `--rule-2: var(--c-line-strong)`, `--accent: var(--c-accent-text)`, `--primary: var(--c-accent)`, and the space, radius and type scales); replace base rules with the prototype's base, buttons, seg, tabs, switch, checkbox, field, search, menu, banner, badge, status, type, chip, kbd, toast, scrollbars, focus |
| `frontend/src/main.js` | import `tokens.css` before `app.css` |
| `frontend/src/lib/state.svelte.js` | `applyTheme` sets `data-theme` on `<html>` only when the user chose a theme; "system" removes the attribute |
| `frontend/src/components/Icon.svelte` | replace the path set with the prototype's sprite; add `wave, atoms, tree, inspector, sidebar, compare, word, jira, table, spark, updown` |

Check: recompute the contrast table with the final values.

### Phase 1. Shell (3 to 4 days)

| File | Change |
|---|---|
| `frontend/src/App.svelte` | `.app` grid; `<Sidebar/>`, `<Toolbar/>`, `.workspace`; window no longer scrolls (remove `onscroll`); add `overview` route; add `<CommandPalette/>`, `<Sheet/>`, `<RecordingHud/>`, `<Toasts/>`; global keys from §6 |
| `frontend/src/components/Rail.svelte` → `Sidebar.svelte` | keep `nav.rail` class and `aria-label="Main"` (add class `sidebar`); stage rings; status words; children for sources and documents; job card; rail mode. Keep `.proj` on the project button |
| `frontend/src/components/Toolbar.svelte` (new) | props: `title`, `crumb`, `sub`, snippets `actions` and `primary`; renders `.screen-head` (kept as a second class on `.toolbar`), `.screen-title` on the `h1`, `.screen-sub` on the status line |
| `frontend/src/components/Panes.svelte` (new) | the pane grid, container queries, dividers with drag, overlay inspector |
| `frontend/src/components/Inspector.svelte` (new) | head, body, action bar, empty and multi-select states |
| `frontend/src/components/CommandPalette.svelte` (new) | data: routes, `app.sources`, atoms, documents, backlog items, commands registered by screens |
| `frontend/src/components/Sheet.svelte`, `EmptyState.svelte`, `Kbd.svelte`, `Menu.svelte`, `StageRing.svelte`, `JobCard.svelte`, `RecordingHud.svelte` (new) | per §5 |
| `frontend/src/components/Toast.svelte` | stack of 2, 10 s, pause on hover, offset when the bulk bar is up; keep `role="status"` |
| `frontend/src/lib/state.svelte.js` | `app.inspector[screen]`, `app.paneWidths`, `app.commands`; filters stored per project |
| `frontend/src/lib/i18n.js` | new keys for shell, palette, keys list; renames from §10.2 (both languages) |

Screens are wrapped as they are, each in one content pane, so the app works after this phase.

### Phase 2. Requirements (3 to 4 days)

`frontend/src/screens/Atoms.svelte`, `frontend/src/components/AtomInspector.svelte`, `frontend/src/components/OpenItems.svelte`, `frontend/src/lib/atoms.js`. List rows and columns, scope bar, conflict as a filter and an inspector card, bulk bar, context pane (uses `GET /api/sources/<id>` and scrolls to the evidence segment), "Для заказчика" view, editing in the inspector, reject reasons menu.

### Phase 3. Sources, Source, Overview (3 to 4 days)

`frontend/src/screens/Sources.svelte` (table, preview, window drop target, record popover, first-run state), `frontend/src/screens/Transcript.svelte` (lines, chips, player bar, inspector segments, context pane), `frontend/src/components/ProjectHome.svelte` → `frontend/src/screens/Overview.svelte`, `frontend/src/lib/recorder.js` (only what the HUD needs to read: timer, level).

### Phase 4. Documents (4 to 5 days)

`frontend/src/screens/Document.svelte`: split into `DocumentPaper.svelte`, `DocumentOutline.svelte`, `DocumentFindings.svelte`, `DocumentCompare.svelte`. Tabs, outline with versions, paper, inspector segments, compare in two pages, in-place fix, status pop-up button, export menu.

### Phase 5. Backlog and Export (4 days)

`frontend/src/screens/Backlog.svelte` (outline tree, story inspector, context pane), `frontend/src/screens/Export.svelte` (destinations list; Jira pane with connection, target, preview, sheet; Word, traceability and letter panes using the existing endpoints `export.docx`, `export.md`, `traceability.xlsx`, `followup`).

### Phase 6. Skills and Settings (3 days)

`frontend/src/screens/Skills.svelte` (grouped list, editor tabs, try-out diff, inspector), `frontend/src/screens/Settings.svelte` (categories, form cards, system state pane), `frontend/src/components/LocalModel.svelte`, `frontend/src/components/Block.svelte` (delete when no screen uses it).

### Phase 7. Finish (2 to 3 days)

Motion pass (§4.6), reduced motion and reduced transparency, `prefers-contrast`, keyboard list (`?`), tooltips, RU and EN review of every string against §10, Windows check in WebView2 (fonts, scrollbars, `backdrop-filter`), screenshots of every screen at 1024, 1280, 1728, 2560 and 3840 in both themes into `docs/design/current/`, remove the variable aliases from phase 0, delete `docs/design/design-system.md` and `docs/design/prototype.html` or mark them superseded.

Total: 23 to 29 working days for one engineer.

---

## 12. What the e2e suites depend on

Read from `frontend/e2e/atoms.mjs`, `backlog.mjs`, `bulk.mjs`, `document.mjs`, `export.mjs`, `skills.mjs`, `smoke.mjs`. "Keep" means the selector must still match the same element with the same meaning. "Update" means change the app and the suite in one commit.

### 12.1 Classes and ids

| Selector | Used for | Decision |
|---|---|---|
| `.rail` | sidebar root | Keep (second class on `.sidebar`) |
| `.proj` | project button | Keep |
| `.screen-head` | toolbar; suites look for buttons and a file input inside it | Keep as a class on `.toolbar`. The Skills import `input[type=file]` must stay inside it |
| `.screen-title`, `.screen-sub` | title and status line; suites read "N на ревью · принято N из N", "версия 1 · 3 требования", "историй: 2", "SBX · Sandbox" | Keep classes. **Update** the texts if the status line wording changes: Requirements keeps "N на ревью · принято N из N"; Documents becomes "Версия 1 · …" (capitalised) → update `document.mjs`, `export.mjs`; Backlog "историй: 2" becomes "2 истории" → update `backlog.mjs`, `export.mjs` |
| `input[type=file]` (first in page) | import on Sources | Keep: a hidden input in the Sources screen, first in DOM order |
| `.seg-row`, `.seg-row.flash`, `.seg-row .spk`, `.seg-meta` | transcript line, evidence flash, speaker name | Keep on the new line element (`.seg-line` gets `.seg-row` too) |
| `.speaker input` | speaker rename | Keep, now inside the inspector segment "Участники". **Update** `smoke.mjs` to open that segment first |
| `.atom`, `.atom .type`, `.atom .quote`, `.atom .row-check`, `.atom textarea` | requirement row | Keep `.atom` on `.row`, `.type` on the marker, `.quote` on the quote, `.row-check` on the checkbox. **Update**: the edit `textarea` moves to the inspector → `atoms.mjs` looks for `.inspector textarea` |
| `.check-all input` | select all | Keep (wrap the header checkbox in `.check-all`) |
| `.bulkbar`, `.bulkbar b`, `.bulkbar select.type-select` | bulk bar | Keep `.bulkbar` on `.bulk`, the count in `<b>`. **Update**: the type `select` becomes a menu button → `bulk.mjs` clicks "Тип…" then the item |
| `.pill` with "вопросы" | type filter | **Update**: type filter is a pop-up menu → `atoms.mjs` opens "Тип" and picks "Вопросы" |
| `.src-select`, `.src-select option:checked` | source filter | **Update**: pop-up menu "Источник" |
| `.conflict`, `.cf-head` | conflict card and its header | Keep both classes on the inspector card. **Update** the step that opens it: click the "Конфликты" filter, not "Разобрать" on a banner |
| `.doc-tabs [role=tab]` | document tabs | Keep |
| `.title-input` | new document name | Keep (in the "Новый документ" popover) |
| `#sec-purpose`, `#sec-purpose textarea`, `#sec-purpose .blk.free` | section anchor, own text | Keep ids `sec-<key>` and classes `.blk.free` |
| `#blk-FR-1`, `#blk-FR-1 .src[aria-label="из атома, 1 источник"]` | requirement block and its source chip | Keep id `blk-<ID>` and `.src` on the chip. Keep the `aria-label` text as is, or **update** to "из требования, 1 источник" together with `document.mjs` |
| `.sec h2`, `.sec h3` | section headings on the paper | Keep `.sec` wrapper |
| `.finding` | quality finding | Keep |
| `.change` | item in "Изменения" | Keep |
| `.out-lang` | output language note | Keep |
| `select.tpl` | Word template choice | **Update**: becomes the menu of "Экспорт в Word ⌄"; `document.mjs` picks the item |
| `.node.epic`, `.node.story`, `.node.sub`, `.node.nfr`, `> .row-line`, `.inc` | tree rows and the "выгружать" checkbox | Keep `.node.*`; keep `.row-line` as the row's inner element and `.inc` on the checkbox |
| `.epic .t` | epic title | Keep `.t` on the title span |
| `.story .acs b`, `.story .refs .link`, `.ac-edit`, `.invest`, `.row-note` | story details | **Update**: details move to the inspector. Keep the classes there (`.acs`, `.refs .link`, `.ac-edit`, `.invest`, `.row-note`) and wrap the inspector body in `.story`; `backlog.mjs` selects the story row first |
| `.counts` | Jira preview counts | Keep; texts "создать: 3", "пропустить: 5", "без изменений: 3" are read → either keep a visually hidden line with these strings or **update** `export.mjs` to the new "3 создать" form |
| `#jr-project`, `.types select` | Jira target form | Keep (native selects styled as pop-up buttons) |
| `.result a`, `.result h4` | push result links; skill try-out result | Keep |
| `.list`, `.item`, `.e-title h2`, `.editor input[type=file]`, `#sk-instr`, `.rule`, `.sec-row`, `.h-text`, `.block-title` | Skills list, editor title, template upload, instructions field, rules, sections, history | Keep all. `.list` is the skills list container: do not reuse the class name `.list` for the requirements list in Svelte global CSS (the prototype's `.list` becomes `.rows`) |

### 12.2 Roles, labels and texts

Buttons by name (keep the exact text or update the suite in the same commit):
"Импортировать и суммировать", "Извлечь требования", "Собрать документ", "Собрать бэклог", "Обновить изменённое", "Пересобрать", "Экспорт DOCX" (**renamed** "Экспорт в Word"), "Сравнить с v1", "Скрыть сравнение", "Свой текст", "Раздел, который напишет ИИ", "Править", "Править атом" (**renamed** "Править требование"), "Починить" (**renamed** "Принять исправление" is a different step: keep "Починить" as the button that asks the AI for a fix when none is proposed yet), "Принять в атом" (**renamed** "Принять в требование"), "Применить", "Отклонить", "Отменить", "Удалить", "Вернуть", "В вопрос" (**renamed** "Спросить заказчика"), "В критерии", "Критерий", "Проверить по INVEST", "К декомпозиции" (**renamed** "К бэклогу"), "К выгрузке в Jira", "Подключить Jira", "Сохранить", "Показать", "Обновить" / "Показать предпросмотр", "Выгрузить 3 задачи", "Да, выгрузить в SBX", "Сделать копию", "Создать", "Создать документ этого типа", "Добавить правило", "Запустить", "Экспорт .zip" (**renamed** "Экспорт в .zip"), "Скачать шаблон", "Настройки", "Скиллы", "Все источники", "Русский", "English", "N атома" (regexp `^N атом`, **renamed** "Требования из источника · N"), filter buttons `^все` and `^вопросы` (**changed** to the segmented control and the type menu), bulk button matching `конфликтные`.

Other roles: `getByRole("status")` (toasts: keep `role="status"`), `getByRole("tab", …)` for "Разделы", "История", "Правила", "Попробовать" (keep `role="tab"` in the skill editor), `getByRole("heading", { name: "Источники" })` and `"Settings"` (the toolbar `h1`), `getByRole("group", { name: "Язык интерфейса" / "Interface language" })` (keep `role="group"` and the label on the language segmented control).

Placeholders: "Название", "Название проекта", "Название (рус.)", "Что проверять", "Что ИИ должен написать в этом разделе". Keep.

Texts waited for: "Все атомы разобраны" (**renamed** "Все требования разобраны"), "Атомов пока нет" (**renamed** "Требований пока нет"), "Пока пусто", "Пока нечего собирать", "Сначала нужен документ", "Можно собирать: 3 принятых атома" (**renamed** "…3 принятых требования"), "Можно собирать бэклог из документа v1", "Атом обновлён — пересоберите документ" (**renamed** "Требование обновлено. Обновите документ"), "Изменено 3 атома", "Удалён 1 атом", "Удалено 6 атомов" (**renamed** with "требование"), "в конфликтах: N", "N конфликт… не разрешён", "ждёт ответа заказчика", "разделы 3.1 устарели", "После сборки изменилось 1 требование", "размыто", "изменено", "сгенерировано", "удалён", "Исходная формулировка:", "Сохранено (версия 2)", "Копия создана", "Шаблон обновлён", "Встроенный скилл нельзя менять", "Есть несохранённые изменения", "Типы документов" (**changed**: the group is now "Документы" → update `skills.mjs`), "Скилл «…» импортирован", "Собрано N истори…", "Перенесено в критерии", "Текст истории обновлён", "Цель: …", "Создать или обновить 3 задачи в проекте SBX (sandbox.atlassian.net)?" (**changed** to the sheet title "Выгрузить 3 задачи в проект SBX?" with the site in the facts list → update `export.mjs`), "Готово: 3 задачи", "подключено", "Доступ к сайтам: sandbox.atlassian.net", "Jira подключена", "Документ собран на русском, а язык проекта — на английском".

Keys pressed by the suites: `a`, `x`, `e`, Space, `Delete`, `Escape`, ⌘/Ctrl+A, ⌘/Ctrl+S. All keep their meaning. `Delete` on Requirements deletes the checked rows after a sheet; if the suite expects no confirmation, **update** `bulk.mjs` to confirm.

### 12.3 Behaviour the suites assume

- The window used to scroll; suites use `fullPage` screenshots. With panes, `fullPage` equals the viewport. No assertion depends on it.
- `export.mjs` follows the wizard order (connect, target, preview). The new Jira pane shows the same three states in the same order, so only the locators in the table change.
- Suites navigate with `page.goto("#/…")`. All routes stay.

---

## 13. Not verified

- The prototype was rendered in Playwright WebKit only. It was not run inside pywebview, and not in WebView2 on Windows. `backdrop-filter`, container queries, `text-wrap: pretty`, `color-mix()` and `prefers-reduced-transparency` need a check there; all have fallbacks or degrade to the plain look.
- Window vibrancy behind the sidebar needs a native change in the pywebview window and is outside this spec. Without it the sidebar is a flat tint, which is what the screenshots show.
- The current app was reviewed on a small demo project with the fake AI (2 sources, 17 requirements, 1 document, 22 backlog items). The owner's real library was not opened. Density at 500+ requirements is designed for (one-line-per-item tree, table columns, grouping) but not measured.
- Dragging pane dividers and the overlay inspector are specified, not built in the prototype.
- The EN interface is specified in §10 but the prototype is in Russian only.
- Contrast was computed for solid colours; text over the translucent sidebar and toolbar was computed against their solid fallbacks, not against what may show through.
