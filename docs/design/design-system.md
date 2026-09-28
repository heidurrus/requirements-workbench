# Requirements Workbench design system (proposal)

This is the proposed system behind `prototype.html`. Every value below is used in the prototype's `:root`, so you can inspect it there. The last section maps it onto the existing variables in `frontend/src/app.css` for a step-by-step migration.

---

## 1. Principles

1. **The content is the interface.** Chrome stays neutral and quiet. Colour goes on status and on *one* primary action per screen. The BA's material (atoms, requirements, stories) is the only thing on screen that's allowed to be loud.
2. **The main task is above the fold.** Each screen opens on its main work area. Secondary things like conflicts, settings and history show up as a one-line summary that expands in place, not as a wall of cards.
3. **One toolbar, one place for the next step.** Every screen has a sticky toolbar: the title and state on the left, actions on the right, and the one prominent action last. Users learn it once.
4. **Dense but legible.** 13 px UI text, 14 px for items being reviewed, 15/24 for reading. Rows are 36–44 px. Row actions appear on hover or focus. Numbers use tabular figures.
5. **Keyboard first, visibly.** Every repeated action has a key, and the key is printed where the action is (`Принять A`). Focus is always visible and never confused with selection.
6. **Trust through provenance.** Every derived item shows where it came from (a source chip, a timestamp, an FRD reference). Irreversible or external actions (a Jira push) always go through a confirmation that states the facts.
7. **Designed for long Russian strings.** Labels wrap before they truncate. When truncation is unavoidable it uses an ellipsis on the full string plus a `title`. Controls size to their content, never to a fixed width.
8. **Calm motion.** 120–240 ms, ease-out, used only to show where something came from or went (expand, sheet, HUD). With `prefers-reduced-motion`, motion becomes a 1 ms change.

---

## 2. Color

Neutral surfaces with a slight warm tint in light mode and a neutral graphite in dark mode. There's a single blue accent (a continuation of today's #2B5B78) and five semantic hues. Each token has one **role**, following the Geist idea that backgrounds, lines and text each get their own steps.

### 2.1 Tokens

| Role | Token | Light | Dark | Notes |
|---|---|---|---|---|
| Window canvas | `--bg` | `#F5F5F3` | `#141517` | the page behind cards |
| Sidebar material | `--sidebar` | `#ECECE9` | `#18191C` | 88 % + `backdrop-filter: blur(24px) saturate(1.4)` where supported |
| Surface | `--surface` | `#FFFFFF` | `#1C1D20` | cards, rows, paper, inputs |
| Sunk / hover | `--surface-2` | `#EEEEEB` | `#25272B` | segmented track, hover rows, code, quotes |
| Pressed | `--surface-3` | `#E6E6E2` | `#2D2F34` | pressed buttons, sidebar hover |
| Text primary | `--text` | `#1B1C1F` | `#ECECEE` | |
| Text secondary | `--text-2` | `#55585F` | `#A8ABB2` | quotes, descriptions |
| Text tertiary | `--text-3` | `#63666D` | `#8A8D95` | meta, counts, hints (passes AA, unlike today) |
| Separator | `--line` | `#E1E1DD` | `#26282C` | decorative, between rows |
| Card edge | `--line-strong` | `#CFCFCA` | `#303237` | card and button rings (used as a 1-px shadow) |
| Control boundary | `--line-control` | `#8B8E95` | `#6C7078` | inputs, checkboxes, switches, drop zone. ≥ 3:1 |
| Accent (text/icon) | `--accent` | `#245E92` | `#86B8EC` | links, selected icons, IDs |
| Accent tint | `--accent-bg` | `#E3EDF7` | `#1E2D3E` | selection, functional tag, info banner |
| Accent line | `--accent-line` | `#A9C5E2` | `#34506F` | pressed chip ring, focus-row ring |
| **Primary fill** | `--primary` / `--primary-hover` | `#245E92` / `#1D5282` | `#2F6DAE` / `#3A7BBE` | white text in **both** themes (fixes the "disabled-looking" dark primary) |
| Focus ring | `--focus` | `#2A6FB0` | `#6AA6E8` | 2 px, 2 px offset |
| Success | `--ok` / `--ok-bg` | `#2B6841` / `#E2F0E6` | `#7CCB95` / `#1B3124` | принят, готово, создать |
| Warning | `--warn` / `--warn-bg` | `#845400` / `#F8ECD3` | `#E5B65E` / `#342A15` | устарел, INVEST, размыто |
| Danger | `--danger` / `--danger-bg` | `#A3352A` / `#F9E5E1` | `#F29C8C` / `#3A211D` | конфликт, ошибка |
| Danger fill | `--danger-fill` | `#A3352A` | `#B8463A` | destructive buttons (white text) |
| Question | `--q` / `--q-bg` | `#62479E` / `#EEE9F8` | `#BCA6F0` / `#2A2340` | вопрос / Q-n |
| NFR | `--nfr` / `--nfr-bg` | `#1F6770` / `#DFF0F1` | `#7CCDD5` / `#17313A` | нефункц. / NFR-n |
| Recording | `--rec` | `#D1382B` | `#FF6B5E` | record button, recording HUD |
| Evidence highlight | `--mark` | `#FAEDB0` | `#4A4020` | quote in transcript and inspector |
| Diff | `--ins` / `--del` | `#DDF1E2` / `#FBE3DF` | `#1B3124` / `#3A211D` | document comparison |
| HUD material | `--hud` · `--hud-text` · `--hud-text-2` · `--hud-line` | `#232427` · `#F2F2F4` · `#B5B7BD` · `#3A3B40` | `#2A2B2F` · same · same · `#3D3F45` | bulk bar, toasts, recording pill. Always dark: an overlay layer, as in Raycast and macOS HUDs |
| Scrim | `--overlay` | `rgba(20,21,23,.32)` | `rgba(0,0,0,.55)` | behind sheets |

