<script>
  import { untrack } from "svelte";
  import Block from "../components/Block.svelte";
  import Icon from "../components/Icon.svelte";
  import { explain } from "../lib/errors.js";
  import { api, pollJob } from "../lib/api.js";
  import { fmtDate, renderMarkdown } from "../lib/format.js";
  import { saveUrl } from "../lib/save.js";
  import { app, t, go, toast, currentProject } from "../lib/state.svelte.js";

  let list = $state(null);               // {stages, skills, project_id}
  let skill = $state(null);              // full skill as loaded
  let draft = $state(null);              // editable copy
  let error = $state("");
  let saving = $state(false);
  let historyText = $state(null);        // {id, text}
  let tryState = $state(null);           // {running, progress, message, result, partial}
  let trySource = $state("");
  let importInput = $state(null);
  let templateInput = $state(null);

  const selected = $derived(app.route.skill || null);
  const clone = o => JSON.parse(JSON.stringify(o));     // reactive state can't go through structuredClone
  // The desktop bridge can arrive slightly after the page loads.
  let desktop = $state(!!window.pywebview);
  $effect(() => {
    const ready = () => (desktop = true);
    window.addEventListener("pywebviewready", ready);
    return () => window.removeEventListener("pywebviewready", ready);
  });

  async function loadList() {
    try { list = await api(`/api/skills?project_id=${app.currentProjectId}`); }
    catch (err) { error = err.message; }
  }
  async function loadSkill(name) {
    if (!name) { skill = draft = null; return; }
    try {
      skill = await api(`/api/skills/${name}`);
      draft = clone({ title: skill.title, description: skill.description, instructions: skill.instructions,
                                meta: skill.meta });
      historyText = null;
      tryState = null;
    } catch (err) { skill = draft = null; toast(err.message, { kind: "danger" }); }
  }
  $effect(() => { app.currentProjectId; loadList(); });
  $effect(() => { loadSkill(selected); });

  const dirty = $derived(!!(skill && draft) && JSON.stringify(draft) !== JSON.stringify(
    { title: skill.title, description: skill.description, instructions: skill.instructions, meta: skill.meta }));
  const editable = $derived(!!skill && !skill.builtin && !skill.error);
  const stageInfo = $derived(list && skill ? list.stages.find(s => s.id === skill.stage) : null);
  const grouped = $derived(list ? list.stages.map(st => ({ ...st, skills: list.skills.filter(s => s.stage === st.id) }))
    .concat([{ id: "broken", skills: list.skills.filter(s => s.error) }]).filter(g => g.skills.length) : []);
  const readySources = $derived(app.sources.filter(s => s.status === "ready"));

  function open(name) {
    if (dirty && !confirm(t("sk.leave"))) return;
    go(`/skills/${name}`);
  }
  // Warn before leaving the app screen with unsaved edits.
  $effect(() => {
    const handler = e => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  });

  async function save() {
    if (!editable || !dirty) return;
    saving = true;
    try {
      const updated = await api(`/api/skills/${skill.name}`, { method: "PUT", body: draft });
      skill = updated;
      draft = clone({ title: updated.title, description: updated.description,
                                instructions: updated.instructions, meta: updated.meta });
      toast(t("sk.saved", { v: updated.version }));
      loadList();
    } catch (err) { toast(err.message, { kind: "danger", ms: 12000 }); }
    finally { saving = false; }
  }
  function onKey(e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s" && app.route.name === "skills") { e.preventDefault(); save(); }
  }

  async function copy() {
    try {
      const c = await api("/api/skills", { method: "POST", body: { from: skill.name } });
      await loadList();
      toast(t("sk.copied"));
      go(`/skills/${c.name}`);
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function remove() {
    const name = skill.name, title = skill.title;
    if (!confirm(`${t("sk.delete")}: ${title}?`)) return;
    try {
      await api(`/api/skills/${name}`, { method: "DELETE" });
      await loadList();
      go("/skills");
      toast(t("sk.deleted", { name: title }), { action: t("at.undo"), onAction: async () => {
        await api(`/api/skills/${name}/undelete`, { method: "POST" });
        await loadList();
        go(`/skills/${name}`);
      } });
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function reveal(what) {
    try {
      await api(`/api/skills/${skill.name}/open`, { method: "POST", body: { what } });
      if (what === "template") toast(t("sk.template_opened"), { ms: 9000 });
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function useGlobally() {
    try { list = await api("/api/skills/active", { method: "PUT", body: { stage: skill.stage, skill: skill.name } }); }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function useForProject(on) {
    try {
      list = await api("/api/skills/active", { method: "PUT",
        body: { stage: skill.stage, skill: on ? skill.name : null, project_id: app.currentProjectId } });
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function importFile(e) {
    const f = e.currentTarget.files[0];
    e.currentTarget.value = "";
    if (!f) return;
    const form = new FormData();
    form.append("file", f);
    try {
      const s = await api("/api/skills/import", { method: "POST", form });
      await loadList();
      toast(t("sk.imported", { name: s.title }));
      go(`/skills/${s.name}`);
    } catch (err) { toast(err.message, { kind: "danger", ms: 12000 }); }
  }
  async function uploadTemplate(e) {
    const f = e.currentTarget.files[0];
    e.currentTarget.value = "";
    if (!f) return;
    const form = new FormData();
    form.append("file", f);
    try { skill = await api(`/api/skills/${skill.name}/template`, { method: "POST", form }); toast(t("sk.template_uploaded")); }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function showHistory(h) {
    if (h.kind !== "text") return;
    try { historyText = { id: h.id, ...(await api(`/api/skills/${skill.name}/history/${h.id}`)) }; }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function restore(h) {
    if (dirty && !confirm(t("sk.leave"))) return;
    try {
      await api(`/api/skills/${skill.name}/history/${h.id}/restore`, { method: "POST" });
      await loadSkill(skill.name);
      toast(t("sk.restored"));
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  // ── try it ────────────────────────────────────────────────────────────────
  const tryMode = $derived(!skill ? null : ["summary", "global", "extract"].includes(skill.stage) ? "source"
    : ["frd", "quality"].includes(skill.stage) ? "project" : skill.stage === "export" ? "export" : null);
  $effect(() => { if (!trySource && readySources.length) trySource = readySources[0].id; });

  async function runTry() {
    tryState = { running: true, progress: 0, message: "", partial: "" };
    try {
      const { job_id } = await api("/api/skills/try", { method: "POST", body: {
        name: skill.name, ...draft, source_id: tryMode === "source" ? trySource : null, project_id: app.currentProjectId } });
      const job = await pollJob(job_id, j => { tryState = { running: true, progress: j.progress || 0,
        message: j.progress_msg || "", partial: j.partial || "" }; });
      tryState = { running: false, result: job.result };
    } catch (err) {
      tryState = null;
      const e = explain(err);
      toast(e.message, { kind: "danger", ...(e.setup ? { action: t("err.open_settings"), onAction: () => go("/settings") } : {}) });
    }
  }
  async function exportSample() {
    try {
      const body = await api(`/api/projects/${app.currentProjectId}/document`);
      if (!body.version) { toast(t("sk.try_no_doc")); return; }
      saveUrl(`/api/documents/${body.document.id}/export.docx?template=${skill.name}`, `${body.document.title} (${skill.title}).docx`);
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  // ── stage editors ─────────────────────────────────────────────────────────
  const REQUIRED = ["functional", "nfr", "questions"];
  const KINDS = ["purpose", "context", "functional", "nfr", "out_of_scope", "questions"];
  const titleOf = (title, lang) => (typeof title === "object" && title) ? (title[lang] ?? "") : (lang === "ru" ? title ?? "" : "");
  function setTitle(sec, lang, value) {
    const cur = typeof sec.title === "object" && sec.title ? sec.title : { ru: sec.title || "" };
    sec.title = { ...cur, [lang]: value };
  }
  function move(i, d) {
    const s = draft.meta.sections;
    const j = i + d;
    if (j < 0 || j >= s.length) return;
    [s[i], s[j]] = [s[j], s[i]];
  }
  function addSection() {
    const keys = new Set(draft.meta.sections.map(s => s.key));
    let n = 1;
    while (keys.has(`section_${n}`)) n++;
    draft.meta.sections.push({ key: `section_${n}`, title: { ru: "", en: "" }, instructions: "" });
  }
  const words = lang => (draft.meta.vague_words?.[lang] || []).join(", ");
  function setWords(lang, text) {
    draft.meta.vague_words = { ...(draft.meta.vague_words || {}),
      [lang]: text.split(",").map(w => w.trim()).filter(Boolean) };
  }
  function addRule() {
    draft.meta.rules = [...(draft.meta.rules || []), { id: `rule_${(draft.meta.rules || []).length + 1}`, title: "", description: "" }];
  }
  const typeClass = { functional: "fr", nfr: "nfr", question: "q" };

  // Editor tabs: what a stage has decides which appear.
  const tabs = $derived(!skill ? [] : [
    ...(skill.stage !== "export" ? ["instructions"] : []),
    ...(skill.stage === "frd" ? ["sections"] : []),
    ...(skill.stage === "quality" ? ["rules"] : []),
    ...(skill.stage === "export" ? ["template"] : []),
    ...(tryMode && !skill.error ? ["try"] : []),
    "contract",
    ...(editable ? ["history"] : []),
  ]);
  let tab = $state("instructions");
  $effect(() => { skill?.name; untrack(() => { tab = tabs[0] || "instructions"; }); });
  function tabKey(e) {
    const i = tabs.indexOf(tab);
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      tab = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      requestAnimationFrame(() => document.getElementById("sk-tab-" + tab)?.focus());
    }
  }
</script>

<svelte:window onkeydown={onKey} />

<div class="screen-inner wide">
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("sk.title")}</h1>
      <p class="screen-sub">{t("sk.sub")}</p>
    </div>
    <div class="actions">
      <input type="file" accept=".zip,.md" class="hidden" bind:this={importInput} onchange={importFile} aria-label={t("sk.import")} />
      <button class="btn" title={t("sk.import_hint")} onclick={() => importInput.click()}><Icon name="upload" size={14} /> {t("sk.import")}</button>
    </div>
  </header>

  {#if error}<p class="note danger">{error}</p>{/if}

  {#if list}
    <div class="layout">
      <nav class="list" aria-label={t("sk.title")}>
        {#each grouped as g (g.id)}
          <p class="g-title">{g.id === "broken" ? t("sk.broken") : t("sk.stage." + g.id)}</p>
          {#each g.skills as s (s.name + g.id)}
            {#if g.id === "broken" || !s.error}
              <button class="item" class:on={s.name === selected} class:err={!!s.error} onclick={() => open(s.name)}
                      aria-current={s.name === selected ? "true" : undefined}>
                <span class="dot" class:off={!(g.id !== "broken" && g.effective === s.name)}></span>
                <span class="i-title">{s.title}</span>
                <span class="own">{s.builtin ? t("sk.builtin") : t("sk.custom")}</span>
                {#if g.id !== "broken" && g.effective === s.name}<span class="in-use">{t("sk.in_use")}</span>{/if}
              </button>
            {/if}
          {/each}
        {/each}
      </nav>

      <section class="editor">
        {#if !skill || !draft}
          <div class="card empty"><div class="glyph"><Icon name="skills" /></div><p>{t("sk.pick")}</p></div>
        {:else}
          {#key skill.name}
          <div class="card sk-card">
            <div class="head">
              <div class="e-title">
                {#if editable}
                  <input class="input title-input" bind:value={draft.title} aria-label={t("sk.name")} />
                {:else}
                  <h2>{skill.title}</h2>
                {/if}
                <p class="meta"><span class="mono">{skill.name}</span> · {t("sk.stage." + skill.stage)} · v{skill.version}
                  · <span class="tag outline">{skill.builtin ? t("sk.builtin") : t("sk.custom")}</span></p>
                {#if editable}
                  <input class="input desc-input" id="sk-desc" bind:value={draft.description} placeholder={t("sk.description")} aria-label={t("sk.description")} />
                {:else if skill.description}
                  <p class="t2 desc">{skill.description}</p>
                {/if}
              </div>
              <div class="actions">
                <button class="btn" onclick={copy}><Icon name="copy" size={14} /> {t("sk.copy")}</button>
                <button class="btn btn-ghost icon-btn" aria-label={t("sk.export_zip")} title={t("sk.export_zip")}
                        onclick={() => saveUrl(`/api/skills/${skill.name}/export.zip`, `${skill.name}.zip`)}><Icon name="download" size={14} /></button>
                {#if editable && desktop}<button class="btn btn-ghost" onclick={() => reveal("folder")}>{t("sk.folder")}</button>{/if}
                {#if editable}<button class="btn btn-ghost icon-btn danger-text" aria-label={t("sk.delete")} title={t("sk.delete")} onclick={remove}><Icon name="trash" size={14} /></button>{/if}
              </div>
            </div>

            {#if skill.error}<p class="note danger pad">{t("sk.error", { error: skill.error })}</p>{/if}
            {#if !editable && !skill.error}<p class="banner info pad"><Icon name="lock" size={14} /><span>{t("sk.readonly")}</span></p>{/if}

            <div class="tabs" role="tablist" aria-label={skill.title}>
              {#each tabs as k (k)}
                <button role="tab" id="sk-tab-{k}" aria-selected={tab === k} tabindex={tab === k ? 0 : -1}
                        aria-controls="sk-pane" onclick={() => (tab = k)} onkeydown={tabKey}>
                  {t("sk.tab." + k)}
                  {#if k === "sections" && draft.meta.sections}<span class="n">{draft.meta.sections.length}</span>{/if}
                  {#if k === "history"}<span class="n">{skill.history.length}</span>{/if}
                </button>
              {/each}
            </div>

            <div class="pane" id="sk-pane" role="tabpanel" aria-labelledby="sk-tab-{tab}">
              {#if tab === "instructions"}
                <p class="hint pane-hint">{t("sk.hint." + skill.stage)}</p>
                <div class="field">
                  <label class="field-l" for="sk-instr"><span>{t("sk.instructions")}</span>
                    {#if ["frd", "fix", "global", "quality"].includes(skill.stage)}<span class="t3 vars">{t("sk.vars")}</span>{/if}</label>
                  <textarea id="sk-instr" class="input code-area" rows="18" readonly={!editable}
                            bind:value={draft.instructions} spellcheck="false"></textarea>
                </div>
              {:else if tab === "sections"}
                <p class="hint pane-hint">{t("sk.sections_hint")}</p>
                <ol class="sections">
                  {#each draft.meta.sections as sec, i (i + sec.key)}
                    <li class="sec-row">
                      <div class="sec-head">
                        <span class="mono t3">{i + 1}. {sec.key}</span>
                        {#if REQUIRED.includes(sec.key)}<span class="tag outline">{t("sk.sec.required")}</span>{/if}
                        <span class="spacer"></span>
                        {#if editable}
                          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.up")} title={t("sk.sec.up")} disabled={i === 0} onclick={() => move(i, -1)}><Icon name="up" size={14} /></button>
                          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.down")} title={t("sk.sec.down")} disabled={i === draft.meta.sections.length - 1} onclick={() => move(i, 1)}><Icon name="down" size={14} /></button>
                          {#if !REQUIRED.includes(sec.key)}
                            <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.remove")} title={t("sk.sec.remove")}
                                    onclick={() => draft.meta.sections.splice(i, 1)}><Icon name="close" size={14} /></button>
                          {/if}
                        {/if}
                      </div>
                      <div class="sec-fields">
                        <input class="input" placeholder={t("sk.sec.title_ru")} aria-label={t("sk.sec.title_ru")} readonly={!editable}
                               value={titleOf(sec.title, "ru")} oninput={e => setTitle(sec, "ru", e.currentTarget.value)} />
                        <input class="input" placeholder={t("sk.sec.title_en")} aria-label={t("sk.sec.title_en")} readonly={!editable}
                               value={titleOf(sec.title, "en")} oninput={e => setTitle(sec, "en", e.currentTarget.value)} />
                      </div>
                      {#if !KINDS.includes(sec.key)}
                        <textarea class="input area" rows="2" placeholder={t("sk.sec.instructions")} aria-label={t("sk.sec.instructions")}
                                  readonly={!editable} bind:value={sec.instructions}></textarea>
                      {/if}
                    </li>
                  {/each}
                </ol>
                {#if editable}
                  <button class="btn btn-sm" onclick={addSection}><Icon name="plus" size={14} /> {t("sk.sec.add")}</button>
                {/if}
              {:else if tab === "rules"}
                <p class="field-l">{t("sk.vague")}</p>
                <p class="hint pane-hint">{t("sk.vague_hint")}</p>
                <div class="grid-2 vague">
                  {#each ["ru", "en"] as lang (lang)}
                    <div class="field">
                      <label class="label" for="sk-vague-{lang}">{lang === "ru" ? "Русский" : "English"}</label>
                      <textarea class="input area" id="sk-vague-{lang}" rows="3" readonly={!editable} value={words(lang)}
                                onchange={e => setWords(lang, e.currentTarget.value)}></textarea>
                    </div>
                  {/each}
                </div>
                <p class="field-l rules-t">{t("sk.rules")} <span class="t3 num">{(draft.meta.rules || []).length}</span></p>
                <ul class="rules">
                  {#each draft.meta.rules || [] as rule, i (i)}
                    <li class="rule">
                      <div class="sec-fields">
                        <input class="input code" placeholder={t("sk.rule.id")} aria-label={t("sk.rule.id")} readonly={!editable} bind:value={rule.id} />
                        <input class="input" placeholder={t("sk.rule.title")} aria-label={t("sk.rule.title")} readonly={!editable} bind:value={rule.title} />
                        {#if editable}<button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")} title={t("sources.delete")}
                                onclick={() => draft.meta.rules.splice(i, 1)}><Icon name="close" size={14} /></button>{/if}
                      </div>
                      <textarea class="input area" rows="2" placeholder={t("sk.rule.description")} aria-label={t("sk.rule.description")}
                                readonly={!editable} bind:value={rule.description}></textarea>
                    </li>
                  {/each}
                </ul>
                {#if editable}<button class="btn btn-sm" onclick={addRule}><Icon name="plus" size={14} /> {t("sk.rule.add")}</button>{/if}
              {:else if tab === "template"}
                <p class="field-l">{t("sk.template")}</p>
                {#if !editable}<p class="hint pane-hint">{t("sk.template_builtin")}</p>{/if}
                <div class="actions">
                  <button class="btn" onclick={() => saveUrl(`/api/skills/${skill.name}/template.docx`, `${skill.name}.docx`)}>
                    <Icon name="download" size={14} /> {t("sk.template_download")}</button>
                  {#if editable}
                    {#if desktop}<button class="btn btn-primary" onclick={() => reveal("template")}>{t("sk.template_open")}</button>{/if}
                    <input type="file" accept=".docx" class="hidden" bind:this={templateInput} onchange={uploadTemplate} aria-label={t("sk.template_upload")} />
                    <button class="btn" onclick={() => templateInput.click()}><Icon name="upload" size={14} /> {t("sk.template_upload")}</button>
                  {/if}
                </div>
                <div class="field num-field">
                  <label class="label" for="sk-num">{t("sk.numbering")}</label>
                  <select class="select" id="sk-num" disabled={!editable} bind:value={draft.meta.numbering}>
                    <option value="dot">{t("sk.numbering.dot")}</option>
                    <option value="plain">{t("sk.numbering.plain")}</option>
                  </select>
                </div>
                <p class="field-l ph-t">{t("sk.placeholders")}</p>
                <p class="hint pane-hint">{t("sk.placeholders_hint")}</p>
                <table class="table ph"><tbody>
                  {#each skill.placeholders || [] as ph (ph.code)}
                    <tr><td class="mono">{ph.code}</td><td>{ph.label}</td></tr>
                  {/each}
                </tbody></table>
              {:else if tab === "try"}
                <p class="hint pane-hint">{t("sk.try_hint." + tryMode)}</p>
                {#if tryMode === "export"}
                  <button class="btn" onclick={exportSample}><Icon name="download" size={14} /> {t("sk.try_export")}</button>
                {:else}
                  <div class="row">
                    {#if tryMode === "source"}
                      <div class="field grow">
                        <label class="label" for="sk-src">{t("sk.try_source")}</label>
                        {#if readySources.length}
                          <select class="select" id="sk-src" bind:value={trySource}>
                            {#each readySources as s (s.id)}<option value={s.id}>{s.title}</option>{/each}
                          </select>
                        {:else}<p class="muted">{t("sk.try_none")}</p>{/if}
                      </div>
                    {/if}
                    <button class="btn btn-primary" disabled={tryState?.running || (tryMode === "source" && !trySource)}
                            onclick={runTry}>{#if tryState?.running}<span class="spinner"></span>{/if}{t("sk.try_run")}</button>
                  </div>
                  {#if tryState?.running}
                    <p class="hint" style="margin-top: var(--sp-4)">{tryState.message}</p>
                    {#if tryState.partial}<div class="md result">{@html renderMarkdown(tryState.partial)}</div>{/if}
                  {:else if tryState?.result}
                    {@const r = tryState.result}
                    <div class="result">
                      {#if r.kind === "markdown"}
                        <div class="md">{@html renderMarkdown(r.text)}</div>
                      {:else if r.kind === "atoms"}
                        <p class="label">{t("sk.try_atoms", { n: r.atoms.length })}{#if r.dropped} · {t("sk.try_dropped", { n: r.dropped })}{/if}</p>
                        <ul class="try-atoms">
                          {#each r.atoms as a, i (i)}
                            <li><span class="tag {typeClass[a.type]}">{t("at.type." + a.type)}</span> <span class="st">{a.statement}</span>
                              {#each a.evidence as ev, j (j)}<span class="quote">«{ev.quote}»</span>{/each}</li>
                          {/each}
                        </ul>
                        {#if r.skipped?.length}
                          <p class="label">{t("sk.try_skipped")}: {r.skipped.length}</p>
                          <ul class="try-atoms skipped">
                            {#each r.skipped as x, i (i)}<li><span class="tag outline">{t("sk.skip." + x.type)}</span> {x.statement}</li>{/each}
                          </ul>
                        {/if}
                      {:else if r.kind === "document"}
                        {#each r.content.sections as sec (sec.key)}
                          <h4>{sec.number}. {sec.title}</h4>
                          {#each [...sec.blocks, ...(sec.subsections || []).flatMap(sub => [{ kind: "sub", text: `${sub.number} ${sub.title}` }, ...sub.blocks])] as b, i (i)}
                            {#if b.kind === "sub"}<h5>{b.text}</h5>
                            {:else if b.kind === "req"}<p><b class="mono">{b.id}</b> {b.text}
                              {#each b.issues || [] as is, k (k)}<span class="tag warn">{r.content.rule_titles?.[is.rule] || t("doc.rule." + is.rule)}: {is.message}</span>{/each}</p>
                            {:else if b.kind === "text"}<p>{b.text}</p>
                            {:else if b.kind === "list"}<ul>{#each b.items as it, k (k)}<li>{it}</li>{/each}</ul>{/if}
                          {/each}
                        {/each}
                      {/if}
                    </div>
                  {/if}
                {/if}
              {:else if tab === "contract"}
                <p class="hint pane-hint">{t("sk.contract_hint")}</p>
                {#if skill.contract}<pre class="contract">{skill.contract}</pre>{:else}<p class="muted">{t("sk.no_contract")}</p>{/if}
              {:else if tab === "history"}
                {#if !skill.history.length}<p class="muted">{t("sk.history_empty")}</p>{/if}
                <ul class="history">
                  {#each skill.history as h (h.id)}
                    <li>
                      <span class="num">{fmtDate(h.at, app.lang)}</span>
                      <span class="tag outline">{h.kind === "template" ? t("sk.history_template") : t("sk.history_text")}</span>
                      <span class="spacer"></span>
                      {#if h.kind === "text"}<button class="btn btn-ghost btn-sm" onclick={() => showHistory(h)}>{t("sk.show")}</button>{/if}
                      <button class="btn btn-sm" onclick={() => restore(h)}>{t("sk.restore")}</button>
                    </li>
                    {#if historyText?.id === h.id}<li class="h-text"><pre class="contract">{historyText.text}</pre></li>{/if}
                  {/each}
                </ul>
              {/if}
            </div>

            {#if stageInfo && !skill.error}
              <div class="usage">
                <span class="label">{t("sk.use")}</span>
                {#if stageInfo.global === skill.name}
                  <span class="status ok"><Icon name="check" size={14} /> {t("sk.is_global")}</span>
                {:else}
                  <button class="btn btn-sm" onclick={useGlobally}>{t("sk.use_global")}</button>
                {/if}
                <label class="check">
                  <input type="checkbox" class="switch" checked={stageInfo.project === skill.name}
                         onchange={e => useForProject(e.currentTarget.checked)} />
                  {t("sk.use_project", { name: currentProject()?.name || "" })}
                </label>
                {#if stageInfo.effective !== skill.name && stageInfo.project && stageInfo.project !== skill.name}
                  <span class="hint">{t("sk.project_override", { name: list.skills.find(x => x.name === stageInfo.project)?.title || stageInfo.project })}</span>
                {/if}
              </div>
            {/if}
          </div>

          {#if editable && dirty}
            <div class="savebar">
              <span class="t2">{t("sk.unsaved")}</span><span class="kbd">⌘S</span>
              <span class="spacer"></span>
              <button class="btn btn-ghost" onclick={() => loadSkill(skill.name)}>{t("sk.revert")}</button>
              <button class="btn btn-primary" disabled={saving} onclick={save}>{#if saving}<span class="spinner"></span>{/if}{t("sk.save")}</button>
            </div>
          {/if}
          {/key}
        {/if}
      </section>
    </div>
  {/if}
</div>

<style>
  .layout { display: grid; grid-template-columns: 272px minmax(0, 1fr); gap: var(--sp-6); align-items: start; }
  .list { position: sticky; top: calc(var(--toolbar) + 8px); background: var(--surface); border-radius: var(--r-lg); box-shadow: var(--e1);
    padding: var(--sp-3); max-height: calc(100vh - var(--toolbar) - 24px); overflow: auto; }
  .g-title { font-size: var(--fs-11); font-weight: 600; color: var(--text-3); padding: var(--sp-5) var(--sp-4) var(--sp-2); }
  .g-title:first-child { padding-top: var(--sp-3); }
  .item { display: grid; grid-template-columns: 7px minmax(0, 1fr) auto; column-gap: var(--sp-4); align-items: baseline; width: 100%;
    border: 0; background: transparent; text-align: left; padding: 6px var(--sp-4); border-radius: var(--r-sm); cursor: pointer; }
  .item:hover { background: var(--surface-2); }
  .item.on { background: var(--accent-bg); }
  .item .dot { background: var(--ok); align-self: center; }
  .item .dot.off { background: transparent; box-shadow: inset 0 0 0 1px var(--line-control); }
  .i-title { font-weight: 500; line-height: 17px; min-width: 0; }
  .item.err .i-title { color: var(--danger); }
  .own { font-size: var(--fs-11); color: var(--text-3); }
  .in-use { grid-column: 2; font-size: var(--fs-11); color: var(--ok); line-height: 14px; }

  .editor { min-width: 0; padding-bottom: var(--sp-10); }
  .sk-card { overflow: hidden; }
  .head { display: flex; align-items: flex-start; gap: var(--sp-6); padding: var(--sp-6) var(--sp-7) var(--sp-5); flex-wrap: wrap; }
  .e-title { flex: 1 1 320px; min-width: 0; }
  .e-title h2, .title-input { font: 600 var(--fs-17)/24px var(--font-display); }
  .title-input { height: 32px; }
  .meta { font-size: var(--fs-12); color: var(--text-3); margin-top: 2px; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
  .desc { margin-top: var(--sp-4); max-width: 72ch; }
  .desc-input { margin-top: var(--sp-4); }
  .danger-text { color: var(--danger); }
  .pad { margin: 0 var(--sp-7) var(--sp-5); }
  .tabs { display: flex; gap: var(--sp-7); overflow-x: auto; scrollbar-width: none; white-space: nowrap; padding: 0 var(--sp-7);
    border-bottom: 1px solid var(--line); }
  .tabs button { border: 0; background: transparent; padding: 10px 0; font-weight: 500; color: var(--text-2); border-bottom: 2px solid transparent;
    margin-bottom: -1px; display: inline-flex; gap: 6px; align-items: center; cursor: pointer; }
  .tabs button:hover { color: var(--text); }
  .tabs button[aria-selected="true"] { color: var(--text); border-bottom-color: var(--accent); }
  .tabs .n { color: var(--text-3); font-size: var(--fs-12); font-variant-numeric: tabular-nums; }
  .pane { padding: var(--sp-6) var(--sp-7) var(--sp-7); }
  .pane-hint { margin-bottom: var(--sp-5); max-width: 80ch; }
  .field-l { font-size: var(--fs-12); font-weight: 600; color: var(--text-2); margin-bottom: 6px; display: flex; justify-content: space-between; gap: 8px; }
  .vars { font-weight: 400; }
  .rules-t, .ph-t { margin-top: var(--sp-8); }
  .vague { margin-bottom: var(--sp-2); }
  .num-field { margin-top: var(--sp-6); max-width: 320px; }

  .code-area { font: 12.5px/20px var(--mono); padding: var(--sp-5) var(--sp-6); border-radius: var(--r-md); min-height: 320px; height: auto;
    resize: vertical; tab-size: 2; }
  .area { resize: vertical; }
  textarea[readonly], input[readonly] { background: var(--surface-2); color: var(--text-2); border-color: transparent; }
  .sections, .rules, .history, .try-atoms { list-style: none; margin: 0 0 var(--sp-5); padding: 0; }
  .sec-row, .rule { display: flex; flex-direction: column; gap: var(--sp-4); padding: var(--sp-5) 0; border-bottom: 1px solid var(--line); }
  .sec-row:first-child, .rule:first-child { padding-top: 0; }
  .sec-head { display: flex; align-items: center; gap: var(--sp-4); }
  .sec-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); gap: var(--sp-4); align-items: center; }
  .rule .sec-fields { grid-template-columns: 160px minmax(0, 1fr) auto; }
  .spacer { flex: 1; }
  .ph td { height: 36px; }
  .ph td:first-child { white-space: nowrap; width: 1%; color: var(--accent); }
  .contract { white-space: pre-wrap; font: 12px/19px var(--mono); background: var(--surface-2); padding: var(--sp-5) var(--sp-6);
    border-radius: var(--r-md); margin: 0; color: var(--text-2); }
  .history li { display: flex; align-items: center; gap: var(--sp-4); padding: var(--sp-4) 0; border-bottom: 1px solid var(--line); }
  .history .h-text { display: block; padding-top: 0; }
  .result { margin-top: var(--sp-6); border-radius: var(--r-md); background: var(--surface-2); padding: var(--sp-5) var(--sp-6);
    max-height: 560px; overflow-y: auto; }
  .result h4 { font-size: var(--fs-13); font-weight: 600; margin: var(--sp-5) 0 var(--sp-2); }
  .result h4:first-child { margin-top: 0; }
  .result h5 { font-size: var(--fs-12); font-weight: 600; margin: var(--sp-4) 0 var(--sp-2); }
  .result p { margin: var(--sp-2) 0; }
  .result .tag { margin-left: var(--sp-2); }
  .try-atoms li { padding: var(--sp-4) var(--sp-5); background: var(--surface); border-radius: var(--r-sm); margin-top: var(--sp-3); }
  .try-atoms .st { font-weight: 500; }
  .try-atoms .tag { margin: 0 var(--sp-2) 0 0; }
  .quote { display: block; font-size: var(--fs-12); color: var(--text-2); margin-top: 2px; }
  .skipped li { color: var(--text-3); }
  .usage { display: flex; align-items: center; gap: var(--sp-6); flex-wrap: wrap; padding: var(--sp-5) var(--sp-7); border-top: 1px solid var(--line);
    background: color-mix(in srgb, var(--surface-2) 45%, transparent); }
  .savebar { position: sticky; bottom: var(--sp-5); display: flex; align-items: center; gap: var(--sp-4); margin-top: var(--sp-5);
    padding: 6px 6px 6px var(--sp-6); border-radius: var(--r-xl); background: var(--surface); box-shadow: var(--e3); z-index: 20;
    animation: fadein var(--t-slow) var(--ease); }

  @media (max-width: 1120px) { .layout { grid-template-columns: 220px minmax(0, 1fr); } }
  @media (max-width: 840px) {
    .layout { grid-template-columns: 1fr; }
    .list { position: static; max-height: 240px; }
    .rule .sec-fields { grid-template-columns: 1fr auto; }
  }
</style>
