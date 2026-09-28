<script>
  import Block from "../components/Block.svelte";
  import Icon from "../components/Icon.svelte";
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
      const setup = err.body?.needs_setup;
      toast(err.message, { kind: "danger", ...(setup ? { action: t("nav.settings"), onAction: () => go("/settings") } : {}) });
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
  const typeClass = { functional: "accent", nfr: "", question: "warn" };
</script>

<svelte:window onkeydown={onKey} />

<div class="screen-inner wide">
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("sk.title")}</h1>
      <p class="screen-sub">{t("sk.sub")}</p>
    </div>
    <div class="actions">
      <input type="file" accept=".zip,.md" class="hidden" bind:this={importInput} onchange={importFile} />
      <button class="btn" title={t("sk.import_hint")} onclick={() => importInput.click()}><Icon name="upload" /> {t("sk.import")}</button>
    </div>
  </header>

  {#if error}<p class="note danger">{error}</p>{/if}

  {#if list}
    <div class="layout">
      <nav class="list" aria-label={t("sk.title")}>
        {#each grouped as g (g.id)}
          <div class="group">
            <p class="g-title">{g.id === "broken" ? t("sk.broken") : t("sk.stage." + g.id)}</p>
            {#each g.skills as s (s.name + g.id)}
              {#if g.id === "broken" || !s.error}
                <button class="item" class:on={s.name === selected} class:err={!!s.error} onclick={() => open(s.name)}>
                  <span class="i-title">{s.title}</span>
                  <span class="i-tags">
                    {#if g.id !== "broken" && g.effective === s.name}<span class="tag ok">{t("sk.in_use")}</span>{/if}
                    <span class="tag">{s.builtin ? t("sk.builtin") : t("sk.custom")}</span>
                  </span>
                </button>
              {/if}
            {/each}
          </div>
        {/each}
      </nav>

      <section class="editor">
        {#if !skill || !draft}
          <div class="empty panel"><p>{t("sk.pick")}</p></div>
        {:else}
          {#key skill.name}
          <div class="panel e-head">
            <div class="e-title">
              {#if editable}
                <input class="input title-input" bind:value={draft.title} aria-label={t("sk.name")} />
              {:else}
                <h2>{skill.title}</h2>
              {/if}
              <p class="mono faint">{skill.name} · {t("sk.stage." + skill.stage)} · v{skill.version}</p>
            </div>
            <div class="actions">
              <button class="btn" onclick={copy}><Icon name="copy" /> {t("sk.copy")}</button>
              <button class="btn btn-ghost" onclick={() => saveUrl(`/api/skills/${skill.name}/export.zip`, `${skill.name}.zip`)}>
                <Icon name="download" /> {t("sk.export_zip")}</button>
              {#if editable && desktop}<button class="btn btn-ghost" onclick={() => reveal("folder")}>{t("sk.folder")}</button>{/if}
              {#if editable}<button class="btn btn-ghost danger-text" onclick={remove}><Icon name="trash" /> {t("sk.delete")}</button>{/if}
            </div>
          </div>

          {#if skill.error}<p class="note danger">{t("sk.error", { error: skill.error })}</p>{/if}
          <p class="hint">{t("sk.hint." + skill.stage)}</p>

          {#if stageInfo && !skill.error}
            <div class="panel use">
              <span class="label">{t("sk.use")}</span>
              {#if stageInfo.global === skill.name}
                <span class="tag ok">{t("sk.is_global")}</span>
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

          {#if !editable && !skill.error}<p class="note">{t("sk.readonly")}</p>{/if}

          <div class="stack">
            {#if editable}
              <div class="field">
                <label class="label" for="sk-desc">{t("sk.description")}</label>
                <input class="input" id="sk-desc" bind:value={draft.description} />
              </div>
            {:else if skill.description}
              <p class="muted">{skill.description}</p>
            {/if}

            {#if skill.stage !== "export"}
              <div class="field">
                <label class="label" for="sk-instr">{t("sk.instructions")}</label>
                <textarea id="sk-instr" class="input area code-area" rows="16" readonly={!editable}
                          bind:value={draft.instructions} spellcheck="false"></textarea>
                {#if ["frd", "fix", "global", "quality"].includes(skill.stage)}<span class="hint">{t("sk.vars")}</span>{/if}
              </div>
            {/if}

            {#if skill.stage === "frd" && draft.meta.sections}
              <Block id="sk-sections" title={t("sk.sections")} meta={String(draft.meta.sections.length)}>
                <p class="hint" style="margin-bottom: var(--s-3)">{t("sk.sections_hint")}</p>
                <ol class="sections">
                  {#each draft.meta.sections as sec, i (i + sec.key)}
                    <li class="sec-row">
                      <div class="sec-head">
                        <span class="mono faint">{i + 1}. {sec.key}</span>
                        {#if REQUIRED.includes(sec.key)}<span class="tag">{t("sk.sec.required")}</span>{/if}
                        <span class="spacer"></span>
                        {#if editable}
                          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.up")} disabled={i === 0} onclick={() => move(i, -1)}>↑</button>
                          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.down")} disabled={i === draft.meta.sections.length - 1} onclick={() => move(i, 1)}>↓</button>
                          {#if !REQUIRED.includes(sec.key)}
                            <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.remove")}
                                    onclick={() => draft.meta.sections.splice(i, 1)}><Icon name="close" /></button>
                          {/if}
                        {/if}
                      </div>
                      <div class="sec-fields">
                        <input class="input" placeholder={t("sk.sec.title_ru")} readonly={!editable}
                               value={titleOf(sec.title, "ru")} oninput={e => setTitle(sec, "ru", e.currentTarget.value)} />
                        <input class="input" placeholder={t("sk.sec.title_en")} readonly={!editable}
                               value={titleOf(sec.title, "en")} oninput={e => setTitle(sec, "en", e.currentTarget.value)} />
                      </div>
                      {#if !KINDS.includes(sec.key)}
                        <textarea class="input area" rows="2" placeholder={t("sk.sec.instructions")} readonly={!editable}
                                  bind:value={sec.instructions}></textarea>
                      {/if}
                    </li>
                  {/each}
                </ol>
                {#if editable}
                  <button class="btn btn-sm" onclick={addSection}><Icon name="plus" /> {t("sk.sec.add")}</button>
                {/if}
              </Block>
            {/if}

            {#if skill.stage === "quality"}
              <Block id="sk-vague" title={t("sk.vague")}>
                <p class="hint" style="margin-bottom: var(--s-2)">{t("sk.vague_hint")}</p>
                {#each ["ru", "en"] as lang (lang)}
                  <div class="field">
                    <span class="label">{lang === "ru" ? "Русский" : "English"}</span>
                    <textarea class="input area" rows="2" readonly={!editable} value={words(lang)}
                              onchange={e => setWords(lang, e.currentTarget.value)}></textarea>
                  </div>
                {/each}
              </Block>
              <Block id="sk-rules" title={t("sk.rules")} meta={String((draft.meta.rules || []).length)}>
                <ul class="rules">
                  {#each draft.meta.rules || [] as rule, i (i)}
                    <li class="rule">
                      <div class="sec-fields">
                        <input class="input code" placeholder={t("sk.rule.id")} readonly={!editable} bind:value={rule.id} />
                        <input class="input" placeholder={t("sk.rule.title")} readonly={!editable} bind:value={rule.title} />
                        {#if editable}<button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")}
                                onclick={() => draft.meta.rules.splice(i, 1)}><Icon name="close" /></button>{/if}
                      </div>
                      <textarea class="input area" rows="2" placeholder={t("sk.rule.description")} readonly={!editable}
                                bind:value={rule.description}></textarea>
                    </li>
                  {/each}
                </ul>
                {#if editable}<button class="btn btn-sm" onclick={addRule}><Icon name="plus" /> {t("sk.rule.add")}</button>{/if}
              </Block>
            {/if}

            {#if skill.stage === "export"}
              <div class="panel">
                <p class="panel-title">{t("sk.template")}</p>
                {#if !editable}<p class="panel-desc">{t("sk.template_builtin")}</p>{/if}
                <div class="actions" style="margin-top: var(--s-2)">
                  <button class="btn" onclick={() => saveUrl(`/api/skills/${skill.name}/template.docx`, `${skill.name}.docx`)}>
                    <Icon name="download" /> {t("sk.template_download")}</button>
                  {#if editable}
                    {#if desktop}<button class="btn btn-primary" onclick={() => reveal("template")}>{t("sk.template_open")}</button>{/if}
                    <input type="file" accept=".docx" class="hidden" bind:this={templateInput} onchange={uploadTemplate} />
                    <button class="btn" onclick={() => templateInput.click()}><Icon name="upload" /> {t("sk.template_upload")}</button>
                  {/if}
                </div>
                <div class="field" style="margin-top: var(--s-4); max-width: 320px">
                  <label class="label" for="sk-num">{t("sk.numbering")}</label>
                  <select class="select" id="sk-num" disabled={!editable} bind:value={draft.meta.numbering}>
                    <option value="dot">{t("sk.numbering.dot")}</option>
                    <option value="plain">{t("sk.numbering.plain")}</option>
                  </select>
                </div>
              </div>
              <Block title={t("sk.placeholders")} open={editable}>
                <p class="hint" style="margin-bottom: var(--s-2)">{t("sk.placeholders_hint")}</p>
                <table class="ph"><tbody>
                  {#each skill.placeholders || [] as ph (ph.code)}
                    <tr><td class="mono">{ph.code}</td><td>{ph.label}</td></tr>
                  {/each}
                </tbody></table>
              </Block>
            {/if}

            {#if tryMode && !skill.error}
              <Block id="sk-try" title={t("sk.try")}>
                <p class="hint" style="margin-bottom: var(--s-3)">{t("sk.try_hint." + tryMode)}</p>
                {#if tryMode === "export"}
                  <button class="btn" onclick={exportSample}><Icon name="download" /> {t("sk.try_export")}</button>
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
                    <p class="hint" style="margin-top: var(--s-2)">{tryState.message}</p>
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
                            <li><span class="tag {typeClass[a.type]}">{t("at.type." + a.type)}</span> {a.statement}
                              {#each a.evidence as ev, j (j)}<span class="quote">«{ev.quote}»</span>{/each}</li>
                          {/each}
                        </ul>
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
              </Block>
            {/if}

            <Block id="sk-contract" title={t("sk.contract")} open={false}>
              <p class="hint" style="margin-bottom: var(--s-2)">{t("sk.contract_hint")}</p>
              {#if skill.contract}<pre class="contract">{skill.contract}</pre>{:else}<p class="muted">{t("sk.no_contract")}</p>{/if}
            </Block>

            {#if editable}
              <Block id="sk-history" title={t("sk.history")} meta={String(skill.history.length)} open={false}>
                {#if !skill.history.length}<p class="muted">{t("sk.history_empty")}</p>{/if}
                <ul class="history">
                  {#each skill.history as h (h.id)}
                    <li>
                      <span>{fmtDate(h.at, app.lang)}</span>
                      <span class="tag">{h.kind === "template" ? t("sk.history_template") : t("sk.history_text")}</span>
                      <span class="spacer"></span>
                      {#if h.kind === "text"}<button class="btn btn-ghost btn-sm" onclick={() => showHistory(h)}>{t("sk.show")}</button>{/if}
                      <button class="btn btn-sm" onclick={() => restore(h)}>{t("sk.restore")}</button>
                    </li>
                    {#if historyText?.id === h.id}<li class="h-text"><pre class="contract">{historyText.text}</pre></li>{/if}
                  {/each}
                </ul>
              </Block>
            {/if}
          </div>

          {#if editable && dirty}
            <div class="savebar panel">
              <span class="hint">{t("sk.unsaved")} · ⌘S</span>
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
  .wide { width: min(1240px, 100%); }
  .layout { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: var(--s-5); align-items: start; }
  .list { position: sticky; top: var(--s-4); max-height: calc(100vh - var(--s-6)); overflow-y: auto; display: flex;
    flex-direction: column; gap: var(--s-3); padding-right: var(--s-1); }
  .g-title { font-size: var(--t-xs); text-transform: uppercase; letter-spacing: .04em; color: var(--ink-3); margin: 0 0 var(--s-1) var(--s-2); }
  .item { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; width: 100%; text-align: left; border: 0;
    background: none; padding: var(--s-2); border-radius: var(--r-md); cursor: pointer; }
  .item:hover { background: var(--sunk); }
  .item.on { background: var(--accent-bg); }
  .item.err .i-title { color: var(--danger); }
  .i-title { font-weight: 500; font-size: var(--t-sm); line-height: 1.35; }
  .i-tags { display: flex; gap: var(--s-1); flex-wrap: wrap; }

  .editor { min-width: 0; display: flex; flex-direction: column; gap: var(--s-3); padding-bottom: var(--s-7); }
  .e-head { display: flex; gap: var(--s-3); align-items: flex-start; justify-content: space-between; flex-wrap: wrap; }
  .e-title { min-width: 0; flex: 1 1 260px; }
  .e-title h2 { font-size: var(--t-lg); font-weight: 600; }
  .title-input { font-size: var(--t-lg); font-weight: 600; }
  .danger-text { color: var(--danger); }
  .use { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; padding: var(--s-2) var(--s-4); }
  .use .label { margin-right: var(--s-1); }

  .area { height: auto; padding: var(--s-2) var(--s-3); line-height: 1.55; resize: vertical; }
  .code-area { font-family: var(--mono); font-size: var(--t-sm); min-height: 260px; }
  textarea[readonly], input[readonly] { background: var(--sunk); color: var(--ink-2); }
  .sections, .rules, .history, .try-atoms { list-style: none; margin: 0 0 var(--s-3); padding: 0; }
  .sec-row, .rule { display: flex; flex-direction: column; gap: var(--s-2); padding: var(--s-3) 0; border-top: 1px solid var(--rule); }
  .sec-row:first-child, .rule:first-child { border-top: 0; padding-top: 0; }
  .sec-head { display: flex; align-items: center; gap: var(--s-2); }
  .sec-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); gap: var(--s-2); align-items: center; }
  .rule .sec-fields { grid-template-columns: 160px minmax(0, 1fr) auto; }
  .spacer { flex: 1; }
  .ph { border-collapse: collapse; width: 100%; font-size: var(--t-sm); }
  .ph td { padding: 5px var(--s-2); border-top: 1px solid var(--rule); vertical-align: top; }
  .ph td:first-child { white-space: nowrap; width: 1%; color: var(--accent); }
  .contract { white-space: pre-wrap; font-family: var(--mono); font-size: var(--t-xs); line-height: 1.6; background: var(--sunk);
    padding: var(--s-3); border-radius: var(--r-md); margin: 0; color: var(--ink-2); }
  .history li { display: flex; align-items: center; gap: var(--s-2); padding: var(--s-2) 0; border-top: 1px solid var(--rule); }
  .history li:first-child { border-top: 0; }
  .history .h-text { display: block; border-top: 0; padding-top: 0; }
  .result { margin-top: var(--s-3); border-top: 1px solid var(--rule); padding-top: var(--s-3); max-height: 520px; overflow-y: auto; }
  .result h4 { font-size: var(--t-md); font-weight: 600; margin: var(--s-3) 0 var(--s-1); }
  .result h5 { font-size: var(--t-sm); font-weight: 600; margin: var(--s-2) 0 var(--s-1); }
  .result p { line-height: 1.6; margin: var(--s-1) 0; }
  .result .tag { margin-left: var(--s-1); }
  .try-atoms li { padding: var(--s-2) 0; border-top: 1px solid var(--rule); line-height: 1.55; }
  .quote { display: block; font-size: var(--t-sm); color: var(--ink-2); }
  .savebar { position: sticky; bottom: var(--s-3); display: flex; align-items: center; gap: var(--s-2);
    padding: var(--s-2) var(--s-3); box-shadow: 0 6px 20px rgba(0,0,0,.12); z-index: 20; }

  @media (max-width: 900px) {
    .layout { grid-template-columns: 1fr; }
    .list { position: static; max-height: none; }
  }
</style>