**Type colours:** functional = accent, NFR = teal, question = violet. **Status colours:** accepted = green, rejected = neutral with strikethrough, conflict = red. Every coloured element also carries a text label (NFR-A11Y-02).

**Backlog type glyphs** are 18-px squares with a white letter: epic `#7A5AC8` "E", story `#3F8A55` "S", task `#3F7DC0` "T", sub-task `#8B8E95` "·". They match Jira's semantics without using Jira's assets.

### 2.2 Contrast (WCAG 2.1 AA), measured

Relative-luminance ratios, computed with the WCAG formula:

| Foreground | on Background | Light | Dark | Needs |
|---|---|---|---|---|
| `--text` | `--bg` | 15.61 | 15.49 | 4.5:1 |
| `--text` | `--surface` | 17.04 | 14.29 | 4.5:1 |
| `--text-2` | `--bg` | 6.53 | 7.95 | 4.5:1 |
| `--text-2` | `--surface-2` | 6.13 | 6.51 | 4.5:1 |
| `--text-3` | `--bg` | 5.27 | 5.50 | 4.5:1 |
| `--text-3` | `--surface` | 5.75 | 5.08 | 4.5:1 |
| `--text-3` | `--surface-2` | 4.95 | 4.51 | 4.5:1 |
| `--text-3` | `--sidebar` | 4.86 | 5.29 | 4.5:1 |
| `--accent` | `--surface` | 6.79 | 8.09 | 4.5:1 |
| `--accent` | `--accent-bg` | 5.73 | 6.72 | 4.5:1 |
| `#FFFFFF` | `--primary` | 6.79 | 5.36 | 4.5:1 |
| `--ok` | `--ok-bg` | 5.65 | 7.17 | 4.5:1 |
| `--warn` | `--warn-bg` | 5.52 | 7.52 | 4.5:1 |
| `--danger` | `--danger-bg` | 5.59 | 7.00 | 4.5:1 |
| `#FFFFFF` | `--danger-fill` | 6.77 | 5.28 | 4.5:1 |
| `--q` | `--q-bg` | 6.06 | 6.97 | 4.5:1 |
| `--nfr` | `--nfr-bg` | 5.53 | 7.52 | 4.5:1 |
| `--text` | `--mark` | 14.45 | 8.70 | 4.5:1 |
| `--line-control` | `--surface` | 3.28 | 3.39 | 3:1 (UI) |
| `--line-control` | `--bg` | 3.01 | 3.68 | 3:1 (UI) |
| `--focus` | `--surface` | 5.25 | 6.61 | 3:1 (UI) |
| `--focus` | `--bg` | 4.81 | 7.16 | 3:1 (UI) |
| `--hud-text` | `--hud` | 13.88 | 12.65 | 4.5:1 |
| `--hud-text-2` | `--hud` | 7.74 | 7.05 | 4.5:1 |

