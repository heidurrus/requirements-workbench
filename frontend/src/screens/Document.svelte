<script>
  import Block from "../components/Block.svelte";
  import Icon from "../components/Icon.svelte";
  import { explain } from "../lib/errors.js";
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
  const projectLang = $derived(({ ru: "ru", en: "en" })[app.projects.find(p => p.id === app.currentProjectId)?.language] || null);
  const staleSections = $derived(body?.stale ? Object.keys(body.stale.sections).sort().join(", ") : "");

  async function follow(jobId) {
    build = { progress: 0, message: t("doc.writing") };
    try {
      const job = await pollJob(jobId, j => (build = { progress: j.progress || 0, message: j.progress_msg || "" }), { interval: 800 });
      viewing = null;
      diff = null;
      toast(t("doc.built", { v: job.result.version }));
    } catch (err) {
      const e = explain(err);
      toast(e.message, { kind: "danger", ...(e.setup ? { action: t("err.open_settings"), onAction: () => go("/settings") } : {}) });
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
      const e = explain(err);
      toast(e.message, { kind: "danger", ...(e.setup ? { action: t("err.open_settings"), onAction: () => go("/settings") } : {}) });
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
  const staleIds = $derived(new Set(isLatest && body?.stale?.stale ? body.stale.atom_ids : []));
  const flaggedSecs = $derived.by(() => {
    const out = {};
    if (!content) return out;
    for (const sec of content.sections) {
      const all = [...sec.blocks, ...(sec.subsections || []).flatMap(x => x.blocks)].filter(b => b.kind === "req");
      if (all.some(b => b.conflict)) out[sec.key] = "danger";
      else if (all.some(b => (b.issues || []).length || staleIds.has(b.atom_id))) out[sec.key] = "warn";
    }
    return out;
  });
  const typeOf = b => (b.type === "question" ? "q" : b.type === "nfr" || /^NFR/.test(b.id) ? "nfr" : "fr");
</script>

<div class="screen-inner wide">
  <header class="screen-head">
    <div class="head-main">
      {#if doc}
        {#if editingTitle}
          <!-- svelte-ignore a11y_autofocus -->
          <input class="input title-input" bind:value={titleDraft} autofocus onblur={saveTitle} aria-label={t("tr.edit_title")}
                 onkeydown={e => { if (e.key === "Enter") saveTitle(); if (e.key === "Escape") editingTitle = false; }} />
        {:else}
          <h1 class="screen-title">
            <button class="title-btn" title={t("tr.edit_title")} onclick={() => { titleDraft = doc.title; editingTitle = true; }}>
              {doc.title} <span class="pen"><Icon name="pencil" size={12} /></span></button>
          </h1>
        {/if}
        <p class="screen-sub">
          {#if version}{t("doc.sub", { v: version.number, n: version.atom_count, when: ago(version.created_at) })}{#if !isLatest}{" · "}<span class="old">{t("doc.old_version")}</span>{/if}
          {:else}{t("doc.never")}{/if}
        </p>
      {:else}
        <h1 class="screen-title">{t("nav.document")}</h1>
      {/if}
    </div>
    {#if doc}
      <div class="actions">
        {#if !version}
          {#if stats?.accepted}
            <button class="btn btn-primary" disabled={!!build} onclick={() => runBuild("full")}>{t("doc.build")}</button>
          {/if}
        {:else}
          {#if version.number > 1}
            <button class="btn btn-ghost" aria-pressed={!!diff} onclick={toggleDiff}>
              <Icon name="compare" size={14} /> {diff ? t("doc.hide_diff") : t("doc.diff", { v: version.number - 1 })}</button>
          {/if}
          {#if body.stale?.stale}
            <div class="split">
              <button class="btn btn-primary" disabled={!!build} onclick={() => runBuild("changed")}>
                <Icon name="refresh" size={14} /> {t("doc.rebuild")}</button>
              <button class="btn" disabled={!!build} onclick={() => runBuild("full")} title={t("doc.full_hint")}>{t("doc.full")}</button>
            </div>
          {:else}
            <button class="btn btn-ghost" disabled={!!build} onclick={() => runBuild("full")} title={t("doc.full_hint")}>
              <Icon name="refresh" size={14} /> {t("doc.full")}</button>
          {/if}
          <span class="tb-sep"></span>
          <div class="split export">
            <button class="btn" class:btn-primary={!body.stale?.stale} onclick={exportDocx}><Icon name="download" size={14} /> {t("doc.export")}</button>
            <select class="btn select tpl" class:btn-primary={!body.stale?.stale} aria-label={t("doc.template")} value={doc.template}
                    title={t("doc.template")} onchange={e => patchDoc({ template: e.currentTarget.value })}>
              {#each exportSkills as s (s.name)}<option value={s.name}>{s.title}</option>{/each}
            </select>
          </div>
          <button class="btn btn-ghost" onclick={() => go("/backlog")}>{t("doc.to_backlog")} <Icon name="arrow" size={14} /></button>
        {/if}
      </div>
    {/if}
  </header>

  {#if error}<p class="note danger">{error}</p>{/if}

  {#if body}
    {#if build}
      <div class="banner info building">
        <span class="spinner"></span>
        <span class="num">{build.message}</span>
        <div class="grow"><div class="bar"><i style="width: {build.progress}%"></i></div></div>
      </div>
    {/if}

    {#if !stats.accepted}
      <div class="card empty narrow-card">
        <div class="glyph"><Icon name="doc" /></div>
        <p class="panel-title">{t("doc.no_atoms_title")}</p>
        <p>{t("doc.no_atoms")}</p>
        <button class="btn btn-lg btn-primary" onclick={() => go("/atoms")}>{t("doc.to_atoms")}</button>
      </div>
    {:else if !version}
      <div class="card empty narrow-card">
        <div class="glyph"><Icon name="doc" /></div>
        <p class="panel-title">{t("doc.ready_title", { n: stats.accepted })}</p>
        <p>{t("doc.ready")}</p>
        {#if stats.pending}<p class="hint">{t("doc.pending", { n: stats.pending })}</p>{/if}
      </div>
    {:else}
      <div class="doc-layout" class:has-notes={(findings.length && isLatest) || diff}>
        <nav class="toc" aria-label={t("doc.toc")}>
          <h4>{t("doc.toc")}</h4>
          {#each content.sections as sec (sec.key)}
            <button onclick={() => scrollTo("sec-" + sec.key)}><span class="tn">{sec.number}.</span> {sec.title}
              {#if flaggedSecs[sec.key]}<span class="dot {flaggedSecs[sec.key]}"></span>{/if}</button>
            {#each sec.subsections || [] as sub (sub.key)}
              <button class="ind" onclick={() => scrollTo("sec-" + sub.key)}><span class="tn">{sub.number}</span> {sub.title}</button>
            {/each}
          {/each}
          {#if body.versions.length > 1}
            <div class="ver">
              <h4>{t("doc.version")}</h4>
              {#each body.versions as v (v.number)}
                <button class="v" class:on={v.number === version.number}
                        onclick={() => { diff = null; viewing = v.number === latest ? null : v.number; }}>
                  <span>v{v.number}</span><span class="t3 num">{ago(v.created_at)}</span></button>
              {/each}
            </div>
          {/if}
        </nav>

        <div class="paper-col">
      <div class="banners">
            {#if isLatest && body.stale?.stale}
              <p class="banner warn row-note">
                <Icon name="warn" />
                <span class="grow"><b>{t("doc.stale", { n: body.stale.changed + body.stale.removed + body.stale.added })}</b>{#if staleSections} · {t("doc.stale_sections", { s: staleSections })}{/if}</span>
                <button class="btn btn-sm" disabled={!!build} onclick={() => runBuild("changed")}>{t("doc.rebuild")}</button>
              </p>
            {/if}
            {#if stats.open_conflicts}<p class="banner danger"><Icon name="warn" /><span class="grow">{t("doc.conflicts", { n: stats.open_conflicts })}</span>
              <button class="btn btn-sm" onclick={() => go("/atoms")}>{t("at.resolve")}</button></p>{/if}
            {#if isLatest && projectLang && content.language !== projectLang}
              <p class="banner warn row-note"><Icon name="info" /><span class="grow">{t("doc.lang_mismatch", { doc: t("lang." + content.language), want: t("lang." + projectLang) })}</span>
                <button class="btn btn-sm" disabled={!!build} onclick={() => runBuild("full")}>{t("doc.full")}</button></p>
            {/if}
            {#if stats.pending}<p class="hint-line"><Icon name="info" size={12} /> {t("doc.pending", { n: stats.pending })}</p>{/if}
          </div>
        <article class="paper" class:diff-on={!!diff}>
          <p class="doc-kicker">FRD · {t("doc.sub", { v: version.number, n: version.atom_count, when: ago(version.created_at) })}{#if version.model} · {version.model}{/if}</p>
          <h1>{doc.title}</h1>
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
                <p class="muted-i">{t("doc.empty_section")}</p>
              {/if}
              {#if isLatest}
                {#if freeDraft && !freeDraft.id && freeDraft.section === sec.key}
                  {@render freeEditor()}
                {:else}
                  <button class="btn btn-ghost btn-sm add-free" onclick={() => (freeDraft = { section: sec.key, text: "" })}>
                    <Icon name="plus" size={14} /> {t("doc.add_free")}</button>
                {/if}
              {/if}
            </section>
          {/each}
        </article>
        </div>

        {#if (findings.length && isLatest) || diff}
          <aside class="notes">
            {#if diff}
              <h4><span>{t("doc.diff_title", { a: diff.from, b: diff.to })}</span><span class="num">{diff.changes.length}</span></h4>
              {#if !diff.changes.length}<p class="hint">{t("doc.no_changes")}</p>{/if}
              {#each diff.changes as c (c.id + c.change)}
                <div class="finding change {c.change}">
                  <div class="fh"><span class="mono">{c.id}</span><span class="t3">{c.section}</span>
                    <span class="tag {c.change === 'added' ? 'ok' : c.change === 'removed' ? 'danger' : 'warn'}">{t("doc.change." + c.change)}</span></div>
                  {#if c.moved_from}<p class="hint">{t("doc.moved", { s: c.moved_from })}</p>{/if}
                  {#if c.old}<p><del>{c.old}</del></p>{/if}
                  {#if c.new}<p><ins>{c.new}</ins></p>{/if}
                </div>
              {/each}
            {/if}
            {#if findings.length && isLatest}
              <h4><span>{t("doc.quality")}</span><span class="num">{t("doc.findings", { n: findings.length })}</span></h4>
              {#each findings as f (fixKey(f))}
                <div class="finding">
                  <div class="fh">
                    <button class="mono link" onclick={() => scrollTo("blk-" + f.block.id)}>{f.block.id}</button>
                    <span class="tag warn">{t("doc.rule." + f.rule)}</span>
                  </div>
                  <p>{f.message}</p>
                  {#if fixes[fixKey(f)]?.statement !== undefined}
                    <p class="prop-lbl">{t("doc.fix_proposal")}</p>
                    <textarea class="input area" rows="3" bind:value={fixes[fixKey(f)].statement} aria-label={t("doc.fix_proposal")}></textarea>
                    <div class="acts">
                      <button class="btn btn-sm btn-primary" disabled={!fixes[fixKey(f)].statement.trim()} onclick={() => acceptFix(f)}>{t("doc.fix_accept")}</button>
                      <button class="btn btn-sm btn-ghost" onclick={() => delete fixes[fixKey(f)]}>{t("at.cancel")}</button>
                    </div>
                  {:else if fixes[fixKey(f)]?.loading}
                    <div class="acts"><span class="spinner"></span></div>
                  {:else}
                    <div class="acts">
                      <button class="btn btn-sm" onclick={() => fix(f)}><Icon name="bolt" size={12} /> {t("doc.fix")}</button>
                      <button class="btn btn-sm btn-ghost" onclick={() => dismiss(f)}>{t("doc.dismiss")}</button>
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          </aside>
        {/if}
      </div>
    {/if}
  {/if}
</div>

{#snippet freeEditor()}
  <div class="free-edit">
    <!-- svelte-ignore a11y_autofocus -->
    <textarea class="input area" rows="3" bind:value={freeDraft.text} autofocus placeholder={t("doc.free_placeholder")}
              aria-label={t("doc.add_free")} onkeydown={e => e.key === "Escape" && (freeDraft = null)}></textarea>
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
      <div class="lbl"><Icon name="pin" size={12} /> <span>{t("doc.free")}</span>
        {#if isLatest}<span class="row-actions">
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("at.edit")} title={t("at.edit")} onclick={() => (freeDraft = { section: f.section, id: f.id, text: f.text })}><Icon name="pencil" size={14} /></button>
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")} title={t("sources.delete")} onclick={() => removeFree(f)}><Icon name="trash" size={14} /></button>
        </span>{/if}
      </div>
      <p class="body">{f.text}</p>
    </div>
  {/if}
{/snippet}

{#snippet blocks(list)}
  {#each list as b (b.id)}
    {#if b.kind === "req"}
      <div class="blk req {typeOf(b)}" id="blk-{b.id}" class:stale={staleIds.has(b.atom_id)} class:flagged={(b.issues || []).length}>
        <span class="rid" title={sourcesLabel(b)}>{b.id}</span>
        <div class="txt">
          {#if editAtom?.atom_id === b.atom_id}
            <div class="free-edit">
              <span class="hint">{t("doc.edit_atom_hint")}</span>
              <!-- svelte-ignore a11y_autofocus -->
              <textarea class="input area" rows="2" bind:value={editAtom.text} autofocus aria-label={t("doc.edit_atom")}
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
            <p class="src" aria-label={sourcesLabel(b)}>
              {#each b.sources as s, i (i)}<button class="src-chip" title={s.quote}
                onclick={() => go(`/source/${s.source_id}/seg/${s.segment_idx}`)}><Icon name="transcript" size={12} />
                {s.source_title}{#if sourceRef(s)}<span class="num"> · {sourceRef(s)}</span>{/if}</button>{/each}
            </p>
          {/if}
          {#if b.conflict || (b.issues || []).length || staleIds.has(b.atom_id)}
            <p class="flag">
              {#if b.conflict}<span class="tag danger" title={b.conflict}><Icon name="warn" size={12} /> {t("at.conflict_with", { text: b.conflict })}</span>
              {:else if (b.issues || []).length}<span class="tag warn">{t("doc.rule." + b.issues[0].rule)}</span>
              {:else}<span class="tag warn">{t("nav.badge_stale")}</span>{/if}
            </p>
          {/if}
        </div>
        {#if isLatest}<span class="row-actions">
          <button class="btn btn-ghost btn-sm icon-btn" title={t("doc.edit_atom")} aria-label={t("doc.edit_atom")}
                  onclick={() => (editAtom = { atom_id: b.atom_id, text: b.text })}><Icon name="pencil" size={14} /></button>
        </span>{/if}
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
  .screen-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .title-btn { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: text; text-align: left; max-width: 100%; }
  .title-btn .pen { color: var(--text-3); opacity: 0; display: inline-block; vertical-align: middle; }
  .title-btn:hover .pen { opacity: 1; }
  .title-input { font: 600 var(--fs-15)/20px var(--font-display); max-width: 520px; }
  .old { color: var(--warn); }
  .tb-sep { width: 1px; height: 18px; background: var(--line-strong); margin: 0 var(--sp-2); }
  .split .btn + .btn, .split .btn + .select { margin-left: 1px; }
  .split .btn:last-child { padding: 0 8px; }
  .export .tpl { width: auto; max-width: 180px; padding-right: 30px; overflow: hidden; text-overflow: ellipsis; text-align: left; background-position: right 7px center;
    background-repeat: no-repeat; }
  .export .tpl.btn-primary { background-color: var(--primary); }
  .export .tpl.btn-primary:hover { background-color: var(--primary-hover); }
  .export .tpl.btn-primary { background-image: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2710%27 height=%276%27 viewBox=%270 0 10 6%27%3E%3Cpath d=%27M1 1l4 4 4-4%27 fill=%27none%27 stroke=%27white%27 stroke-width=%271.5%27 stroke-linecap=%27round%27/%3E%3C/svg%3E"); }
  .export .tpl option { color: var(--text); background: var(--surface); }
  .grow { flex: 1; min-width: 0; }
  .link { border: 0; background: none; padding: 0; font: inherit; color: var(--accent); cursor: pointer; }

  .building { align-items: center; margin-bottom: var(--sp-6); max-width: 760px; margin-inline: auto; }
  .building .bar { background: color-mix(in srgb, var(--accent) 18%, transparent); }
  .narrow-card { max-width: 560px; margin: var(--sp-8) auto 0; }
  .narrow-card .hint { margin-top: calc(-1 * var(--sp-4)); }
  .paper-col { min-width: 0; }
  .banners { margin: 0 0 var(--sp-6); display: flex; flex-direction: column; gap: var(--sp-4); }
  .banners:empty { display: none; }
  .banners .banner :global(.icon) { margin-top: 1px; }
  .hint-line { font-size: var(--fs-12); color: var(--text-3); display: flex; align-items: center; gap: 6px; }

  .doc-layout { display: grid; grid-template-columns: 200px minmax(0, 760px) 280px; gap: var(--sp-8); justify-content: center; align-items: start; }
  .doc-layout:not(.has-notes) { grid-template-columns: 200px minmax(0, 760px) 200px; }
  .toc { position: sticky; top: calc(var(--toolbar) + var(--sp-5)); font-size: 12.5px; max-height: calc(100vh - var(--toolbar) - 32px);
    overflow-y: auto; display: flex; flex-direction: column; gap: 1px; }
  .toc h4, .notes h4 { font-size: var(--fs-11); font-weight: 600; color: var(--text-3); margin: 0 0 var(--sp-4) var(--sp-4); }
  .toc button { display: flex; align-items: center; gap: 6px; border: 0; background: none; text-align: left; padding: 4px var(--sp-4);
    border-radius: var(--r-sm); color: var(--text-2); cursor: pointer; font: inherit; line-height: 17px; }
  .toc button:hover { background: var(--surface-3); color: var(--text); }
  .toc .tn { color: var(--text-3); font-variant-numeric: tabular-nums; }
  .toc .ind { padding-left: 20px; }
  .toc .dot { margin-left: auto; }
  .dot.warn { background: var(--warn); } .dot.danger { background: var(--danger); }
  .ver { margin-top: var(--sp-7); }
  .toc .v { justify-content: space-between; }
  .toc .v.on { color: var(--text); font-weight: 600; background: var(--surface-3); }

  .paper { background: var(--surface); border-radius: var(--r-md); min-width: 0; --pad-l: 88px;
    box-shadow: 0 0 0 1px var(--line-strong), 0 2px 8px rgba(0,0,0,.05), 0 12px 32px -12px rgba(0,0,0,.08);
    padding: 56px 64px 72px var(--pad-l); font-size: var(--fs-15); line-height: 24px; }
  .doc-kicker { font-size: var(--fs-12); line-height: 16px; color: var(--text-3); margin-bottom: var(--sp-4); font-variant-numeric: tabular-nums; }
  .paper h1 { font: 700 var(--fs-26)/32px var(--font-display); letter-spacing: -.015em; margin-bottom: var(--sp-9); }
  .sec h2 { font: 600 var(--fs-17)/24px var(--font-display); letter-spacing: -.005em; margin: var(--sp-10) 0 var(--sp-4); }
  .sec:first-of-type h2 { margin-top: 0; }
  .sub h3 { font: 600 var(--fs-15)/22px var(--font); margin: var(--sp-8) 0 var(--sp-3); }
  .sec, .sub { scroll-margin-top: calc(var(--toolbar) + 16px); }
  .prose { margin: 0 0 var(--sp-5); white-space: pre-line; }
  .muted-i { color: var(--text-3); font-style: italic; margin: 0 0 var(--sp-5); }
  .list-title { font-weight: 600; margin: var(--sp-4) 0 var(--sp-2); }
  .prose-list { margin: 0 0 var(--sp-5); padding-left: 22px; }

  .req { position: relative; display: grid; grid-template-columns: 56px minmax(0, 1fr) auto; gap: var(--sp-4);
    margin: 0 -12px 0 -76px; padding: var(--sp-4) 12px; border-radius: var(--r-md); transition: background var(--t-fast);
    scroll-margin-top: calc(var(--toolbar) + 16px); }
  .req:hover { background: color-mix(in srgb, var(--surface-2) 60%, transparent); }
  .req.stale { background: color-mix(in srgb, var(--warn-bg) 55%, transparent); }
  .rid { font: 600 12px/24px var(--mono); color: var(--accent); text-align: right; white-space: nowrap; }
  .req.nfr .rid { color: var(--nfr); } .req.q .rid { color: var(--q); }
  .txt { min-width: 0; }
  .flagged .body { text-decoration: underline wavy color-mix(in srgb, var(--warn) 70%, transparent); text-decoration-thickness: 1px; text-underline-offset: 5px; }
  .src { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; font-size: var(--fs-12); line-height: 16px; }
  .src-chip { display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; border-radius: var(--r-full); border: 0;
    background: var(--surface-2); color: var(--text-2); font: inherit; cursor: pointer; max-width: 100%; }
  .src-chip:hover { background: var(--accent-bg); color: var(--accent); }
  .flag { margin-top: 6px; display: flex; gap: 6px; flex-wrap: wrap; }
  .flag .tag { max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
  .req .row-actions { align-self: start; }
  .free { margin: var(--sp-5) 0; padding: var(--sp-4) var(--sp-6); border-left: 2px solid var(--line-control); background: var(--surface-2);
    border-radius: 0 var(--r-sm) var(--r-sm) 0; }
  .free .lbl { display: flex; align-items: center; gap: 6px; font-size: var(--fs-11); font-weight: 600; color: var(--text-3); min-height: 24px; }
  .free .row-actions { margin-left: auto; }
  .free-edit { display: flex; flex-direction: column; gap: var(--sp-4); margin: var(--sp-2) 0 var(--sp-5); font-size: var(--fs-13); line-height: 18px; }
  .area { resize: vertical; font-size: var(--fs-14); line-height: 20px; }
  .sec { position: relative; }
  .add-free { position: absolute; top: -2px; right: -40px; color: var(--text-3); opacity: 0; transition: opacity var(--t-fast); }
  .sec:first-of-type > .add-free { top: -2px; }
  .sec:not(:first-of-type) > .add-free { top: calc(var(--sp-10) - 2px); }
  .sec:hover > .add-free, .add-free:focus-visible { opacity: 1; }
  @media (hover: none) { .add-free { opacity: 1; } }

  .notes { position: sticky; top: calc(var(--toolbar) + var(--sp-5)); display: flex; flex-direction: column; gap: var(--sp-4);
    max-height: calc(100vh - var(--toolbar) - 32px); overflow-y: auto; padding: 1px; }
  .notes h4 { display: flex; justify-content: space-between; margin: var(--sp-4) 0 0; }
  .notes h4:first-child { margin-top: 0; }
  .finding { background: var(--surface); border-radius: var(--r-md); box-shadow: var(--e1); padding: var(--sp-5); font-size: 12.5px; line-height: 18px; }
  .finding .fh { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; flex-wrap: wrap; }
  .finding .fh .mono { color: var(--accent); font-weight: 600; }
  .finding p { color: var(--text-2); }
  .finding .acts { display: flex; gap: 6px; margin-top: var(--sp-4); }
  .finding textarea { margin-top: var(--sp-2); font-size: var(--fs-13); line-height: 19px; }
  .prop-lbl { font-size: var(--fs-11); color: var(--text-3) !important; margin-top: var(--sp-4); }
  .change ins, .change del { border-radius: 2px; padding: 0 1px; text-decoration: none; }
  .change ins { background: var(--ins); color: var(--text); }
  .change del { background: var(--del); color: var(--text-2); text-decoration: line-through; }

  @media (max-width: 1360px) {
    .doc-layout, .doc-layout:not(.has-notes) { grid-template-columns: 188px minmax(0, 760px); }
    .notes { position: static; grid-column: 2; grid-row: 1; max-height: none; display: grid; grid-template-columns: 1fr 1fr; }
    .notes h4 { grid-column: 1 / -1; }
  }
  @media (max-width: 1120px) {
    .doc-layout, .doc-layout:not(.has-notes) { grid-template-columns: minmax(0, 1fr); max-width: 760px; margin: 0 auto; }
    .toc { display: none; }
    .notes { grid-column: 1; }
    .paper { padding: 40px 40px 56px; --pad-l: 40px; }
    .add-free { right: -24px; }
    .req { margin: 0 -12px; grid-template-columns: minmax(0, 1fr) auto; }
    .rid { text-align: left; grid-column: 1 / -1; line-height: 16px; }
    .req .row-actions { grid-column: 2; grid-row: 2; }
  }
  @media (max-width: 720px) {
    .notes { grid-template-columns: 1fr; }
    .paper { padding: 24px 20px 40px; }
  }
</style>
