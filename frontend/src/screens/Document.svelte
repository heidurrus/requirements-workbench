<script>
  import Block from "../components/Block.svelte";
  import Icon from "../components/Icon.svelte";
  import { api, pollJob } from "../lib/api.js";
  import { fmtDate, fmtTime } from "../lib/format.js";
  import { saveUrl } from "../lib/save.js";
  import { app, t, go, toast } from "../lib/state.svelte.js";

  let body = $state(null);
  let error = $state("");
  let viewing = $state(null);            // version number, null = latest
  let diff = $state(null);               // {from, to, changes} while comparing
  let build = $state(null);              // {progress, message} while building
  let editingTitle = $state(false);
  let titleDraft = $state("");
  let editAtom = $state(null);           // {atom_id, text}
  let freeDraft = $state(null);          // {section, id?, text}
  let fixes = $state({});                // `${atom_id}:${rule}` → {loading, statement}
  let exportSkills = $state([]);
  $effect(() => { api("/api/skills").then(b => (exportSkills = b.skills.filter(s => s.stage === "export" && !s.error))).catch(() => {}); });

  async function load() {
    const pid = app.currentProjectId;
    try {
      const q = viewing ? `?version=${viewing}` : "";
      const b = await api(`/api/projects/${pid}/document${q}`);
      if (pid !== app.currentProjectId) return;
      body = b;
      error = "";
      if (b.building && !build) follow(b.building);
    } catch (err) { error = err.message; }
  }
  $effect(() => { app.currentProjectId; app.atomsVersion; viewing; load(); });

  const doc = $derived(body?.document);
  const version = $derived(body?.version);
  const content = $derived(version?.content);
  const latest = $derived(body?.versions?.[0]?.number || 0);
  const isLatest = $derived(!version || version.number === latest);
  const stats = $derived(body?.stats);
  const freeBy = $derived.by(() => {
    const out = {};
    for (const f of body?.free_blocks || []) (out[f.section] ||= []).push(f);
    return out;
  });
  const findings = $derived.by(() => {
    if (!content) return [];
    const out = [];
    for (const sec of content.sections)
      for (const b of [...sec.blocks, ...(sec.subsections || []).flatMap(s => s.blocks)])
        if (b.kind === "req") for (const i of b.issues || []) out.push({ ...i, block: b });
    return out;
  });
  const staleSections = $derived(body?.stale ? Object.keys(body.stale.sections).sort().join(", ") : "");

  async function follow(jobId) {
    build = { progress: 0, message: t("doc.writing") };
    try {
      const job = await pollJob(jobId, j => (build = { progress: j.progress || 0, message: j.progress_msg || "" }), { interval: 800 });
      viewing = null;
      diff = null;
      toast(t("doc.built", { v: job.result.version }));
    } catch (err) {
      const setup = err.body?.needs_setup || /API key|Settings/.test(err.message);
      toast(err.message, { kind: "danger", ...(setup ? { action: t("nav.settings"), onAction: () => go("/settings") } : {}) });
    } finally {
      build = null;
      load();
    }
  }

  async function runBuild(mode) {
    try {
      const { job_id } = await api(`/api/projects/${app.currentProjectId}/document/build`, { method: "POST", body: { mode } });
      follow(job_id);
    } catch (err) {
      const setup = err.body?.needs_setup;
      toast(err.message, { kind: "danger", ...(setup ? { action: t("nav.settings"), onAction: () => go("/settings") } : {}) });
    }
  }

  async function patchDoc(changes) {
    try { body.document = await api(`/api/documents/${doc.id}`, { method: "PATCH", body: changes }); }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }
  function saveTitle() {
    editingTitle = false;
    if (titleDraft.trim() && titleDraft.trim() !== doc.title) patchDoc({ title: titleDraft.trim() });
  }

  async function toggleDiff() {
    if (diff) { diff = null; return; }
    try { diff = await api(`/api/documents/${doc.id}/diff?to=${version.number}`); }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }

  function exportDocx() {
    const name = `${doc.title} v${version.number}.docx`.replace(/[\\/:*?"<>|]/g, "");
    saveUrl(`/api/documents/${doc.id}/export.docx?version=${version.number}&template=${doc.template}`, name);
  }

  // editing the atom behind a block (D-07: prose changes through atoms; marks the section stale)
  async function saveAtom() {
    const { atom_id, text } = editAtom;
    editAtom = null;
    try {
      await api(`/api/atoms/${atom_id}`, { method: "PATCH", body: { statement: text } });
      app.atomsVersion++;
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function saveFree() {
    const f = freeDraft;
    freeDraft = null;
    if (!f.text.trim()) return;
    try {
      if (f.id) await api(`/api/free-blocks/${f.id}`, { method: "PATCH", body: { text: f.text } });
      else await api(`/api/documents/${doc.id}/free-blocks`, { method: "POST", body: { section: f.section, text: f.text } });
      load();
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function removeFree(f) {
    await api(`/api/free-blocks/${f.id}`, { method: "DELETE" });
    load();
    toast(t("doc.free_deleted"), { action: t("at.undo"),
      onAction: async () => { await api(`/api/free-blocks/${f.id}/restore`, { method: "POST" }); load(); } });
  }

  const fixKey = f => `${f.block.atom_id}:${f.rule}`;
  async function fix(f) {
    fixes[fixKey(f)] = { loading: true };
    try {
      const { job_id } = await api(`/api/documents/${doc.id}/fix`, { method: "POST",
        body: { atom_id: f.block.atom_id, rule: f.rule, message: f.message } });
      const job = await pollJob(job_id, null, { interval: 700 });
      fixes[fixKey(f)] = { statement: job.result.statement };
    } catch (err) {
      delete fixes[fixKey(f)];
      toast(err.message, { kind: "danger" });
    }
  }
  async function acceptFix(f) {
    const statement = fixes[fixKey(f)].statement;
    delete fixes[fixKey(f)];
    try {
      await api(`/api/atoms/${f.block.atom_id}`, { method: "PATCH", body: { statement } });
      app.atomsVersion++;
      toast(t("doc.fix_applied"));
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function dismiss(f) {
    await api(`/api/documents/${doc.id}/dismiss`, { method: "POST", body: { atom_id: f.block.atom_id, rule: f.rule } });
    load();
  }

  function sourcesLabel(b) {
    const n = b.sources.length;
    return n ? t("doc.from_atom_n", { n }) : t("doc.from_atom");
  }
  function sourceRef(s) {
    const date = s.source_date ? new Date(s.source_date * 1000).toLocaleDateString(app.lang, { day: "2-digit", month: "2-digit" }) : "";
    return [date, s.start != null ? fmtTime(s.start) : null].filter(Boolean).join(" — ");
  }
  function scrollTo(id) { document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }); }
  const ago = ts => fmtDate(ts, app.lang);
</script>

<div class="screen-inner">
  <header class="screen-head">
    <div class="head-main">
      {#if doc}
        {#if editingTitle}
          <!-- svelte-ignore a11y_autofocus -->
          <input class="input title-input" bind:value={titleDraft} autofocus onblur={saveTitle}
                 onkeydown={e => { if (e.key === "Enter") saveTitle(); if (e.key === "Escape") editingTitle = false; }} />
        {:else}
          <h1 class="screen-title">
            <button class="title-btn" title={t("tr.edit_title")} onclick={() => { titleDraft = doc.title; editingTitle = true; }}>
              {doc.title} <span class="pen"><Icon name="pencil" size={14} /></span></button>
          </h1>
        {/if}
        <p class="screen-sub">
          {#if version}{t("doc.sub", { v: version.number, n: version.atom_count, when: ago(version.created_at) })}
            {#if version.model}<span class="faint"> · {version.model}</span>{/if}
          {:else}{t("doc.never")}{/if}
        </p>
      {:else}
        <h1 class="screen-title">{t("nav.document")}</h1>
      {/if}
    </div>
    {#if doc}
      <div class="actions">
        {#if !version}
          <button class="btn btn-primary" disabled={!!build || !stats?.accepted} onclick={() => runBuild("full")}>{t("doc.build")}</button>
        {:else}
          <button class="btn" class:btn-primary={body.stale?.stale} disabled={!!build || !body.stale?.stale}
                  title={body.stale?.stale ? "" : t("doc.up_to_date")} onclick={() => runBuild("changed")}>{t("doc.rebuild")}</button>
          <button class="btn btn-ghost" disabled={!!build} onclick={() => runBuild("full")} title={t("doc.full_hint")}>{t("doc.full")}</button>
          <div class="export">
            <select class="select tpl" aria-label={t("doc.template")} value={doc.template}
                    onchange={e => patchDoc({ template: e.currentTarget.value })}>
              {#each exportSkills as s (s.name)}<option value={s.name}>{s.title}</option>{/each}
            </select>
            <button class="btn btn-primary" onclick={exportDocx}><Icon name="download" /> {t("doc.export")}</button>
          </div>
          <button class="btn btn-ghost" onclick={() => go("/backlog")}>{t("doc.to_backlog")} →</button>
        {/if}
      </div>
    {/if}
  </header>

  {#if error}<p class="note danger">{error}</p>{/if}

  {#if body}
    <div class="stack">
      {#if build}
        <div class="panel building">
          <span class="spinner"></span>
          <div class="grow"><div class="bar"><i style="width: {build.progress}%"></i></div></div>
          <span class="mono faint">{build.message}</span>
        </div>
      {/if}

      {#if !stats.accepted}
        <div class="empty panel">
          <p class="panel-title">{t("doc.no_atoms_title")}</p>
          <p>{t("doc.no_atoms")}</p>
          <button class="btn" style="margin-top: var(--s-3)" onclick={() => go("/atoms")}>{t("doc.to_atoms")}</button>
        </div>
      {:else if !version}
        <div class="empty panel">
          <p class="panel-title">{t("doc.ready_title", { n: stats.accepted })}</p>
          <p>{t("doc.ready")}</p>
          {#if stats.pending}<p class="hint" style="margin-top: var(--s-2)">{t("doc.pending", { n: stats.pending })}</p>{/if}
        </div>
      {:else}
        {#if isLatest && body.stale?.stale}
          <p class="note warn row-note">
            <span>{t("doc.stale", { n: body.stale.changed + body.stale.removed + body.stale.added })}{#if staleSections} · {t("doc.stale_sections", { s: staleSections })}{/if}</span>
            <button class="btn btn-sm" disabled={!!build} onclick={() => runBuild("changed")}>{t("doc.rebuild")}</button>
          </p>
        {/if}
        {#if stats.open_conflicts}<p class="note warn">{t("doc.conflicts", { n: stats.open_conflicts })}</p>{/if}
        {#if stats.pending}<p class="hint">{t("doc.pending", { n: stats.pending })}</p>{/if}

        <div class="toolbar">
          {#if body.versions.length > 1}
            <label class="ver">
              <span class="label">{t("doc.version")}</span>
              <select class="select" value={version.number} onchange={e => { diff = null; viewing = Number(e.currentTarget.value) === latest ? null : Number(e.currentTarget.value); }}>
                {#each body.versions as v (v.number)}<option value={v.number}>v{v.number} · {ago(v.created_at)}</option>{/each}
              </select>
            </label>
            {#if version.number > 1}
              <button class="btn btn-sm" aria-pressed={!!diff} class:on={!!diff} onclick={toggleDiff}>
                {diff ? t("doc.hide_diff") : t("doc.diff", { v: version.number - 1 })}</button>
            {/if}
          {/if}
          {#if !isLatest}<span class="tag warn">{t("doc.old_version")}</span>{/if}
        </div>

        {#if diff}
          <Block id="doc-diff" title={t("doc.diff_title", { a: diff.from, b: diff.to })} meta={String(diff.changes.length)}>
            {#if !diff.changes.length}<p class="muted">{t("doc.no_changes")}</p>{/if}
            <ul class="changes">
              {#each diff.changes as c (c.id + c.change)}
                <li class="change {c.change}">
                  <span class="mono">{c.section} · {c.id}</span>
                  <span class="tag {c.change === 'added' ? 'ok' : c.change === 'removed' ? 'danger' : 'warn'}">{t("doc.change." + c.change)}</span>
                  {#if c.moved_from}<span class="hint">{t("doc.moved", { s: c.moved_from })}</span>{/if}
                  {#if c.old}<p class="old">{c.old}</p>{/if}
                  {#if c.new}<p class="new">{c.new}</p>{/if}
                </li>
              {/each}
            </ul>
          </Block>
        {/if}

        {#if findings.length && isLatest}
          <Block id="doc-quality" title={t("doc.quality")} meta={t("doc.findings", { n: findings.length })}>
            <ul class="findings">
              {#each findings as f (fixKey(f))}
                <li class="finding">
                  <div class="f-head">
                    <button class="mono link" onclick={() => scrollTo("blk-" + f.block.id)}>{f.block.id}</button>
                    <span class="tag warn">{t("doc.rule." + f.rule)}</span>
                    <span class="f-msg">{f.message}</span>
                    <span class="spacer"></span>
                    {#if !fixes[fixKey(f)]}
                      <button class="btn btn-sm" onclick={() => fix(f)}>{t("doc.fix")}</button>
                      <button class="btn btn-sm btn-ghost" onclick={() => dismiss(f)}>{t("doc.dismiss")}</button>
                    {:else if fixes[fixKey(f)].loading}
                      <span class="spinner"></span>
                    {/if}
                  </div>
                  {#if fixes[fixKey(f)]?.statement !== undefined}
                    <div class="f-fix">
                      <span class="label">{t("doc.fix_proposal")}</span>
                      <textarea class="input area" rows="2" bind:value={fixes[fixKey(f)].statement}></textarea>
                      <div class="actions">
                        <button class="btn btn-sm btn-primary" disabled={!fixes[fixKey(f)].statement.trim()} onclick={() => acceptFix(f)}>{t("doc.fix_accept")}</button>
                        <button class="btn btn-sm btn-ghost" onclick={() => delete fixes[fixKey(f)]}>{t("at.cancel")}</button>
                      </div>
                    </div>
                  {/if}
                </li>
              {/each}
            </ul>
          </Block>
        {/if}

        <div class="doc">
          <nav class="toc" aria-label={t("doc.toc")}>
            {#each content.sections as sec (sec.key)}
              <button onclick={() => scrollTo("sec-" + sec.key)}>{sec.number}. {sec.title}</button>
              {#each sec.subsections || [] as sub (sub.key)}
                <button class="ind" onclick={() => scrollTo("sec-" + sub.key)}>{sub.number} {sub.title}</button>
              {/each}
            {/each}
          </nav>

          <article class="panel paper">
            {#each content.sections as sec (sec.key)}
              <section class="sec" id="sec-{sec.key}">
                <h2>{sec.number}. {sec.title}</h2>
                {#each freeBy[sec.key] || [] as f (f.id)}
                  {@render freeBlock(f)}
                {/each}
                {@render blocks(sec.blocks)}
                {#each sec.subsections || [] as sub (sub.key)}
                  <section class="sub" id="sec-{sub.key}">
                    <h3>{sub.number} {sub.title}</h3>
                    {@render blocks(sub.blocks)}
                  </section>
                {/each}
                {#if !sec.blocks.length && !(sec.subsections || []).length && !(freeBy[sec.key] || []).length}
                  <p class="faint">{t("doc.empty_section")}</p>
                {/if}
                {#if isLatest}
                  {#if freeDraft && !freeDraft.id && freeDraft.section === sec.key}
                    {@render freeEditor()}
                  {:else}
                    <button class="btn btn-sm btn-ghost add-free" onclick={() => (freeDraft = { section: sec.key, text: "" })}>
                      <Icon name="plus" /> {t("doc.add_free")}</button>
                  {/if}
                {/if}
              </section>
            {/each}
          </article>
        </div>
      {/if}
    </div>
  {/if}
</div>

{#snippet freeEditor()}
  <div class="free-edit">
    <!-- svelte-ignore a11y_autofocus -->
    <textarea class="input area" rows="3" bind:value={freeDraft.text} autofocus placeholder={t("doc.free_placeholder")}
              onkeydown={e => e.key === "Escape" && (freeDraft = null)}></textarea>
    <div class="actions">
      <button class="btn btn-sm btn-primary" disabled={!freeDraft.text.trim()} onclick={saveFree}>{t("at.save")}</button>
      <button class="btn btn-sm btn-ghost" onclick={() => (freeDraft = null)}>{t("at.cancel")}</button>
    </div>
  </div>
{/snippet}

{#snippet freeBlock(f)}
  {#if freeDraft?.id === f.id}
    {@render freeEditor()}
  {:else}
    <div class="blk free">
      <div class="meta"><span>{t("doc.free")}</span>
        {#if isLatest}<span class="blk-acts">
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("at.edit")} onclick={() => (freeDraft = { section: f.section, id: f.id, text: f.text })}><Icon name="pencil" /></button>
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")} onclick={() => removeFree(f)}><Icon name="trash" /></button>
        </span>{/if}
      </div>
      <p class="body">{f.text}</p>
    </div>
  {/if}
{/snippet}

{#snippet blocks(list)}
  {#each list as b (b.id)}
    {#if b.kind === "req"}
      <div class="blk" id="blk-{b.id}" class:q={b.type === "question"} class:flagged={(b.issues || []).length}>
        <div class="meta">
          <span><span class="rid">{b.id}</span> · {sourcesLabel(b)}</span>
          {#if isLatest}<span class="blk-acts">
            <button class="btn btn-ghost btn-sm icon-btn" title={t("doc.edit_atom")} aria-label={t("doc.edit_atom")}
                    onclick={() => (editAtom = { atom_id: b.atom_id, text: b.text })}><Icon name="pencil" /></button>
          </span>{/if}
        </div>
        {#if editAtom?.atom_id === b.atom_id}
          <div class="free-edit">
            <span class="hint">{t("doc.edit_atom_hint")}</span>
            <!-- svelte-ignore a11y_autofocus -->
            <textarea class="input area" rows="2" bind:value={editAtom.text} autofocus
                      onkeydown={e => e.key === "Escape" && (editAtom = null)}></textarea>
            <div class="actions">
              <button class="btn btn-sm btn-primary" disabled={!editAtom.text.trim()} onclick={saveAtom}>{t("at.save")}</button>
              <button class="btn btn-sm btn-ghost" onclick={() => (editAtom = null)}>{t("at.cancel")}</button>
            </div>
          </div>
        {:else}
          <p class="body">{b.text}</p>
        {/if}
        {#if b.sources.length}
          <p class="refs">{t("doc.sources")}:
            {#each b.sources as s, i (i)}<button class="link" title={s.quote}
              onclick={() => go(`/source/${s.source_id}/seg/${s.segment_idx}`)}>{sourceRef(s) || s.source_title}</button>{i < b.sources.length - 1 ? ", " : ""}{/each}
          </p>
        {/if}
        {#if b.conflict}<p class="note danger c-note">{t("at.conflict_with", { text: b.conflict })}</p>{/if}
      </div>
    {:else if b.kind === "text"}
      <p class="prose">{b.text}</p>
    {:else if b.kind === "list"}
      {#if b.title}<p class="list-title">{b.title}</p>{/if}
      <ul class="prose-list">{#each b.items as item, i (i)}<li>{item}</li>{/each}</ul>
    {/if}
  {/each}
{/snippet}

<style>
  .head-main { min-width: 0; flex: 1; }
  .title-btn { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: text; text-align: left; }
  .title-btn .pen { color: var(--ink-3); opacity: 0; display: inline-block; vertical-align: middle; }
  .title-btn:hover .pen { opacity: 1; }
  .title-input { font-size: var(--t-xl); font-weight: 600; height: 40px; max-width: 640px; }
  .export { display: flex; gap: var(--s-2); align-items: center; }
  .export .tpl { width: auto; max-width: 220px; }

  .building { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
  .grow { flex: 1; }
  .row-note { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); flex-wrap: wrap; }
  .toolbar { display: flex; align-items: flex-end; gap: var(--s-3); flex-wrap: wrap; }
  .toolbar:empty { display: none; }
  .ver { display: flex; flex-direction: column; gap: var(--s-1); }
  .ver .select { height: 30px; width: auto; }
  .toolbar .on { border-color: var(--accent); color: var(--accent); }

  .changes, .findings { list-style: none; margin: 0; padding: 0; }
  .change, .finding { padding: var(--s-2) 0; border-top: 1px solid var(--rule); }
  .change:first-child, .finding:first-child { border-top: 0; padding-top: 0; }
  .change { display: flex; flex-wrap: wrap; gap: var(--s-1) var(--s-2); align-items: center; }
  .change p { flex-basis: 100%; line-height: 1.55; padding: var(--s-1) var(--s-2); border-radius: var(--r-sm); }
  .old { background: var(--danger-bg); color: var(--danger); text-decoration: line-through; }
  .new { background: var(--ok-bg); color: var(--ok); }
  .f-head { display: flex; align-items: center; flex-wrap: wrap; gap: var(--s-2); }
  .f-msg { font-size: var(--t-sm); color: var(--ink-2); min-width: 0; }
  .f-fix { display: flex; flex-direction: column; gap: var(--s-2); margin-top: var(--s-2); }
  .spacer { flex: 1; }
  .link { border: 0; background: none; padding: 0; font: inherit; color: var(--accent); cursor: pointer; }

  .doc { display: grid; grid-template-columns: 184px minmax(0, 1fr); gap: var(--s-4); align-items: start; }
  .toc { position: sticky; top: var(--s-4); display: flex; flex-direction: column; gap: 2px; font-size: var(--t-sm);
    max-height: calc(100vh - var(--s-6)); overflow-y: auto; }
  .toc button { border: 0; background: none; text-align: left; padding: 3px var(--s-2); border-radius: var(--r-sm);
    color: var(--ink-2); cursor: pointer; font: inherit; line-height: 1.4; }
  .toc button:hover { background: var(--sunk); color: var(--ink); }
  .toc .ind { padding-left: var(--s-4); }
  .paper { padding: var(--s-5) var(--s-6); }
  .sec + .sec { margin-top: var(--s-5); }
  .sec, .sub { scroll-margin-top: var(--s-4); }
  .sec h2 { font-size: var(--t-lg); font-weight: 600; margin-bottom: var(--s-3); }
  .sub { margin-top: var(--s-4); }
  .sub h3 { font-size: var(--t-md); font-weight: 600; margin-bottom: var(--s-2); }
  .prose { line-height: 1.7; max-width: 72ch; margin-bottom: var(--s-3); white-space: pre-line; }
  .list-title { font-weight: 500; margin: var(--s-2) 0 var(--s-1); }
  .prose-list { margin: 0 0 var(--s-3); padding-left: var(--s-5); line-height: 1.65; }

  .blk { padding: var(--s-2) 0 var(--s-2) var(--s-3); border-left: 2px solid var(--accent); margin-bottom: var(--s-3);
    scroll-margin-top: var(--s-4); }
  .blk.q { border-left-color: var(--warn); }
  .blk.free { border-left-color: var(--rule-2); }
  .blk.flagged .body { text-decoration: underline wavy var(--warn); text-decoration-thickness: 1px; text-underline-offset: 4px; }
  .meta { display: flex; justify-content: space-between; align-items: center; gap: var(--s-2); font-size: var(--t-xs);
    color: var(--ink-3); min-height: 24px; }
  .rid { color: var(--accent); font-family: var(--mono); }
  .blk.q .rid { color: var(--warn); }
  .blk-acts { display: flex; gap: 2px; opacity: .55; }
  .blk:hover .blk-acts { opacity: 1; }
  .body { line-height: 1.65; max-width: 72ch; }
  .refs { margin-top: var(--s-1); font-size: var(--t-xs); color: var(--ink-3); }
  .c-note { margin-top: var(--s-2); }
  .free-edit { display: flex; flex-direction: column; gap: var(--s-2); margin: var(--s-1) 0 var(--s-3); }
  .area { height: auto; padding: var(--s-2) var(--s-3); line-height: 1.5; resize: vertical; }
  .add-free { margin-left: calc(-1 * var(--s-3)); color: var(--ink-3); opacity: 0; transition: opacity .12s ease; }
  .sec:hover > .add-free, .add-free:focus-visible { opacity: 1; }
  @media (hover: none) { .add-free { opacity: 1; } }

  @media (max-width: 900px) {
    .doc { grid-template-columns: 1fr; }
    .toc { position: static; max-height: none; flex-direction: row; flex-wrap: wrap; }
    .toc .ind { display: none; }
    .paper { padding: var(--s-4); }
  }
</style>