**Rules:**

- `--text-3` is the *lightest* text allowed. There's no `--text-4`, so placeholder text also uses `--text-3`.
- `--line` and `--line-strong` are decorative only. Anything that marks the boundary of an interactive control uses `--line-control`, or it's a button whose label identifies it.
- Disabled controls use `opacity: .45` **and** `pointer-events: none`, and are never the only primary on screen. Prefer hiding an action, or explaining why it's unavailable, over showing a disabled primary.
- **Increased contrast (proposal):** under `@media (prefers-contrast: more)`, set `--text-2: var(--text)`, `--text-3: var(--text-2)`, and `--line-strong: var(--line-control)`.

---

## 3. Typography

System fonts only: they're fast, native and Cyrillic-complete. **Drop the unbundled "IBM Plex Sans"** so every machine renders the same metrics.

```css
--font:         -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, "Noto Sans", Roboto, sans-serif;
--font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif;
--mono:         ui-monospace, "SF Mono", "Cascadia Mono", Consolas, Menlo, monospace;
```

SF Pro, Segoe UI Variable, Cascadia Mono and SF Mono all include Cyrillic. In WKWebView, `-apple-system` switches between Text and Display optical sizes automatically. On Windows, WebView2 picks up Segoe UI Variable.

### 3.1 Scale (px; based on macOS text styles)

| Token | Size / line | Weight | macOS analogue | Used for |
|---|---|---|---|---|
| `--fs-11` | 11 / 14 | 500–600 | Caption 1 | tags, table headers, sidebar group labels, kbd |
| `--fs-12` | 12 / 16 | 400 | Footnote | meta lines, toolbar subtitle, hints |
| `--fs-13` | 13 / 18 | 400 / 500 / 600 | **Body** / Headline | default UI, buttons, card titles (600) |
| `--fs-14` | 14 / 20 | 500 | — | *items under review*: atom statements, transcript text, story text |
| `--fs-15` | 15 / 20 (UI) · 15 / 24 (reading) | 600 / 400 | Title 3 | toolbar title, empty-state title, **document body** |
| `--fs-17` | 17 / 24 | 600 | Title 2 | document H2, skill editor title |
| `--fs-22` | 22 / 28 | 600 | Title 1 | reserved (onboarding) |
| `--fs-26` | 26 / 32 | 700 | Large Title | document title on paper |

**Rules:**

- Use sentence case everywhere, and no uppercase labels. Russian uppercase is wide and shouts.
- `letter-spacing: -.005em` at ≥ 15 px and `-.015em` at 26 px. Never add tracking to body text.
- `font-variant-numeric: tabular-nums` (`.num`) for counts, times, progress and versions.
- Mono only for **identifiers and code**: FR-1, SBX-14, `write-frd`, `{language}`, timestamps inside transcripts, and instructions editors. Never for dates or general meta.
- Reading measure: the document paper keeps lines at ≈ 65–75 characters (paper 760 px, text column ≈ 608 px).
- Minimum size is 11 px, above the HIG minimum of 10 pt. Everything must reflow at 200 % zoom.

---

## 4. Space, size, radius

| Token | Value | Token | Value |
|---|---|---|---|
| `--sp-1` | 2 | `--sp-7` | 20 |
| `--sp-2` | 4 | `--sp-8` | 24 (screen gutter) |
| `--sp-3` | 6 | `--sp-9` | 32 |
| `--sp-4` | 8 | `--sp-10` | 40 |
| `--sp-5` | 12 (row padding Y) | `--sp-11` | 56 (page bottom) |
| `--sp-6` | 16 (card padding) | | |

| Size | Value | Notes |
|---|---|---|
| `--ctl` | 28 px | default control height (macOS regular controls) |
| `--ctl-lg` | 32 px | primary CTA in sheets and empty states, and the push button |
| small control | 24 px | row actions, chips, segmented items. The minimum target (WCAG 2.2, 2.5.8) |
| `--row` | 36 px compact / 44 px comfortable | proposal: a density setting |
| `--toolbar` | 52 px | sticky |
| `--sidebar-w` | 232 px → 60 px collapsed | auto-collapses at ≤ 1120 px, toggle with ⌘\ |
| checkbox | 16 px visual, **28 px hit area** (`.cb-hit`) | |

