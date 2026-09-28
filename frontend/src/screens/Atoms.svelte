<script>
  import Block from "../components/Block.svelte";
  import Icon from "../components/Icon.svelte";
  import { api } from "../lib/api.js";
  import { extractAtoms } from "../lib/atoms.js";
  import { fmtTime, speakerDisplay } from "../lib/format.js";
  import { app, t, go, toast, loadSources, writePref } from "../lib/state.svelte.js";
  import { SvelteSet } from "svelte/reactivity";

  let atoms = $state([]);
  let stats = $state(null);
  let conflicts = $state([]);
  let loaded = $state(false);
  let error = $state("");

  function readFilter(key, fallback) {
    try { return JSON.parse(localStorage.getItem("wb.atoms." + key)) ?? fallback; } catch (_) { return fallback; }
  }
  let statusFilter = $state(readFilter("status", "all"));
  let typeFilter = $state(readFilter("type", "all"));
  $effect(() => { writePref("atoms.status", statusFilter); writePref("atoms.type", typeFilter); });

  let selectedId = $state(null);
  let editingId = $state(null);
  let draft = $state({ statement: "", type: "functional" });
  let mergingId = $state(null);
  let mergeDraft = $state("");
  let busy = $state(false);

  async function load() {
    const pid = app.currentProjectId;
    try {
      const [a, c] = await Promise.all([api(`/api/projects/${pid}/atoms`), api(`/api/projects/${pid}/conflicts`)]);
      if (pid !== app.currentProjectId) return;
      atoms = a.atoms;
      stats = a.stats;
      conflicts = c.conflicts;
      error = "";
    } catch (err) {
      error = err.message;
    } finally {
      loaded = true;
    }
  }

  // Reload on project switch and whenever an extraction finishes.
  $effect(() => { app.currentProjectId; app.atomsVersion; load(); });

  const sourceFilter = $derived(app.route.source || null);
  const sourceFilterTitle = $derived(app.sources.find(s => s.id === sourceFilter)?.title || "");
  const visible = $derived(atoms.filter(a =>
    (statusFilter === "all" || a.status === statusFilter) &&
    (typeFilter === "all" || a.type === typeFilter) &&
    (!sourceFilter || a.evidence.some(e => e.source_id === sourceFilter))));
  const manySources = $derived(new Set(atoms.flatMap(a => a.evidence.map(e => e.source_id))).size > 1);
  const readySources = $derived(app.sources.filter(s => s.status === "ready"));
  const statementOf = $derived(Object.fromEntries(atoms.map(a => [a.id, a.statement])));
  const openConflicts = $derived(conflicts.filter(c => c.status === "open"));

  $effect(() => {
    // Keep a valid selection while the list changes under the filters.
    if (!visible.length) selectedId = null;
    else if (!visible.some(a => a.id === selectedId)) selectedId = visible[0].id;
  });

  function select(id, scroll = true) {
    selectedId = id;
    if (scroll) requestAnimationFrame(() => document.getElementById(`atom-${id}`)?.scrollIntoView({ block: "nearest" }));
  }

  async function patch(atom, body) {
    const updated = await api(`/api/atoms/${atom.id}`, { method: "PATCH", body });
    stats = updated.stats;
    const { stats: _, ...fresh } = updated;
    atoms = atoms.map(a => (a.id === atom.id ? { ...a, ...fresh } : a));
    // Answering a conflict's question closes the conflict: refresh the flags on both atoms.
    if (atom.type === "question" && body.status && conflicts.some(c => c.question_atom === atom.id)) await load();
    return fresh;
  }

  // Buttons toggle (clicking again takes the decision back); keys only set it.
  async function decide(atom, status, { toggle = true } = {}) {
    const previous = atom.status;
    const next = toggle && previous === status ? "pending" : status;
    // Move on to the next atom still to review right away, so fast keyboard review never lands twice on one atom.
    const i = visible.findIndex(a => a.id === atom.id);
    const others = visible.filter(a => a.id !== atom.id && a.status === "pending");
    const after = next === "pending" ? null
      : visible.slice(i + 1).find(a => a.status === "pending") || others[0] || visible[i + 1];
    if (after) select(after.id);
    if (next === previous) return;
    try {
      await patch(atom, { status: next });
      if (next !== "pending") {
        toast(t(next === "accepted" ? "at.accepted_toast" : "at.rejected_toast"), {
          action: t("at.undo"), onAction: () => patch(atom, { status: previous }).then(() => select(atom.id)) });
      }
    } catch (err) {
      select(atom.id);
      toast(err.message, { kind: "danger" });
    }
  }

  // ── bulk review: check atoms, then accept / reject / retype them together ──
  const checked = new SvelteSet();
  let anchorId = null;                    // for shift-click ranges
  let bulkBusy = $state(false);
  $effect(() => { app.currentProjectId; checked.clear(); });
  const checkedVisible = $derived(visible.filter(a => checked.has(a.id)));
  const allChecked = $derived(visible.length > 0 && checkedVisible.length === visible.length);
  const checkedInConflict = $derived(checkedVisible.filter(a => a.conflicts.length).length);
  const sourcesWithAtoms = $derived(app.sources.filter(s => s.atom_count));

  function toggleCheck(atom, shift = false) {
    const on = !checked.has(atom.id);
    if (shift && anchorId) {
      const a = visible.findIndex(x => x.id === anchorId), b = visible.findIndex(x => x.id === atom.id);
      if (a >= 0 && b >= 0) {
        for (const x of visible.slice(Math.min(a, b), Math.max(a, b) + 1)) on ? checked.add(x.id) : checked.delete(x.id);
        anchorId = atom.id;
        return;
      }
    }
    on ? checked.add(atom.id) : checked.delete(atom.id);
    anchorId = atom.id;
  }
  function toggleAll() {
    if (allChecked) for (const a of visible) checked.delete(a.id);
    else for (const a of visible) checked.add(a.id);
  }

  async function bulk(change) {
    const targets = checkedVisible.filter(a => Object.entries(change).some(([k, v]) => a[k] !== v));
    if (!targets.length) { checked.clear(); return; }
    const before = targets.map(a => ({ id: a.id, status: a.status, type: a.type }));
    bulkBusy = true;
    try {
      const r = await bulkSend(targets.map(a => ({ id: a.id, ...change })));
      checked.clear();
      toast(t("at.bulk_done", { n: r.changed.length }), { action: t("at.undo"), ms: 10000, onAction: async () => {
        const undo = before.filter(b => r.changed.includes(b.id)).map(b => ({ id: b.id,
          ...(change.status ? { status: b.status } : {}), ...(change.type ? { type: b.type } : {}) }));
        await bulkSend(undo);
      } });
    } catch (err) {
      toast(err.message, { kind: "danger" });
    } finally {
      bulkBusy = false;
    }
  }
  async function bulkSend(items) {
    const r = await api(`/api/projects/${app.currentProjectId}/atoms/bulk`, { method: "POST", body: { items } });
    const byId = Object.fromEntries(items.map(i => [i.id, i]));
    atoms = atoms.map(a => (r.changed.includes(a.id) ? { ...a, ...byId[a.id] } : a));
    stats = r.stats;
    // Accepting questions may have closed conflicts: refresh those flags.
    if (items.some(i => i.status === "accepted") && conflicts.some(c => c.question_atom && r.changed.includes(c.question_atom))) await load();
    return r;
  }

  // Delete (with undo): gone from the list, the counters and the next document build.
  async function removeAtoms(list) {
    if (!list.length) return;
    const ids = list.map(a => a.id);
    const i = visible.findIndex(a => a.id === ids[0]);
    try {
      const r = await api(`/api/projects/${app.currentProjectId}/atoms/delete`, { method: "POST", body: { ids } });
      stats = r.stats;
      atoms = atoms.filter(a => !r.deleted.includes(a.id));
      for (const id of r.deleted) checked.delete(id);
      const next = visible[Math.min(i, visible.length - 1)];
      if (next) select(next.id);
      if (conflicts.length) load();
      loadSources();
      toast(t("at.deleted", { n: r.deleted.length }), { action: t("at.undo"), ms: 10000, onAction: async () => {
        await api(`/api/projects/${app.currentProjectId}/atoms/restore`, { method: "POST", body: { ids: r.deleted } });
        await load();
        loadSources();
      } });
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  function startEdit(atom) {
    editingId = atom.id;
    selectedId = atom.id;
    draft = { statement: atom.statement, type: atom.type };
  }

  async function saveEdit(atom) {
    const body = {};
    if (draft.statement.trim() !== atom.statement) body.statement = draft.statement;
    if (draft.type !== atom.type) body.type = draft.type;
    editingId = null;
    if (!Object.keys(body).length) return;
    try { await patch(atom, body); } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function resolve(conflict, action, statement) {
    busy = true;
    try {
      const r = await api(`/api/conflicts/${conflict.id}/resolve`, { method: "POST", body: { action, statement } });
      mergingId = null;
      toast(t(r.status === "awaiting_answer" ? "at.question_toast" : "at.resolved_toast"));
      await load();
      loadSources();
    } catch (err) {
      toast(err.message, { kind: "danger" });
    } finally {
      busy = false;
    }
  }

  function onKey(e) {
    if (app.route.name !== "atoms" || e.target.closest("textarea, select, [contenteditable], input:not([type=checkbox])")) return;
    const onCheckbox = e.target.matches?.("input[type=checkbox]");     // shortcuts still work after ticking a box
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "a") {   // select every atom under the filters
      e.preventDefault();
      for (const a of visible) checked.add(a.id);
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const i = visible.findIndex(a => a.id === selectedId);
    const atom = visible[i];
    if (e.key === " " && onCheckbox) return;                          // Space toggles the focused box itself
    if (e.key === " " && atom) toggleCheck(atom, e.shiftKey);
    else if (e.key === "Escape" && checked.size) checked.clear();
    else if (e.key === "j" || e.key === "ArrowDown") { if (visible[i + 1]) select(visible[i + 1].id); }
    else if (e.key === "k" || e.key === "ArrowUp") { if (i > 0) select(visible[i - 1].id); }
    else if (e.key === "a" && atom) decide(atom, "accepted", { toggle: false });
    else if (e.key === "x" && atom) decide(atom, "rejected", { toggle: false });
    else if (e.key === "e" && atom) startEdit(atom);
    else if ((e.key === "Delete" || e.key === "Backspace") && (checkedVisible.length || atom))
      removeAtoms(checkedVisible.length ? checkedVisible : [atom]);
    else return;
    e.preventDefault();
  }

  function evidenceLabel(ev) {
    const bits = [];
    if (ev.start != null) bits.push(fmtTime(ev.start));
    if (ev.speaker) bits.push(speakerDisplay(ev.speaker, ev.speaker_name, t));
    if (manySources) bits.push(ev.source_title);
    return bits.join(" · ");
  }

  const statusPills = ["all", "pending", "accepted", "rejected"];
  const typePills = ["all", "functional", "nfr", "question"];
  const typeClass = { functional: "fr", nfr: "nfr", question: "q" };

  let conflictsOpen = $state(readFilter("conflictsOpen", true));
  $effect(() => { writePref("atoms.conflictsOpen", conflictsOpen); });
  // The toast stack moves up while the bulk bar is visible.
  $effect(() => {
    document.body.classList.toggle("has-bulk", checkedVisible.length > 0);
    return () => document.body.classList.remove("has-bulk");
  });
  const count = (key, value) => atoms.filter(a => a[key] === value).length;
</script>

<svelte:window onkeydown={onKey} />

<div class="screen-inner" class:bulk-on={checkedVisible.length > 0}>
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("at.title")}</h1>
      <p class="screen-sub">
        {#if stats && stats.total}{t("at.sub", stats)}{:else}{t("at.sub_empty")}{/if}
      </p>
    </div>
    {#if stats && stats.accepted && stats.pending}
      <div class="actions">
        <button class="btn btn-primary" onclick={() => go("/document")}>{t("doc.build_cta")} <Icon name="arrow" size={14} /></button>
      </div>
    {/if}
  </header>

  {#if error}<p class="note danger">{error}</p>{/if}

  {#if conflicts.length}
    <section class="card conflicts" class:open={conflictsOpen} class:calm={!openConflicts.length}>
      <button class="cf-head" onclick={() => (conflictsOpen = !conflictsOpen)} aria-expanded={conflictsOpen}>
        <span class="cf-ico"><Icon name="warn" /></span>
        <span class="grow">
          <b>{openConflicts.length ? t("at.conflicts_n", { n: openConflicts.length }) : t("at.conflicts")}</b>
          <span class="t2"> · {t("at.conflicts_desc")}</span>
        </span>
        <span class="btn btn-sm">{conflictsOpen ? t("at.hide") : t("at.resolve")}</span>
      </button>
      {#if conflictsOpen}
        <div class="cf-body">
          {#each conflicts as c (c.id)}
            <div class="conflict" class:waiting={c.status === "awaiting_answer"}>
              <h3>
                {c.description}
                {#if c.status === "awaiting_answer"}<span class="tag warn">{t("at.awaiting")}</span>{/if}
              </h3>
              <div class="c-sides">
                {#each [["A", c.a], ["B", c.b]] as [side, atom] (side)}
                  <div class="c-side">
                    <span class="ab">{side}</span>
                    <p class="s">{atom.statement}</p>
                    {#if atom.evidence[0]}
                      <button class="quote link" onclick={() => go(`/source/${atom.evidence[0].source_id}/seg/${atom.evidence[0].segment_idx}`)}>
                        {atom.evidence[0].quote}
                      </button>
                      {#if evidenceLabel(atom.evidence[0])}<p class="meta">{evidenceLabel(atom.evidence[0])}</p>{/if}
                    {/if}
                  </div>
                {/each}
              </div>
              {#if c.status === "open"}
                {#if mergingId === c.id}
                  <div class="field merge">
                    <label class="label" for="merge-{c.id}">{t("at.merge_hint")}</label>
                    <textarea class="input area" id="merge-{c.id}" rows="2" bind:value={mergeDraft}></textarea>
                    <div class="actions">
                      <button class="btn btn-sm btn-primary" disabled={busy || !mergeDraft.trim()}
                              onclick={() => resolve(c, "merge", mergeDraft)}>{t("at.save")}</button>
                      <button class="btn btn-sm btn-ghost" onclick={() => (mergingId = null)}>{t("at.cancel")}</button>
                    </div>
                  </div>
                {:else}
                  <div class="actions c-acts">
                    <button class="btn btn-sm" disabled={busy} onclick={() => resolve(c, "keep_a")}>{t("at.keep", { side: "A" })}</button>
                    <button class="btn btn-sm" disabled={busy} onclick={() => resolve(c, "keep_b")}>{t("at.keep", { side: "B" })}</button>
                    <button class="btn btn-sm" disabled={busy} onclick={() => { mergingId = c.id; mergeDraft = c.a.statement; }}>{t("at.merge")}</button>
                    <button class="btn btn-sm btn-ghost" disabled={busy} onclick={() => resolve(c, "question")}>{t("at.to_question")}</button>
                  </div>
                {/if}
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </section>
  {/if}

  {#if stats && stats.total && !stats.pending}
    <div class="done-state row-done">
      <Icon name="check" />
      <span class="grow"><b>{t("at.done_title")}</b> · {t("at.done_meta", stats)}</span>
      <button class="btn btn-primary" onclick={() => go("/document")}>{t("doc.build_cta")}</button>
    </div>
  {/if}

  {#if atoms.length}
    <div class="filters">
      {#if visible.length}
        <label class="check-all cb-label" title="⌘A">
          <span class="cb-hit"><input type="checkbox" checked={allChecked} indeterminate={checkedVisible.length > 0 && !allChecked}
                 onchange={toggleAll} aria-label={t("at.select_all", { n: visible.length })} /></span>
          <span>{t("at.select_all", { n: visible.length })}</span>
        </label>
      {/if}
      <div class="seg" role="group" aria-label="Status">
        {#each statusPills as f (f)}
          <button class="pill" aria-pressed={statusFilter === f} onclick={() => (statusFilter = f)}>
            {t("at.f." + f)}{#if f !== "all" && stats}<span class="n">{stats[f]}</span>{/if}
          </button>
        {/each}
      </div>
      <div class="chips" role="group" aria-label="Type">
        {#each typePills as f (f)}
          <button class="chip pill" aria-pressed={typeFilter === f} onclick={() => (typeFilter = f)}>
            {t("at.f." + f)}{#if f !== "all"}<span class="n">{count("type", f)}</span>{/if}
          </button>
        {/each}
      </div>
      <span class="spacer"></span>
      {#if sourcesWithAtoms.length > 1 || sourceFilter}
        <select class="select src-select" aria-label={t("at.sources")} value={sourceFilter || ""}
                onchange={e => go(e.currentTarget.value ? `/atoms/source/${e.currentTarget.value}` : "/atoms")}>
          <option value="">{t("at.all_sources")}</option>
          {#each sourcesWithAtoms as s (s.id)}<option value={s.id}>{s.title} ({s.atom_count})</option>{/each}
          {#if sourceFilter && !sourcesWithAtoms.some(s => s.id === sourceFilter)}<option value={sourceFilter}>{sourceFilterTitle}</option>{/if}
        </select>
      {/if}
    </div>
  {/if}

  <section class="list">
    {#if loaded && !atoms.length}
      <div class="empty">
        <div class="glyph"><Icon name="atoms" /></div>
        <p class="panel-title">{t("at.none_title")}</p>
        <p>{t("at.none")}</p>
      </div>
    {:else if loaded && !visible.length}
      <p class="empty">{t("at.none_filtered")}</p>
    {:else}
      <ul class="atoms">
        {#each visible as atom (atom.id)}
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
          <li class="atom" id="atom-{atom.id}" class:sel={atom.id === selectedId} class:rejected={atom.status === "rejected"}
              class:accepted={atom.status === "accepted"} class:checked={checked.has(atom.id)} onclick={() => select(atom.id, false)}>
            <span class="cb-hit"><input type="checkbox" class="row-check" checked={checked.has(atom.id)} aria-label={atom.statement}
                   onclick={e => { e.stopPropagation(); toggleCheck(atom, e.shiftKey); }} /></span>
            <span class="tag type {typeClass[atom.type]}">{t("at.type." + atom.type)}</span>
            <div class="body">
              {#if editingId === atom.id}
                <!-- svelte-ignore a11y_autofocus -->
                <textarea class="input area" rows="2" bind:value={draft.statement} autofocus aria-label={t("at.edit")}
                          onkeydown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); saveEdit(atom); }
                                            if (e.key === "Escape") editingId = null; }}></textarea>
                <div class="actions edit-row">
                  <div class="seg">
                    {#each ["functional", "nfr", "question"] as ty (ty)}
                      <button aria-pressed={draft.type === ty} onclick={() => (draft.type = ty)}>{t("at.type." + ty)}</button>
                    {/each}
                  </div>
                  <span class="spacer"></span>
                  <button class="btn btn-sm btn-ghost" onclick={() => (editingId = null)}>{t("at.cancel")}</button>
                  <button class="btn btn-sm btn-primary" disabled={!draft.statement.trim()} onclick={() => saveEdit(atom)}>{t("at.save")}</button>
                </div>
              {:else}
                <p class="stm">{atom.statement}</p>
                {#if atom.statement !== atom.original_statement}
                  <p class="hint">{t("at.was", { text: atom.original_statement })}</p>
                {/if}
              {/if}
              {#each atom.evidence as ev (ev.id)}
                <button class="quote link" title={t("at.jump")} onclick={() => go(`/source/${ev.source_id}/seg/${ev.segment_idx}`)}>{ev.quote}</button>
                {#if evidenceLabel(ev)}<p class="meta">{evidenceLabel(ev)}</p>{/if}
              {/each}
              {#each atom.conflicts as c (c.id)}
                <p class="conf-line"><Icon name="warn" size={12} /> {t("at.conflict_with", { text: c.description })}
                  {#if statementOf[c.other]}<span class="t3"> — {statementOf[c.other]}</span>{/if}</p>
              {/each}
            </div>
            <div class="side">
              {#if atom.status === "accepted"}<span class="state ok"><Icon name="check" size={12} /> {t("at.status.accepted")}</span>
              {:else if atom.status === "rejected"}<span class="state"><Icon name="close" size={12} /> {t("at.status.rejected")}</span>{/if}
              <div class="acts">
                <button class="btn btn-ghost btn-sm icon-btn" class:on-ok={atom.status === "accepted"} aria-label={t("at.accept")}
                        title="{t('at.accept')} · A" aria-pressed={atom.status === "accepted"}
                        onclick={e => { e.stopPropagation(); decide(atom, "accepted"); }}><Icon name="check" size={14} /></button>
                <button class="btn btn-ghost btn-sm icon-btn" class:on-no={atom.status === "rejected"} aria-label={t("at.reject")}
                        title="{t('at.reject')} · X" aria-pressed={atom.status === "rejected"}
                        onclick={e => { e.stopPropagation(); decide(atom, "rejected"); }}><Icon name="close" size={14} /></button>
                <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("at.edit")} title="{t('at.edit')} · E"
                        onclick={e => { e.stopPropagation(); startEdit(atom); }}><Icon name="pencil" size={14} /></button>
                <button class="btn btn-ghost btn-sm icon-btn del" aria-label={t("at.delete")} title="{t('at.delete')} · Delete"
                        onclick={e => { e.stopPropagation(); removeAtoms([atom]); }}><Icon name="trash" size={14} /></button>
              </div>
            </div>
          </li>
        {/each}
      </ul>
    {/if}

    {#if atoms.length}
      <p class="keys">
        <span><span class="kbd">J</span><span class="kbd">K</span></span>
        {@html t("at.keys", { a: '<span class="kbd">A</span>', x: '<span class="kbd">X</span>', e: '<span class="kbd">E</span>' })}
        · {@html t("at.keys_bulk", { space: '<span class="kbd">␣</span>', all: '<span class="kbd">⌘A</span>' })}
      </p>
    {/if}
  </section>

  {#if checkedVisible.length}
    <div class="bulkbar" role="toolbar" aria-label={t("at.selected", { n: checkedVisible.length })}>
      <b class="count num">{t("at.selected", { n: checkedVisible.length })}</b>
      {#if checkedInConflict}<span class="conf">{t("at.bulk_conflicts", { n: checkedInConflict })}</span>{/if}
      <span class="vsep"></span>
      <button class="btn btn-sm accept" disabled={bulkBusy} onclick={() => bulk({ status: "accepted" })}>
        <Icon name="check" size={14} /> {t("at.accept")} <span class="kbd">A</span></button>
      <button class="btn btn-sm" disabled={bulkBusy} onclick={() => bulk({ status: "rejected" })}>
        <Icon name="close" size={14} /> {t("at.reject")} <span class="kbd">X</span></button>
      <button class="btn btn-sm" disabled={bulkBusy} onclick={() => bulk({ status: "pending" })}>{t("at.bulk_pending")}</button>
      <select class="select type-select" disabled={bulkBusy} aria-label={t("at.bulk_type")} value=""
              onchange={e => { const v = e.currentTarget.value; e.currentTarget.value = ""; if (v) bulk({ type: v }); }}>
        <option value="" disabled>{t("at.bulk_type")}</option>
        {#each ["functional", "nfr", "question"] as ty (ty)}<option value={ty}>{t("at.f." + ty)}</option>{/each}
      </select>
      <button class="btn btn-sm danger-text" disabled={bulkBusy} onclick={() => removeAtoms(checkedVisible)}>
        <Icon name="trash" size={14} /> {t("at.delete")}</button>
      <span class="vsep"></span>
      <button class="btn btn-sm icon-btn" aria-label={t("at.bulk_clear")} title="{t('at.bulk_clear')} · Esc"
              onclick={() => checked.clear()}><Icon name="close" size={14} /></button>
    </div>
  {/if}

  <div class="stack sources-block">
    <Block id="at-sources" title={t("at.sources")} open={!atoms.length}
           meta={t("at.sources_meta", { n: readySources.length })}>
      {#if !readySources.length}
        <p class="muted">{t("at.no_ready")}</p>
      {:else}
        <ul class="sources">
          {#each readySources as s (s.id)}
            <li class="src">
              <button class="src-title link" onclick={() => go(`/source/${s.id}`)}>{s.title}</button>
              <span class="t3">{t("kind." + s.kind)}</span>
              {#if s.atom_count}
                <button class="tag fr link" onclick={() => go(`/atoms/source/${s.id}`)}>{t("at.count", { n: s.atom_count })}</button>
              {/if}
              <span class="spacer"></span>
              {#if app.extracting[s.id]}
                <span class="status run"><span class="spinner"></span>{app.extracting[s.id].message}</span>
              {:else}
                <button class="btn btn-sm" class:btn-primary={!s.atom_count}
                        title={s.atom_count ? t("at.reextract_hint") : ""} onclick={() => extractAtoms(s.id)}>
                  {s.atom_count ? t("at.reextract") : t("at.extract")}
                </button>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </Block>
  </div>
</div>

<style>
  .grow { flex: 1; min-width: 0; }
  .spacer { flex: 1; }
  .link { border: 0; background: none; padding: 0; font: inherit; cursor: pointer; }

  /* conflicts: a one-line summary that expands in place */
  .conflicts { margin-bottom: var(--sp-6); box-shadow: 0 0 0 1px color-mix(in srgb, var(--danger) 35%, var(--line-strong)); }
  .conflicts.calm { box-shadow: var(--e1); }
  .cf-head { display: flex; align-items: center; gap: var(--sp-4); width: 100%; padding: var(--sp-4) var(--sp-5); border: 0;
    background: none; text-align: left; cursor: pointer; border-radius: var(--r-lg); }
  .cf-head b { font-weight: 600; color: var(--danger); }
  .calm .cf-head b { color: var(--text); }
  .cf-ico { color: var(--danger); display: grid; }
  .calm .cf-ico { color: var(--text-3); }
  .cf-body { padding: 0 var(--sp-5) var(--sp-5); display: flex; flex-direction: column; gap: var(--sp-4); }
  .conflict { border-radius: var(--r-md); background: var(--surface); box-shadow: var(--e1); padding: var(--sp-5); }
  .conflict h3 { font-size: var(--fs-13); font-weight: 600; margin-bottom: var(--sp-4); display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap; }
  .c-sides { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4); }
  .c-side { border-radius: var(--r-sm); background: var(--surface-2); padding: var(--sp-4) var(--sp-5); min-width: 0; }
  .c-side .ab { font: 600 11px var(--font); color: var(--text-3); display: block; margin-bottom: 2px; }
  .c-side .s { font-weight: 500; }
  .c-acts { margin-top: var(--sp-5); gap: var(--sp-3); }
  .merge { margin-top: var(--sp-5); }
  @media (max-width: 960px) { .c-sides { grid-template-columns: 1fr; } }

  .done-state { display: flex; align-items: center; gap: var(--sp-5); padding: var(--sp-4) var(--sp-4) var(--sp-4) var(--sp-6);
    background: var(--ok-bg); color: var(--ok); border-radius: var(--r-lg); margin-bottom: var(--sp-5); }
  .done-state b { font-weight: 600; }

  .filters { display: flex; align-items: center; gap: var(--sp-4) var(--sp-5); flex-wrap: wrap; padding: 0 0 var(--sp-5); }
  .chips { display: flex; gap: var(--sp-2); flex-wrap: wrap; }
  .check-all { display: inline-flex; align-items: center; gap: var(--sp-4); color: var(--text-2); cursor: pointer; padding-left: 6px; }
  .src-select { width: auto; max-width: 280px; }

  .list { background: var(--surface); border-radius: var(--r-lg); box-shadow: var(--e1); overflow: hidden; }
  .atoms { list-style: none; margin: 0; padding: 0; }
  .atom { display: grid; grid-template-columns: 16px 64px minmax(0, 1fr) auto; gap: var(--sp-5); align-items: start;
    padding: var(--sp-5) var(--sp-6); border-bottom: 1px solid var(--line); position: relative; scroll-margin: 80px 0 96px;
    transition: background var(--t-fast); cursor: default; }
  .atom:last-child { border-bottom: 0; }
  .atom:hover { background: color-mix(in srgb, var(--surface-2) 50%, transparent); }
  .atom .cb-hit { margin: -4px -6px; }
  .atom.checked { background: var(--accent-bg); }
  /* focus ≠ selection: focus is the accent bar and ring, selection the tint; both can combine */
  .atom.sel { box-shadow: inset 0 0 0 1px var(--accent-line); }
  .atom.sel::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent); border-radius: 0 2px 2px 0; }
  .type { justify-self: start; }
  .body { min-width: 0; }
  .stm { font-size: var(--fs-14); line-height: 20px; font-weight: 500; }
  .atom.accepted .stm { color: var(--text-2); }
  .atom.rejected .stm { color: var(--text-2); text-decoration: line-through; text-decoration-color: var(--text-3); }
  .atom.rejected .quote { opacity: .6; }
  .body .hint { margin-top: 2px; }
  .quote { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-top: 4px; text-align: left;
    font-size: var(--fs-13); line-height: 18px; color: var(--text-2); }
  .quote::before { content: "«"; } .quote::after { content: "»"; }
  button.quote:hover { color: var(--accent); }
  .meta { margin-top: 2px; font-size: var(--fs-12); color: var(--text-3); font-variant-numeric: tabular-nums; }
  .conf-line { display: flex; align-items: baseline; gap: 4px; margin-top: 4px; color: var(--danger); font-size: var(--fs-12); font-weight: 500; }
  .conf-line :global(.icon) { align-self: center; }
  .side { display: flex; align-items: center; gap: var(--sp-4); }
  .state { font-size: var(--fs-12); font-weight: 500; display: inline-flex; gap: 4px; align-items: center; color: var(--text-3); white-space: nowrap; }
  .state.ok { color: var(--ok); }
  .acts { display: flex; gap: 2px; opacity: 0; transition: opacity var(--t-fast); }
  .atom:hover .acts, .atom:focus-within .acts, .atom.sel .acts { opacity: 1; }
  @media (hover: none) { .acts { opacity: 1; } }
  .on-ok { color: var(--ok) !important; background: var(--ok-bg) !important; }
  .on-no { color: var(--danger) !important; background: var(--danger-bg) !important; }
  .del:hover { color: var(--danger) !important; }
  .area { resize: vertical; }
  .edit-row { margin-top: var(--sp-4); }
  .keys { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; font-size: var(--fs-12); color: var(--text-3);
    padding: var(--sp-5) var(--sp-6); border-top: 1px solid var(--line); }
  .keys > span { display: inline-flex; gap: 2px; }
  .keys :global(.kbd) { margin: 0 2px; }
  .bulk-on .list { margin-bottom: 72px; }        /* the bulk bar never covers the last row */

  .bulkbar { position: fixed; z-index: 50; left: calc(50% + var(--sidebar-w) / 2); bottom: var(--sp-7); transform: translateX(-50%);
    display: flex; align-items: center; gap: var(--sp-3); padding: 6px; border-radius: var(--r-xl); background: var(--hud); color: var(--hud-text);
    box-shadow: var(--e3); max-width: calc(100vw - var(--sidebar-w) - 32px); flex-wrap: wrap; animation: hud-in var(--t-slow) var(--ease); }
  @keyframes hud-in { from { opacity: 0; transform: translate(-50%, 16px); } to { opacity: 1; transform: translate(-50%, 0); } }
  .bulkbar .count { padding: 0 var(--sp-4) 0 var(--sp-5); font-weight: 600; white-space: nowrap; }
  .bulkbar .conf { color: #F29C8C; font-weight: 500; font-size: var(--fs-12); white-space: nowrap; }
  .bulkbar .vsep { width: 1px; height: 20px; background: var(--hud-line); margin: 0 2px; }
  .bulkbar .btn { background: transparent; color: var(--hud-text); box-shadow: none; height: 28px; font-size: var(--fs-13); }
  .bulkbar .btn:hover:not(:disabled) { background: rgba(255,255,255,.08); }
  .bulkbar .btn :global(.kbd) { background: transparent; color: var(--hud-text-2); box-shadow: inset 0 0 0 1px var(--hud-line); }
  .bulkbar .btn.accept { background: #2F6DAE; }
  .bulkbar .btn.accept:hover:not(:disabled) { background: #3A7BBE; }
  .bulkbar .btn.accept :global(.kbd) { box-shadow: inset 0 0 0 1px rgba(255,255,255,.3); color: #fff; }
  .bulkbar .danger-text { color: #F29C8C; }
  .bulkbar .select { height: 28px; width: auto; background-color: transparent; color: var(--hud-text); border-color: var(--hud-line); }
  .bulkbar .select option { color: #000; }
  @media (max-width: 720px) { .bulkbar { left: 50%; max-width: calc(100vw - 32px); } }

  .sources-block { margin-top: var(--sp-8); }
  .sources { list-style: none; margin: 0; padding: 0; }
  .src { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-4); padding: var(--sp-4) 0; border-top: 1px solid var(--line); }
  .src:first-child { border-top: 0; }
  .src-title { font-weight: 500; text-align: left; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
  .src-title:hover { color: var(--accent); }

  @media (max-width: 960px) {
    .atom { grid-template-columns: 16px minmax(0, 1fr) auto; }
    .atom > .type { grid-column: 2; grid-row: 1; }
    .atom > .body { grid-column: 2; grid-row: 2; margin-top: -6px; }
    .atom > .side { grid-column: 3; grid-row: 1 / span 2; }
    .src-select { max-width: 100%; }
  }
</style>
