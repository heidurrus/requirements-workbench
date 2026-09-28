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

  // Several documents per project (BRD, SRS, Vision & Scope, risks, As-Is/To-Be…), one tab each.
  let docList = $state(null);            // {documents, types, requirements_document}
  let addMenu = $state(false);
  const docId = $derived(app.route.doc || docList?.documents?.[0]?.id || null);
  async function loadDocs() {
    try { docList = await api(`/api/projects/${app.currentProjectId}/documents`); } catch (err) { error = err.message; }
  }
  $effect(() => { app.currentProjectId; app.atomsVersion; app.lang; loadDocs(); });
  async function createDoc(kind) {
    addMenu = false;
    try {
      const d = await api(`/api/projects/${app.currentProjectId}/documents`, { method: "POST", body: { kind } });
      await loadDocs();
      go(`/document/${d.id}`);
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  // Opened from a skill: "create a document of this type"
  let createdFor = null;
  $effect(() => {
    const kind = app.route.newKind;
    if (kind && docList && createdFor !== kind) { createdFor = kind; createDoc(kind); }
  });
  async function deleteDoc() {
    exportMenu = false;
    if (!confirm(t("doc.delete_q", { title: doc.title }))) return;
    try {
      await api(`/api/documents/${doc.id}`, { method: "DELETE" });
      await loadDocs();
      go("/document");
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function changeType(kind) {
    exportMenu = false;
    if (kind === doc.kind) return;
    try {
      await api(`/api/documents/${doc.id}`, { method: "PATCH", body: { kind } });
      await loadDocs();
      await load();
      toast(t("doc.type_changed"));
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  const hasRequirements = $derived(docList?.types?.find(x => x.name === body?.document?.kind)?.requirements !== false);

  async function load() {
    const pid = app.currentProjectId;
    if (!docId) return;
    try {
      const q = `?document=${docId}` + (viewing ? `&version=${viewing}` : "");
      const b = await api(`/api/projects/${pid}/document${q}`);
      if (pid !== app.currentProjectId) return;
      body = b;
      error = "";
      if (b.building && !build) follow(b.building);
    } catch (err) { error = err.message; }
  }
  $effect(() => { app.currentProjectId; app.atomsVersion; app.lang; docId; viewing; load(); });
  $effect(() => { docId; viewing = null; diff = null; });

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

  async function runBuild(mode, note = null) {
    confirmFull = false;
    refineOpen = false;
    try {
      const { job_id } = await api(`/api/projects/${app.currentProjectId}/document/build`, { method: "POST",
                                                                                          body: { mode, document_id: doc?.id || docId, ...(note ? { note } : {}) } });
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

  // PM-12: a full rewrite is one click away from approved prose — ask first, and say what's kept.
  let confirmFull = $state(false);
  // PM-32: a one-off instruction for this build
  let refineOpen = $state(false);
  let refineNote = $state("");
  let exportMenu = $state(false);
  let reviewInput = $state(null);

  function exportMarkdown() {
    exportMenu = false;
    saveUrl(`/api/documents/${doc.id}/export.md?version=${version.number}`, `${doc.title} v${version.number}.md`.replace(/[\\/:*?"<>|]/g, ""));
  }
  function exportTrace() {
    exportMenu = false;
    saveUrl(`/api/projects/${app.currentProjectId}/traceability.xlsx?lang=${app.lang}`, `${doc.title} — traceability.xlsx`.replace(/[\\/:*?"<>|]/g, ""));
  }
  async function importReview(e) {
    exportMenu = false;
    const f = e.currentTarget.files[0];
    e.currentTarget.value = "";
    if (!f) return;
    const form = new FormData();
    form.append("file", f);
    try {
      const r = await api(`/api/documents/${doc.id}/review`, { method: "POST", form });
      toast(t("doc.review_imported", { n: r.comments, linked: r.linked }), { action: t("doc.review_open"),
                                                                             onAction: () => go(`/source/${r.source_id}`) });
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  // Sign-off and change requests (PM-34)
  const baseline = $derived(body?.versions?.filter(v => v.status === "approved").map(v => v.number).sort((a, b) => b - a)[0] || null);
  let changes = $state(null);
  $effect(() => {
    if (doc && baseline && latest > baseline) {
      api(`/api/documents/${doc.id}/changes`).then(r => (changes = r)).catch(() => (changes = null));
    } else changes = null;
  });
  let showChanges = $state(false);
  async function setStatus(status) {
    try {
      const r = await api(`/api/documents/${doc.id}/versions/${version.number}/status`, { method: "POST", body: { status } });
      body.versions = r.versions;
      toast(t("doc.st_set", { v: version.number, s: t("doc.st." + status) }));
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  // Jira keys on requirements (PM-11)
  let jiraByReq = $state({});
  $effect(() => {
    app.currentProjectId; body;
    api(`/api/projects/${app.currentProjectId}/backlog`).then(b => {
      const m = {};
      for (const i of b.items) if (i.jira_key) for (const r of i.refs || []) (m[r.id] ||= []).push({ key: i.jira_key, url: i.jira_url });
      jiraByReq = m;
    }).catch(() => {});
  });

  // PM-27: fix every finding, accept the proposals, update once — one version, not one per finding.
  let fixingAll = $state(null);
  async function fixAll() {
    const list = findings.filter(f => !fixes[fixKey(f)]);
    fixingAll = { done: 0, total: list.length };
    let applied = 0;
    for (const f of list) {
      try {
        const { job_id } = await api(`/api/documents/${doc.id}/fix`, { method: "POST",
          body: { atom_id: f.block.atom_id, rule: f.rule, message: f.message } });
        const job = await pollJob(job_id, null, { interval: 700 });
        await api(`/api/atoms/${f.block.atom_id}`, { method: "PATCH", body: { statement: job.result.statement } });
        applied++;
      } catch (_) { /* skip this one, keep going */ }
      fixingAll = { done: fixingAll.done + 1, total: list.length };
    }
    fixingAll = null;
    app.atomsVersion++;
    if (applied) { toast(t("doc.fixed_all", { n: applied })); runBuild("changed"); }
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
  // probability rows (high → low) × impact columns (low → high)
  const heatClass = (i, j) => { const score = (2 - i) + (j - 1); return score >= 3 ? "h-high" : score >= 2 ? "h-mid" : "h-low"; };
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
          <button class="btn btn-ghost" onclick={() => (refineOpen = !refineOpen)} title={t("ai.refine_hint")}>{t("ai.refine")}</button>
          {#if body.stale?.stale}
            <div class="split">
              <button class="btn btn-primary" disabled={!!build} onclick={() => runBuild("changed")}>
                <Icon name="refresh" size={14} /> {t("doc.rebuild_n", { n: body.stale.changed + body.stale.removed + body.stale.added })}</button>
              <button class="btn" disabled={!!build} onclick={() => (confirmFull = true)} title={t("doc.full_hint")}>{t("doc.full")}</button>
            </div>
          {:else}
            <button class="btn btn-ghost" disabled={!!build} onclick={() => (confirmFull = true)} title={t("doc.full_hint")}>
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
          <div class="menu-wrap">
            <button class="btn icon-btn" aria-label={t("doc.more_export")} title={t("doc.more_export")} aria-expanded={exportMenu}
                    onclick={() => (exportMenu = !exportMenu)}><Icon name="more" /></button>
            {#if exportMenu}
              <div class="menu" role="menu">
                <button role="menuitem" onclick={exportMarkdown}><Icon name="file" size={14} /> {t("doc.export_md")}</button>
                <button role="menuitem" onclick={exportTrace}><Icon name="tree" size={14} /> {t("doc.export_trace")}</button>
                <button role="menuitem" onclick={() => reviewInput.click()}><Icon name="upload" size={14} /> {t("doc.import_review")}</button>
                {#if docList}
                  <p class="menu-h">{t("doc.change_type")}</p>
                  {#each docList.types as ty (ty.name)}
                    <button role="menuitem" class:on={ty.name === doc.kind} onclick={() => changeType(ty.name)}>
                      <Icon name={ty.name === doc.kind ? "check" : "doc"} size={14} /> {ty.title}</button>
                  {/each}
                {/if}
                {#if docList && docList.documents[0]?.id !== doc.id}
                  <button role="menuitem" class="danger-item" onclick={deleteDoc}><Icon name="trash" size={14} /> {t("doc.delete")}</button>
                {/if}
              </div>
            {/if}
            <input type="file" accept=".docx" class="hidden" bind:this={reviewInput} onchange={importReview} aria-label={t("doc.import_review")} />
          </div>
          {#if hasRequirements}<button class="btn btn-ghost" onclick={() => go("/backlog")}>{t("doc.to_backlog")} <Icon name="arrow" size={14} /></button>{/if}
        {/if}
      </div>
    {/if}
  </header>

  {#if docList}
    <div class="doc-tabs" role="tablist" aria-label={t("nav.document")}>
      {#each docList.documents as d (d.id)}
        <button role="tab" aria-selected={d.id === docId} onclick={() => go(`/document/${d.id}`)} title={d.title}>
          <b>{d.short}</b>{#if d.version}<span class="n">v{d.version}</span>{/if}
          {#if d.stale}<span class="dot warn" title={t("nav.badge_stale")}></span>{/if}
          {#if d.status === "approved"}<Icon name="check" size={12} />{/if}
        </button>
      {/each}
      <div class="add-wrap">
        <button class="btn btn-ghost btn-sm" onclick={() => (addMenu = !addMenu)} aria-expanded={addMenu}><Icon name="plus" size={14} /> {t("doc.add")}</button>
        {#if addMenu}
          <div class="menu types" role="menu">
            {#each docList.types as ty (ty.name)}
              <button role="menuitem" onclick={() => createDoc(ty.name)}>
                <b>{ty.title}</b><span class="t3">{ty.description}</span></button>
            {/each}
            <button role="menuitem" class="custom" onclick={() => { addMenu = false; go("/skills"); }}>
              <span class="t3">{t("doc.add_custom")}</span></button>
          </div>
        {/if}
      </div>
    </div>
  {/if}

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
      {#if refineOpen}
        <div class="card refine">
          <!-- svelte-ignore a11y_autofocus -->
          <textarea class="input" rows="2" bind:value={refineNote} autofocus placeholder={t("ai.refine_ph.doc")} aria-label={t("ai.refine")}></textarea>
          <div class="actions"><span class="hint">{t("ai.refine_hint")}</span><span class="spacer"></span>
            <button class="btn btn-sm btn-ghost" onclick={() => (refineOpen = false)}>{t("at.cancel")}</button>
            <button class="btn btn-sm" disabled={!refineNote.trim() || !!build} onclick={() => runBuild("changed", refineNote)}>{t("doc.rebuild")}</button>
            <button class="btn btn-sm btn-primary" disabled={!refineNote.trim() || !!build} onclick={() => runBuild("full", refineNote)}>{t("doc.full_short")}</button>
          </div>
        </div>
      {/if}
      <div class="version-bar">
        <span class="t3">v{version.number}</span>
        <div class="seg" role="group" aria-label={t("doc.st.label")}>
          {#each ["draft", "review", "approved"] as st (st)}
            <button aria-pressed={(version.status || "draft") === st} disabled={!isLatest && st !== "approved" && false}
                    onclick={() => setStatus(st)}>{t("doc.st." + st)}</button>
          {/each}
        </div>
        {#if baseline && baseline !== version.number}<span class="t3">{t("doc.baseline", { v: baseline })}</span>{/if}
        {#if changes && changes.changes.length}
          <button class="btn btn-sm" onclick={() => (showChanges = !showChanges)}>
            <Icon name="compare" size={12} /> {t("doc.cr_n", { n: changes.changes.length, v: baseline })}</button>
        {/if}
      </div>
      {#if showChanges && changes}
        <div class="card cr">
          <p class="cr-h">{t("doc.cr_title", { a: changes.baseline, b: changes.to })}</p>
          {#each changes.changes as c (c.id + c.change)}
            <div class="cr-row">
              <span class="mono">{c.id}</span>
              <span class="tag {c.change === 'added' ? 'ok' : c.change === 'removed' ? 'danger' : 'warn'}">{t("doc.change." + c.change)}</span>
              <span class="grow">{c.new || c.old}</span>
              {#if c.impact.length}
                <span class="impact">{t("doc.cr_impact")}: {#each c.impact as im, i (i)}{#if im.key}<a href={im.url} target="_blank" rel="noreferrer" class="mono">{im.key}</a>{:else}{im.title}{/if}{i < c.impact.length - 1 ? ", " : ""}{/each}</span>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
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
          <p class="doc-kicker">{doc.short} · {t("doc.sub", { v: version.number, n: version.atom_count, when: ago(version.created_at) })}{#if version.model} · {version.model}{/if}</p>
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
              {#if findings.length > 1}
                <button class="btn btn-sm fix-all" disabled={!!fixingAll || !!build} onclick={fixAll}>
                  {#if fixingAll}<span class="spinner"></span> {fixingAll.done}/{fixingAll.total}{:else}<Icon name="bolt" size={12} /> {t("doc.fix_all", { n: findings.length })}{/if}</button>
              {/if}
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

{#if confirmFull}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="scrim" onclick={e => e.target === e.currentTarget && (confirmFull = false)} onkeydown={e => e.key === "Escape" && (confirmFull = false)}>
    <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="full-h">
      <h2 id="full-h">{t("doc.full_q")}</h2>
      <p class="t2">{t("doc.full_body")}</p>
      <dl class="facts">
        <dt>{t("doc.full_kept")}</dt><dd>{t("doc.full_kept_v")}</dd>
        <dt>{t("doc.full_new")}</dt><dd>{t("doc.full_new_v")}</dd>
      </dl>
      <div class="acts">
        <!-- svelte-ignore a11y_autofocus -->
        <button class="btn" autofocus onclick={() => (confirmFull = false)}>{t("at.cancel")}</button>
        <button class="btn btn-primary" onclick={() => runBuild("full")}>{t("doc.full_yes")}</button>
      </div>
    </div>
  </div>
{/if}

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
          {#if jiraByReq[b.id]}
            <p class="src">{#each jiraByReq[b.id] as j (j.key)}<a class="src-chip jira" href={j.url} target="_blank" rel="noreferrer"><Icon name="link" size={12} /> {j.key}</a>{/each}</p>
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
    {:else if b.kind === "table"}
      {#if b.title}<p class="list-title">{b.title}</p>{/if}
      <div class="doc-table-wrap" class:heat={b.heatmap}>
        <table class="doc-table">
          <thead><tr>{#each b.columns as c, i (i)}<th>{c}</th>{/each}</tr></thead>
          <tbody>
            {#each b.rows as r, i (i)}
              <tr>{#each r as v, j (j)}<td class={b.heatmap && j > 0 ? heatClass(i, j) : ""}>{v}</td>{/each}</tr>
            {/each}
          </tbody>
        </table>
      </div>
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
  .doc-tabs { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; border-bottom: 1px solid var(--line);
    margin: calc(-1 * var(--sp-2)) 0 var(--sp-6); }
  .doc-tabs [role="tab"] { border: 0; background: transparent; padding: 8px 10px; color: var(--text-2); border-bottom: 2px solid transparent;
    margin-bottom: -1px; display: inline-flex; gap: 6px; align-items: center; cursor: pointer; font: inherit; }
  .doc-tabs [role="tab"] b { font-weight: 500; }
  .doc-tabs [role="tab"]:hover { color: var(--text); }
  .doc-tabs [role="tab"][aria-selected="true"] { color: var(--text); border-bottom-color: var(--accent); }
  .doc-tabs [role="tab"][aria-selected="true"] b { font-weight: 600; }
  .doc-tabs .n { color: var(--text-3); font-size: var(--fs-12); }
  .doc-tabs .dot.warn { background: var(--warn); }
  .add-wrap { position: relative; margin-left: var(--sp-2); }
  .menu.types { left: 0; right: auto; width: min(420px, 90vw); max-height: 70vh; overflow: auto; }
  .menu.types button { flex-direction: column; align-items: flex-start; gap: 2px; }
  .menu.types button span { font-size: var(--fs-12); line-height: 16px; }
  .menu-h { font-size: var(--fs-11); font-weight: 600; color: var(--text-3); padding: var(--sp-4) var(--sp-4) var(--sp-2);
    border-top: 1px solid var(--line); margin-top: var(--sp-2); }
  .menu button.on { font-weight: 600; }
  .menu .danger-item { color: var(--danger); border-top: 1px solid var(--line); border-radius: 0; margin-top: var(--sp-2); }
  .doc-table-wrap { overflow-x: auto; margin: var(--sp-4) 0 var(--sp-6); }
  .doc-table { width: 100%; border-collapse: collapse; font-size: var(--fs-13); line-height: 18px; }
  .doc-table th { text-align: left; font-weight: 600; font-size: var(--fs-12); color: var(--text-2); background: var(--surface-2);
    padding: 6px 8px; border: 1px solid var(--line); vertical-align: bottom; }
  .doc-table td { padding: 6px 8px; border: 1px solid var(--line); vertical-align: top; }
  .doc-table td:first-child { white-space: nowrap; }
  .heat .doc-table { width: auto; }
  .heat .doc-table td { min-width: 110px; text-align: center; font-weight: 600; }
  .heat .doc-table td:first-child { text-align: left; font-weight: 500; background: var(--surface-2); }
  .h-high { background: var(--danger-bg); color: var(--danger); }
  .h-mid { background: var(--warn-bg); color: var(--warn); }
  .h-low { background: var(--ok-bg); color: var(--ok); }
  .refine { padding: var(--sp-5); margin-bottom: var(--sp-5); display: flex; flex-direction: column; gap: var(--sp-4); }
  .refine textarea { height: auto; }
  .spacer { flex: 1; }
  .version-bar { display: flex; align-items: center; gap: var(--sp-4); flex-wrap: wrap; margin-bottom: var(--sp-5); font-size: var(--fs-12); }
  .cr { padding: var(--sp-5) var(--sp-6); margin-bottom: var(--sp-5); font-size: var(--fs-13); }
  .cr-h { font-weight: 600; margin-bottom: var(--sp-4); }
  .cr-row { display: flex; gap: var(--sp-4); align-items: baseline; padding: var(--sp-3) 0; border-top: 1px solid var(--line); flex-wrap: wrap; }
  .cr-row .grow { flex: 1; min-width: 200px; }
  .impact { font-size: var(--fs-12); color: var(--text-3); }
  .impact a { color: var(--accent); }
  .menu-wrap { position: relative; }
  .menu { position: absolute; right: 0; top: calc(100% + 4px); z-index: 30; background: var(--surface); border-radius: var(--r-md);
    box-shadow: var(--e2); padding: var(--sp-2); min-width: 240px; }
  .menu button { display: flex; align-items: center; gap: var(--sp-4); width: 100%; border: 0; background: none; text-align: left;
    padding: var(--sp-3) var(--sp-4); border-radius: var(--r-sm); cursor: pointer; font: inherit; color: var(--text); }
  .menu button:hover { background: var(--surface-2); }
  .src-chip.jira { background: var(--accent-bg); color: var(--accent); text-decoration: none; }
  .fix-all { align-self: flex-start; }
  .banners { margin: 0 0 var(--sp-6); display: flex; flex-direction: column; gap: var(--sp-4); }
  .banners:empty { display: none; }
  /* several warnings read as one strip, not a stack (PM review 2.4) */
  .banners:has(.banner + .banner) { gap: 0; }
  .banners:has(.banner + .banner) .banner { border-radius: 0; }
  .banners:has(.banner + .banner) .banner:first-child { border-radius: var(--r-md) var(--r-md) 0 0; }
  .banners:has(.banner + .banner) .banner:last-of-type { border-radius: 0 0 var(--r-md) var(--r-md); }
  .banners .banner + .banner { box-shadow: inset 0 1px 0 color-mix(in srgb, currentColor 18%, transparent); }
  .banners .banner :global(.icon) { margin-top: 1px; }
  .hint-line { font-size: var(--fs-12); color: var(--text-3); display: flex; align-items: center; gap: 6px; }

  .doc-layout { display: grid; grid-template-columns: 220px minmax(0, 820px) minmax(260px, 340px); gap: var(--sp-9); justify-content: center; align-items: start; }
  .doc-layout:not(.has-notes) { grid-template-columns: 220px minmax(0, 860px) 220px; justify-content: center; }
  @media (min-width: 1800px) { .doc-layout { grid-template-columns: 240px minmax(0, 880px) minmax(300px, 380px); } }
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
    .toc { grid-row: 1 / span 2; }
    .paper-col { grid-column: 2; }
    .notes h4 { grid-column: 1 / -1; }
  }
  @media (max-width: 1120px) {
    .doc-layout, .doc-layout:not(.has-notes) { grid-template-columns: minmax(0, 1fr); max-width: 760px; margin: 0 auto; }
    .toc { display: none; }
    .notes { grid-column: 1; }
    .paper-col { grid-column: 1; }
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