| Radius | Value | Used for |
|---|---|---|
| `--r-xs` | 4 | tags, kbd, checkboxes |
| `--r-sm` | 6 | buttons, inputs, sidebar items |
| `--r-md` | 8 | segmented track, banners, paper, inner cards |
| `--r-lg` | 10 | cards, lists, tables |
| `--r-xl` | 14 | sheets, the bulk-bar HUD |
| `--r-full` | 999 | chips, source chips, recording pill |

Nested radii are concentric: an inner radius equals the outer radius minus the padding (HIG *concentric corners*).

**Content widths:** use `.wrap` (max 1180) for lists and tables, 760 for the paper, 720 for Settings, and the full width for Skills (a 2-pane layout). Every screen shares the same 24-px gutter, which becomes 16 px at ≤ 1120 px.

---

## 5. Elevation and materials

| Level | Light | Dark | Used for |
|---|---|---|---|
| `--e1` (resting) | `0 0 0 1px var(--line-strong), 0 1px 2px rgba(0,0,0,.04)` | ring + `inset 0 1px 0 rgba(255,255,255,.03)` | cards, lists, paper |
| `--e-btn` | ring + 1-px shadow | ring + top highlight | secondary buttons |
| `--e2` (popover) | `0 0 0 1px rgba(0,0,0,.08), 0 6px 20px rgba(0,0,0,.10)` | stronger, `.45` | menus, dropdowns, tooltips |
| `--e3` (overlay) | `0 16px 48px rgba(0,0,0,.22)` | `.6` | sheets, toasts, bulk bar, recording HUD |

In dark mode, elevation comes from *lighter surfaces* (bg → surface → surface-2 → surface-3), not from shadows.

**Materials:**

- **Sidebar:** a translucent `--sidebar` with blur. If `backdrop-filter` isn't available, it falls back to solid.
- **Toolbar:** `color-mix(--bg 82%)` plus blur. The hairline under it appears only after the page scrolls (HIG *scroll edge effect*).
- **HUD:** solid `--hud` in both themes.
- Glass is never used inside content.

---

## 6. Motion

| Token | Value | Used for |
|---|---|---|
| `--t-fast` | 120 ms | hover, press, row-action reveal |
| `--t-med` | 180 ms | disclosure, chevron rotation, screen fade (2-px rise), switch |
| `--t-slow` | 240 ms | sheet in, bulk bar in (16-px rise), toast in, toolbar hairline |
| `--ease` | `cubic-bezier(.2,0,0,1)` | entering |
| `--ease-exit` | `cubic-bezier(.4,0,1,1)` | leaving (exits run about 30 % faster) |

- Motion always has a direction: things come from the edge they belong to. The bulk bar and toasts rise from the bottom, the recording HUD drops from the top, and a disclosure unfolds downwards.
- There are no looping animations, except the progress spinner, the recording pulse and the level meter. The **toast stack moves up** when the bulk bar is visible.
- `prefers-reduced-motion`: all durations become 1 ms and the fade stays.

---

## 7. Components

Each component is plain CSS plus a small Svelte file. Class names below match the prototype.

### 7.1 Sidebar (`Rail.svelte` → `Sidebar.svelte`)
- **Project switcher** at the top: a 28-px monogram, the name (600) and a privacy line ("Claude · облако" or "🔒 Только локально"), opening a menu (`--e2`).
- **Group "Конвейер"** holds 6 steps. Each step has a 16-px icon in a 20-px column, a label and a **state badge**: `todo` (accent tint, e.g. "9" to review), `warn` (e.g. "v2" stale document), `done` (a green check), or a neutral count.
- **Group "Инструменты"** holds Скиллы and Настройки.
- Rows are 30 px. The selected row gets `--surface` and `--e1`, which reads as a raised tab rather than a coloured bar.
- The footer carries passive status only: GPU and version. No actions go at the bottom (HIG).
- **At ≤ 1120 px** it collapses to a 60-px icon rail with tooltips, and badges turn into 8-px dots (accent or warn). ⌘\ toggles it at any width. **Proposal:** below 720 px it becomes an overlay.

### 7.2 Toolbar (`Toolbar.svelte`, one per screen)
- **Leading:** an optional back button (Transcript → Sources), then the title (15/600) and a subtitle that states the screen (12, `--text-3`): "9 на ревью · принято 2 из 12".
- **Trailing:** secondary actions, then **one** `primary`, then a separator, then the keyboard-help and theme buttons.
- Every action has a priority class. At ≤ 1120 px, `opt-1` items move into the "…" overflow menu, and at ≤ 960 px `opt-2` items do too. The primary never moves.
- Screen primaries: Sources = *Записать звонок*, Transcript = *12 атомов →*, Atoms = *Собрать документ*, Document = *Экспорт DOCX ▾*, Decomposition = *К выгрузке →*, Export = the push button in the sticky push bar (the toolbar holds only *Обновить предпросмотр*).

### 7.3 Buttons
| Variant | Look | Use |
|---|---|---|
| default | `--surface` + `--e-btn` ring | secondary actions |
| `primary` | `--primary` fill, white text | one per view |
| `ghost` | transparent, `--text-2`, hover `--surface-3` | tertiary (Скрыть, Отключить, Изменить) |
| `danger` | default with `--danger` text | Удалить, Отправить в архив |
| `danger-fill` | `--danger-fill` | only inside a confirmation sheet |
| `icon-btn` | 28 × 28 (24 in rows) | always with `aria-label` and `title` including the shortcut |
| split | a primary action with a ▾ menu | Экспорт DOCX ▾ (template), Пересобрать ▾ (Собрать заново) |

Buttons may carry a `kbd` chip: `Принять A`, `Выгрузить 7 задач ⌘↵`.

### 7.4 Inputs
- 28 px tall, a `--line-control` border and `--r-sm`. On focus the border becomes `--focus` with a 3-px 25 % halo.
- The search field sits in a `--surface-2` well with a leading icon and a `/` kbd. The select uses a custom chevron.
- The code textarea (Skills) uses mono 12.5/20.
- **Checkbox:** a custom 16-px box with a `--line-control` border and a `--primary` fill. It supports an indeterminate state and sits in a 28-px hit area.
- **Switch:** 30 × 18.
- Labels are always present, visible or `.sr` (spec issue #14: 16 unlabeled fields).

### 7.5 Segmented control vs chips
- **Segmented** (`.seg`) = *one of N*, mutually exclusive: the atom status, the Jira action filter, the provider, the language, the theme. It's a macOS-style track with a raised selected segment and a count in `--text-3`.
- **Chips** (`.chip`) = *toggle filters*: the atom type, "В конфликте". They're pill-shaped with a 1-px ring. When pressed they get the accent tint.
- Never use the same look for both: this fixes the current identical "все" pills.

### 7.6 Tags and status
- **Tag:** 20 px, 11/600, `--r-xs`, a tint background with coloured text. Variants: `fr`, `nfr`, `q`, `ok`, `warn`, `danger`, `outline` (neutral: "встроенный", "сгенерировано", "обязательный").
- **Status** (`.status`) = an icon plus coloured 12/500 text, with no background, for table cells: "✓ Готово", "⟳ Извлекаю требования · 6/14" with a progress bar, "⚠ Не распознан: нет ffmpeg" plus *Повторить*.
- Use at most **one** tinted tag per row. Other signals are plain text in meta.

### 7.7 Lists and tables
- **Review list** (`.li`): a checkbox · a type tag · a body (the 14/500 statement, a 13-px `--text-2` quote in «…» clamped to 2 lines, and 12-px meta: `time` mono · who · source · the conflict as red text with an icon) · hover actions.
  - *Focus* = a 3-px accent bar and a 1-px `--accent-line` ring.
  - *Selected* = the `--accent-bg` fill. The two can combine and stay distinguishable.
- **Table** (`.table`): 11/600 headers, 44-px rows (40 in preview), `--line` separators, hover tint, and row actions on hover or focus-within. Headers are sticky under the toolbar when the table isn't clipped.
- Column priorities are hidden progressively at narrow widths (`c-spk`, `c-date`, `c-key`, `c-inv`, `c-ref`).

### 7.8 Tree (Decomposition)
- `role="tree"`. Rows are a grid of `checkbox | disclosure + glyph + title | criteria | INVEST | FRD ref | actions`.
- Indent is 22 px per level. The epic title is 600, stories 500, sub-tasks `--text-2`.
- An expanded story shows its statement ("**Как** … **я хочу** … **чтобы** …"), a **criteria table** (Дано / Когда / Тогда columns), then an inline INVEST finding (a warn tint with the letter badge, the reason, a proposal, and *Разделить* / *Скрыть*), then its sub-tasks.
- Unticking an epic unticks its children and says so in a toast.

### 7.9 Cards, banners and conflict cards
- **Card:** `--surface`, `--r-lg`, `--e1`. It has **no title bar by default**. Use `.section-h` (a 13/600 heading plus a `--text-3` count *outside* the card) so the list itself is the card.
- **Banner:** a one-line note with an icon, bold lead, detail and one action. Variants: neutral, `info`, `warn`, `danger`. Used for "После сборки изменилось 1 требование · раздел 3.2 устарел [Пересобрать раздел]".
- **Conflict summary:** a banner-card ("⚠ 2 конфликта — … [Разобрать]") that **expands in place** into A/B cards. Each card has the sides on `--surface-2` and the actions *Оставить A · Оставить B · Объединить… · В вопрос заказчику*.

### 7.10 Inspector (proposal, Atoms ≥ 1240 px)
- A sticky right pane (360 px) for the focused atom:
  - the type tag and ID
  - the statement at 15/600
  - the evidence in context: the previous segment, then the hit with `mark`
  - a key/value list: source, speaker, status, conflict
  - buttons: *Принять A*, *Отклонить X*, *В источнике*
- Below 1240 px, the same context unfolds inline under the focused row.

### 7.11 Document "paper"
- `--surface` on `--bg`, `--r-md`, a 1-px ring and a soft two-layer shadow. Padding is 56 / 64 / 72 / **88** px: the wide left margin holds the IDs.
- The kicker line (FRD · версия 2 · 11 требований · model) sits above a 26/700 title. Headings are H2 17/600 and H3 15/600, and the body is 15/24.
- **Requirement block** (`.req`): the ID hangs in the left margin (mono 12/600, coloured by type), then the text, then source chips (`src-chip`: an icon, the source and a timestamp or page, linking to the transcript), then at most one flag tag (conflict, размыто, исправлено). Hover shows a light tint and the *Править атом* action. A stale block gets a warn tint.
- **Pinned free text:** a 2-px `--line-control` left rule, `--surface-2`, and a label "📌 свой текст · закреплён".
- **Diff mode** (the *Сравнить с v1* toggle): `ins` and `del` tints inline plus "изменено" / "добавлено" tags.
- **Quality findings** are *margin notes* in a 280-px right column at ≥ 1360 px, and a 2-up grid above the paper when narrower. *Починить* opens an editable proposal in place → *Принять в атом* → the finding dims and the block flag becomes "✓ исправлено".
- Contents: a sticky left column (≥ 1120 px) with status dots on sections (warn = stale or finding, danger = conflict) and a version list underneath.

### 7.12 Toasts
- The HUD material, 36 px, bottom centre, rising in over 240 ms.
- **Toasts belong to the screen that raised them.** They clear on navigation, and they stack (at most 2). When the bulk bar is visible, the stack sits above it (`body.has-bulk .toasts { bottom: 88px }`).
- An undo action shows its key: `Отменить ⌘Z`. Display time is 4.2 s, extended while hovered (proposal).
- Errors are **not** toasts. They're inline banners with a recovery action ("Ключ отклонён — [Открыть настройки]").

### 7.13 Bulk bar
- A floating HUD (`--r-xl`, `--e3`), centred on the *content* area rather than the window, sliding up 16 px over 240 ms.
- Contents: `Выбрано: 3`, then "в конфликтах: 2" in salmon, then **Принять A** (primary fill), *Отклонить X*, *На ревью*, a *Тип…* select, and ✕ (Esc).
- It never covers the last row: the list gets bottom padding while the bar is visible.

### 7.14 Sheets (modal confirmation)
- 460 px, `--r-xl`, `--e3`, on the scrim, 12 vh from the top.
- Contents: a title with the question and the number ("Выгрузить 7 задач в SBX?"), one sentence of consequence, a **facts list** (site, project, create N, update N plus what will be overwritten), then *Отмена* (default focus) and the primary *Да, выгрузить в SBX*.
- Esc and a scrim click cancel. ⌘↵ confirms only when the sheet is open.

### 7.15 Empty states
- A 44-px rounded glyph tile, a 15/600 title, a one-sentence explanation (≤ 44 characters per line) and **one** action (32 px).
- Never pair an empty state with a disabled toolbar primary: hide the primary or make it the empty state's CTA.
- Copy comes from the existing i18n keys (`at.none_title`, `doc.no_atoms_title`, `bl.no_doc_title`…).
- The "done" state is celebratory but quiet: a green glyph with "Все атомы разобраны · Принято 11 из 12 · [Собрать документ]".

### 7.16 Progress
- **Inline:** a 12-px spinner and text with the count ("Извлекаю требования · 6/14"), plus a 4-px bar underneath.
- **Global (proposal):** a running job shows a small spinner dot on its sidebar step.
- **Downloads:** a bar with "1,6 из 2,6 ГБ" and *Отмена*.
- **Recording:** a top-centre HUD pill with a pulse dot, the timer, a level meter, the device and *Остановить*. It stays visible on every screen.

### 7.17 Settings form
- Grouped cards with a 12/600 group title above. Each row puts the label (13/500) and hint (12, `--text-3`) on the left and the control on the right. Rows are at least 48 px, separated by `--line`.
- Segmented controls fit their content.

---

## 8. Keyboard and focus

**Global:**

| Keys | Action |
|---|---|
| ⌘1 … ⌘6 | go to pipeline step |
| ⌘, | Settings |
| ⌘\ | toggle sidebar |
| / | focus search on the screen |
| ? | shortcut sheet (proposal) |
| ⌘K | command palette (proposal: every toolbar action, every screen, every source) |
| ⌘⇧L | toggle theme |
| Esc | close sheet / clear selection / leave field |

**Atoms (review list):**

| Keys | Action |
|---|---|
| J / K or ↓ / ↑ | move focus. ⇧ extends the selection |
| A / X / E | accept / reject / edit the focused atom, or **all selected** if there is a selection |
| Space | toggle selection. ⇧-click selects a range |
| ⌘A | select all shown |
| ⌘Z | undo last decision (bulk included) |
| Enter | open the focused atom's source |

**Decomposition (tree):** ↑/↓ move, ←/→ collapse and expand (← on a collapsed row jumps to its parent), Space toggles *in export*, E edits, ⌥↑/⌥↓ reorders.

**Document:** `[` / `]` go to the previous or next quality finding, F runs *Починить* on the focused finding, ⌘E exports DOCX.

**Export:** ⌘↵ opens the push confirmation. Focus lands on *Отмена*, and a second ⌘↵ confirms.

**Focus rules:**

1. `:focus-visible` gives a 2-px `--focus` outline with a 2-px offset on every interactive element. It's never removed.
2. List and tree rows use a *roving tabindex*: the whole list is one Tab stop, and the arrows move inside it. The focused row shows the inset accent bar, and its actions become visible (`:focus-within`).
3. Focus ≠ selection: they look different and can be combined.
4. Opening a sheet moves focus into it. Closing returns it to the trigger. Focus is trapped while the sheet is open.
5. Shortcuts are ignored while typing in an input, textarea or select (FR-ATM-09 AC3).
6. Every icon button has an `aria-label`. Its `title` includes the shortcut ("Принять · A").

---

## 9. Responsive behaviour

| Width | Change |
|---|---|
| ≥ 1360 | Document: contents + paper + margin notes |
| < 1360 | Document margin notes move above the paper |
| < 1240 | Atoms inspector becomes inline context under the focused row |
| ≤ 1120 | Sidebar collapses to a 60-px icon rail with dots. The gutter becomes 16 px. `opt-1` toolbar items go to overflow. Document contents hidden, and IDs move above the text. Sources capture cards stack. The tree drops the INVEST and ref columns. Skills list becomes 220 px |
| ≤ 960 | `opt-2` toolbar items go to overflow and search is hidden (still reachable with `/`). Conflict A/B sides stack. The atom tag sits above the statement. Low-priority table columns hide |
| ≤ 840 | Skills list stacks above the editor |

---

## 10. Migration: mapping onto the current `app.css`

The current variables keep working during the migration. **Step 1** adds the new tokens and re-points the old names to them. That's one diff in `app.css`, and no component changes are needed yet:

| Current | New token | Change |
|---|---|---|
| `--paper` | `--bg` | #EDEFEC → #F5F5F3 (lighter, more neutral canvas) |
| `--panel` | `--surface` | same white / #1C1D20 |
| `--sunk` | `--surface-2` | #F5F6F3 → #EEEEEB (hover needs to be visible on white) |
| — | `--surface-3`, `--sidebar` | new |
| `--ink` | `--text` | ≈ same |
| `--ink-2` | `--text-2` | ≈ same |
| `--ink-3` | `--text-3` | **#8A908B → #63666D** (3.26 → 5.75 on white). Dark #7C837E → #8A8D95 |
| `--rule` | `--line` | ≈ same |
| `--rule-2` (used for input borders **and** card edges) | split: `--line-strong` (card edges) + `--line-control` (inputs, checkboxes) | **#C6CAC4 → #8B8E95 for controls** (1.66 → 3.28) |
| `--accent` | `--accent` (text) + `--primary` (fills) | light #2B5B78 → #245E92. **Dark primary fill becomes #2F6DAE with white text** instead of #8FBBD6 with dark text |
| `--accent-ink` | `--text-on-accent` | always #FFF |
| `--accent-bg` | `--accent-bg` | ≈ same |
| `--focus` | `--focus` | brighter, so it differs from the accent text |
| `--ok*`, `--warn*`, `--danger*` | same names | small shifts for AA. Add `--danger-fill` |
| — | `--q*`, `--nfr*`, `--rec`, `--mark`(already exists), `--ins`, `--del`, `--hud*`, `--overlay` | new |
| `--s-1…--s-7` (4…48) | `--sp-2, 4, 5, 6, 8, 9, 10…` | aliases: `--s-1:var(--sp-2)`, `--s-2:var(--sp-4)`, `--s-3:var(--sp-5)`, `--s-4:var(--sp-6)`, `--s-5:var(--sp-8)`, `--s-6:var(--sp-9)`, `--s-7:48px` |
| `--t-xs/sm/md/lg/xl` (12/13/14/16/20) | `--fs-12/13/14/15/17` | **base body drops 14 → 13**. Atom and transcript content stays 14. Screen titles move into the toolbar at 15 |
| `--r-sm/md/lg` (4/6/8) | `--r-xs/sm/md` + new `--r-lg 10`, `--r-xl 14` | cards 8 → 10 |
| `--control-h` 36 | `--ctl` 28 (+ `--ctl-lg` 32) | denser. Keep hit areas ≥ 24 |
| `--rail-w` 224 | `--sidebar-w` 232 / 60 | + collapse |
| `--sans` (IBM Plex first) | `--font` / `--font-display` | remove Plex |
| `--mono` | `--mono` | remove Plex Mono. Stop using it for meta |

**Component mapping:**

| Current | Becomes |
|---|---|
| `.screen-head` + `.screen-title` + `.screen-sub` | `Toolbar.svelte` (`.toolbar`, `.tb-title`, `.tb-actions`) |
| `details.block` / `Block.svelte` | stays for *Settings → Окружение* and similar. Elsewhere use `.section-h` + `.card`, or a one-line banner that expands in place |
| `.panel` | `.card` |
| `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-sm`, `.icon-btn` | `.btn`, `.btn.primary`, `.btn.ghost`, `.btn.sm`, `.icon-btn` (same names, new look; add `split`, `danger-fill`, `lg`) |
| `.seg` | `.seg` (track style) |
| filter `.pill` | `.seg` for status, `.chip` for type |
| `.tag.*` | `.tag.*` (+ `fr`, `nfr`, `q`, `outline`) |
| `.note.*` | `.banner.*` |
| `.bar` | `.progress` |
| `Toast.svelte` (single) | `Toasts.svelte` (a stack, screen-scoped, aware of the bulk bar) |
| `.bulkbar` (sticky, light) | `.bulkbar` HUD (fixed, dark) |
| inline `.note.warn.confirm` on Export (text + Отмена / Да, выгрузить) | `Sheet.svelte` with a facts list (keep the same i18n strings) |
| `.spk-0…4` | `.spk.s0…` (a dot and coloured name instead of a filled chip) |
| — | new: `Kbd.svelte`, `EmptyState.svelte`, `Inspector.svelte`, `TreeRow.svelte`, `RecordingHud.svelte` |
