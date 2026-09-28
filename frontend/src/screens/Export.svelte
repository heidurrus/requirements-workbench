<script>
  import Icon from "../components/Icon.svelte";
  import { api, pollJob } from "../lib/api.js";
  import { app, t, go, toast } from "../lib/state.svelte.js";

  let connected = $state(null);
  let waiting = $state(false);           // sign-in open in the browser
  let target = $state(null);
  let editingTarget = $state(false);
  let sites = $state([]);
  let projects = $state([]);
  let pick = $state({ cloud_id: "", project_key: "", q: "", types: {} });
  let loadingProjects = $state(false);
  let preview = $state(null);            // {rows, counts, target}
  let selected = $state({});             // item_id → bool
  let busy = $state(null);               // {kind, progress, message}
  let confirming = $state(false);
  let result = $state(null);

  const KINDS = ["epic", "story", "nfr", "subtask"];

  async function status() {
    try { connected = (await api("/api/jira/status")).connected; } catch (_) { connected = false; }
  }
  async function loadTarget() {
    target = (await api(`/api/projects/${app.currentProjectId}/jira/target`)).target;
    editingTarget = !target;
  }
  $effect(() => { app.currentProjectId; preview = null; result = null; status(); loadTarget(); });
  $effect(() => { if (connected && !sites.length) loadSites(); });

  function fail(err) {
    if (err.body?.needs_connect) connected = false;
    toast(err.message, { kind: "danger", ms: 10000 });
  }

  let privateNote = $state("");
  async function connect(privateWindow = true) {
    try {
      const { url, opened_private } = await api("/api/jira/connect", { method: "POST", body: { private: privateWindow } });
      if (opened_private) {
        privateNote = t("jr.private_opened", { browser: opened_private });
      } else {
        privateNote = privateWindow ? t("jr.private_missing") : "";
        if (window.pywebview?.api?.open_url) await window.pywebview.api.open_url(url);
        else window.open(url, "_blank");
      }
      waiting = true;
      for (let i = 0; i < 150 && waiting; i++) {          // up to 5 minutes for the sign-in
        await new Promise(r => setTimeout(r, 2000));
        await status();
        if (connected) { waiting = false; toast(t("jr.connected")); loadSites(); break; }
      }
      waiting = false;
    } catch (err) { waiting = false; fail(err); }
  }
  async function disconnect() {
    await api("/api/jira/disconnect", { method: "POST" });
    connected = false;
    preview = null;
    sites = [];
    projects = [];
  }

  async function loadSites() {
    try {
      sites = (await api("/api/jira/sites")).sites;
      if (!pick.cloud_id) pick.cloud_id = target?.cloud_id || sites[0]?.cloud_id || "";
      if (pick.cloud_id) loadProjects();
    } catch (err) { fail(err); }
  }
  async function loadProjects() {
    loadingProjects = true;
    try {
      const q = pick.q ? `&q=${encodeURIComponent(pick.q)}` : "";
      projects = (await api(`/api/jira/projects?cloud_id=${pick.cloud_id}${q}`)).projects;
      if (target && target.cloud_id === pick.cloud_id && projects.some(p => p.key === target.project_key)) {
        pick.project_key = target.project_key;
        pick.types = { ...target.types };
      }
    } catch (err) { fail(err); }
    finally { loadingProjects = false; }
  }
  const chosenProject = $derived(projects.find(p => p.key === pick.project_key));
  function chooseProject(key) {
    pick.project_key = key;
    const p = projects.find(x => x.key === key);
    pick.types = p ? { ...p.suggested_types } : {};
  }
  async function saveTarget() {
    const site = sites.find(s => s.cloud_id === pick.cloud_id);
    try {
      target = (await api(`/api/projects/${app.currentProjectId}/jira/target`, { method: "PUT", body: {
        cloud_id: pick.cloud_id, site_url: site?.url || "", project_key: pick.project_key,
        project_name: chosenProject?.name, types: pick.types } })).target;
      editingTarget = false;
      preview = null;
    } catch (err) { fail(err); }
  }

  async function runPreview() {
    result = null;
    busy = { kind: "preview", progress: 0, message: t("jr.reading") };
    try {
      const { job_id } = await api(`/api/projects/${app.currentProjectId}/jira/preview`, { method: "POST" });
      const job = await pollJob(job_id, j => (busy = { kind: "preview", progress: j.progress || 0, message: j.progress_msg || "" }));
      preview = job.result;
      // Creates and updates start ticked; unchanged rows and rows edited in Jira need an explicit tick (FR-JIRA-03/06).
      selected = Object.fromEntries(preview.rows.map(r => [r.item_id,
        ["create", "update"].includes(r.action) && !r.flags.includes("changed_in_jira")]));
    } catch (err) { fail(err); }
    finally { busy = null; }
  }
  const pushable = $derived(preview ? preview.rows.filter(r => ["create", "update"].includes(r.action) && selected[r.item_id]) : []);

  async function push(ids = pushable.map(r => r.item_id)) {
    confirming = false;
    busy = { kind: "push", progress: 0, message: "" };
    try {
      const { job_id } = await api(`/api/projects/${app.currentProjectId}/jira/push`, { method: "POST",
        body: { item_ids: ids, confirm_project_key: target.project_key } });
      const job = await pollJob(job_id, j => (busy = { kind: "push", progress: j.progress || 0, message: j.progress_msg || "" }));
      result = job.result;
      toast(t("jr.pushed", { n: result.done.length }));
      preview = null;
    } catch (err) { fail(err); }
    finally { busy = null; }
  }
  const actionTag = { create: "ok", update: "fr", unchanged: "outline", skip: "outline", blocked: "danger" };
  const indent = { epic: 0, story: 1, nfr: 1, subtask: 2 };
  const glyph = { epic: "E", story: "S", subtask: "T", nfr: "N" };
  const step = $derived(!connected ? 1 : !target || editingTarget ? 2 : 3);
  const site = u => (u || "").replace("https://", "");
  const pushCounts = $derived({ create: pushable.filter(r => r.action === "create").length,
                                update: pushable.filter(r => r.action === "update").length });

  let cancelBtn = $state(null);
  $effect(() => { if (confirming && cancelBtn) cancelBtn.focus(); });
  function onKey(e) {
    if (app.route.name !== "export") return;
    if (confirming && e.key === "Escape") { e.preventDefault(); confirming = false; return; }
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && preview && pushable.length && !busy) {
      e.preventDefault();
      if (confirming) push(); else confirming = true;
    }
  }
</script>

<svelte:window onkeydown={onKey} />

<div class="screen-inner">
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("jr.title")}</h1>
      <p class="screen-sub">
        {#if target}{[target.project_key, target.project_name, site(target.site_url)].filter(Boolean).join(" · ")}
        {:else}{t("jr.sub_empty")}{/if}
      </p>
    </div>
    {#if connected && target && !editingTarget}
      <div class="actions">
        <button class="btn" disabled={!!busy} onclick={runPreview}>
          <Icon name="refresh" size={14} /> {preview ? t("jr.refresh") : t("jr.show_preview")}</button>
      </div>
    {/if}
  </header>

  <nav class="stepper" aria-label={t("jr.title")}>
    {#each [t("jr.account"), t("jr.target"), t("jr.preview")] as label, i (i)}
      {#if i}<span class="ln"></span>{/if}
      <span class="step" class:done={step > i + 1} class:cur={step === i + 1} aria-current={step === i + 1 ? "step" : undefined}>
        <span class="n">{#if step > i + 1}<Icon name="check" size={12} />{:else}{i + 1}{/if}</span>{label}</span>
    {/each}
  </nav>

  <div class="stack">
    <section class="card setup">
      <!-- 1. connection -->
      <div class="done-card">
        <span class="k">{t("jr.account")}</span>
        <div class="v">
          {#if connected}
            <span class="status ok"><Icon name="check" size={14} />{t("jr.is_connected")}</span>
            {#if sites.length}<p class="map">{t("jr.access", { sites: sites.map(s => site(s.url)).join(", ") })}</p>{/if}
            {#if target && sites.length && !sites.some(s => s.cloud_id === target.cloud_id)}
              <p class="banner danger inline"><Icon name="warn" size={14} /><span>{t("jr.target_not_visible", { site: site(target.site_url) })}</span></p>
            {:else if sites.length}
              <p class="map">{t("jr.wrong_account")}</p>
            {/if}
          {:else if connected === false}
            <p class="t2">{t("jr.connect_hint")}</p>
            {#if privateNote}<p class="map">{privateNote}</p>{/if}
          {/if}
        </div>
        {#if connected}
          <button class="btn btn-ghost btn-sm" onclick={disconnect}>{t("jr.disconnect")}</button>
        {:else if connected === false}
          <div class="actions">
            {#if !waiting}<button class="btn btn-ghost btn-sm" onclick={() => connect(false)}>{t("jr.normal_window")}</button>{/if}
            <button class="btn btn-primary" disabled={waiting} onclick={() => connect(true)}>
              {#if waiting}<span class="spinner"></span> {t("jr.waiting")}{:else}{t("jr.connect")}{/if}</button>
          </div>
        {/if}
      </div>

      <!-- 2. target -->
      {#if connected}
        <div class="done-card" class:editing={!target || editingTarget}>
          <span class="k">{t("jr.target")}</span>
          <div class="v">
            {#if target && !editingTarget}
              <p><b>{target.project_key}</b>{target.project_name ? " · " + target.project_name : ""}<span class="t3">{" · " + site(target.site_url)}</span></p>
              <p class="map">{#each KINDS as k (k)}<span>{t("bl.kind." + k)} → {target.types?.[k] || "—"}</span>{/each}</p>
            {:else}
              <div class="row">
                <div class="field grow">
                  <label class="label" for="jr-site">{t("jr.site")}</label>
                  <select class="select" id="jr-site" bind:value={pick.cloud_id} onchange={loadProjects}>
                    {#each sites as s (s.cloud_id)}<option value={s.cloud_id}>{s.url}</option>{/each}
                  </select>
                </div>
                <div class="field grow">
                  <label class="label" for="jr-q">{t("jr.search")}</label>
                  <input class="input" id="jr-q" bind:value={pick.q} placeholder={t("jr.search_ph")}
                         onkeydown={e => e.key === "Enter" && loadProjects()} />
                </div>
                <button class="btn" onclick={loadProjects} disabled={loadingProjects}>{t("jr.find")}</button>
              </div>
              {#if projects.length}
                <div class="field gap">
                  <label class="label" for="jr-project">{t("jr.project")}</label>
                  <select class="select" id="jr-project" value={pick.project_key} onchange={e => chooseProject(e.currentTarget.value)}>
                    <option value="" disabled>{t("jr.choose_project")}</option>
                    {#each projects as p (p.key)}<option value={p.key}>{p.key} · {p.name}</option>{/each}
                  </select>
                </div>
              {/if}
              {#if chosenProject}
                <p class="label gap">{t("jr.types")}</p>
                <div class="types">
                  {#each KINDS as k (k)}
                    <label class="field">
                      <span class="hint">{t("bl.kind." + k)}</span>
                      <select class="select" bind:value={pick.types[k]}>
                        <option value={null}>—</option>
                        {#each chosenProject.issue_types.filter(it => k === "subtask" ? it.subtask : !it.subtask) as it (it.id)}
                          <option value={it.name}>{it.name}</option>
                        {/each}
                      </select>
                    </label>
                  {/each}
                </div>
              {/if}
              <div class="actions gap">
                <button class="btn btn-primary" disabled={!pick.project_key} onclick={saveTarget}>{t("at.save")}</button>
                {#if target}<button class="btn btn-ghost" onclick={() => (editingTarget = false)}>{t("at.cancel")}</button>{/if}
              </div>
            {/if}
          </div>
          {#if target && !editingTarget}
            <button class="btn btn-ghost btn-sm" onclick={() => { editingTarget = true; loadSites(); }}>{t("jr.change")}</button>
          {/if}
        </div>
      {/if}
    </section>

    <!-- 3. preview and push -->
    {#if connected && target && !editingTarget}
      <div>
        <div class="pv-head">
          <h2 class="h2">{t("jr.preview")}</h2>
          {#if preview}
            <div class="counts">
              {#each ["create", "update", "unchanged", "skip", "blocked"] as a (a)}
                {#if preview.counts[a]}<span class="tag {actionTag[a]}">{t("jr.action." + a)}: {preview.counts[a]}</span>{/if}
              {/each}
            </div>
          {/if}
          <span class="spacer"></span>
          <span class="readonly"><Icon name="lock" size={12} /> {t("jr.no_writes")}</span>
        </div>

        {#if busy}
          <div class="banner info running"><span class="spinner"></span><span class="num">{busy.message}</span>
            <div class="grow"><div class="bar"><i style="width: {busy.progress}%"></i></div></div></div>
        {/if}

        {#if preview}
          <div class="pv">
            <table class="table">
              <thead><tr>
                <th><span class="sr">✓</span></th><th>{t("jr.col_action")}</th><th class="c-type">{t("jr.col_type")}</th>
                <th>{t("jr.col_title")}</th><th class="c-key">{t("jr.col_key")}</th>
              </tr></thead>
              <tbody>
                {#each preview.rows as r (r.item_id)}
                  <tr class:skip={["skip", "blocked", "unchanged"].includes(r.action) && !selected[r.item_id]}>
                    <td class="c"><span class="cb-hit"><input type="checkbox" disabled={!["create", "update", "unchanged"].includes(r.action)}
                                         bind:checked={selected[r.item_id]} aria-label={r.title} /></span></td>
                    <td class="a"><span class="tag {actionTag[r.action]}">{t("jr.action." + r.action)}</span></td>
                    <td class="c-type"><span class="ticon {r.kind}" title={t("bl.kind." + r.kind)}>{glyph[r.kind]}</span></td>
                    <td class="ttl"><div style="padding-left: calc({indent[r.kind]} * 18px)">
                      <span class="tt" title={r.title}>{r.title}</span>
                      {#if r.kind === "subtask" && r.parent_title}<span class="t3">{" ← " + r.parent_title}</span>{/if}
                      {#if r.reason}<span class="t3"> — {t("jr.reason." + r.reason)}</span>{/if}
                      {#each r.flags as f (f)}<span class="flag" class:warn={f === "changed_in_jira"}>{t("jr.flag." + f)}</span>{/each}
                    </div></td>
                    <td class="c-key">{#if r.key}<a href={r.url} target="_blank" rel="noreferrer" class="mono">{r.key}</a>{/if}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
            <div class="pushbar">
              <p>{t("jr.target_note", { key: target.project_key })}</p>
              <button class="btn btn-lg btn-primary" disabled={!pushable.length || !!busy} onclick={() => (confirming = true)}>
                {pushable.length ? t("jr.push", { n: pushable.length }) : t("jr.nothing")}
                {#if pushable.length}<span class="kbd">⌘↵</span>{/if}</button>
            </div>
          </div>
        {:else if !busy && !result}
          <div class="card empty">
            <div class="glyph"><Icon name="export" /></div>
            <p class="panel-title">{t("jr.show_preview")}</p>
            <p>{t("jr.no_writes")}</p>
          </div>
        {/if}

        {#if result}
          <div class="card result">
            <div class="res-h"><span class="status ok"><Icon name="check" size={14} /> {t("jr.result", { n: result.done.length })}</span></div>
            <table class="table"><tbody>
              {#each result.done as d (d.item_id)}
                <tr><td class="a"><span class="tag ok">{t("jr.did." + d.action)}</span></td>
                  <td class="c-key"><a href={d.url} target="_blank" rel="noreferrer" class="mono">{d.key}</a></td>
                  <td>{d.title}</td></tr>
              {/each}
            </tbody></table>
            {#if result.failed.length}
              <div class="failed">
                <p class="status danger"><Icon name="warn" size={14} /> {t("jr.failed", { n: result.failed.length })}</p>
                <ul>{#each result.failed as f (f.item_id)}<li><b>{f.title}</b> — <span class="t3">{f.error}</span></li>{/each}</ul>
                <button class="btn btn-sm" disabled={!!busy} onclick={() => push(result.failed.map(f => f.item_id))}>{t("jr.retry")}</button>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/if}

    <div><button class="btn btn-ghost back" onclick={() => go("/backlog")}><Icon name="back" size={14} /> {t("nav.decomposition")}</button></div>
  </div>
</div>

{#if confirming && target}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="scrim" onclick={e => e.target === e.currentTarget && (confirming = false)}>
    <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="push-q">
      <h2 id="push-q">{t("jr.confirm", { n: pushable.length, key: target.project_key, site: site(target.site_url) })}</h2>
      <p class="t2">{t("jr.sheet_body")}</p>
      <dl class="facts">
        <dt>{t("jr.site")}</dt><dd>{site(target.site_url)}</dd>
        <dt>{t("jr.project")}</dt><dd>{target.project_key}{target.project_name ? " · " + target.project_name : ""}</dd>
        {#if pushCounts.create}<dt>{t("jr.action.create")}</dt><dd class="num">{pushCounts.create}</dd>{/if}
        {#if pushCounts.update}<dt>{t("jr.action.update")}</dt><dd class="num">{pushCounts.update}</dd>{/if}
      </dl>
      <div class="acts">
        <button class="btn" bind:this={cancelBtn} onclick={() => (confirming = false)}>{t("at.cancel")}</button>
        <button class="btn btn-primary" onclick={() => push()}>{t("jr.confirm_yes", { key: target.project_key })} <span class="kbd">⌘↵</span></button>
      </div>
    </div>
  </div>
{/if}

<style>
  .spacer { flex: 1; }
  .grow { flex: 1; min-width: 0; }
  .gap { margin-top: var(--sp-5); }
  .stepper { display: flex; align-items: center; gap: var(--sp-4); margin: 0 0 var(--sp-6); flex-wrap: wrap; }
  .step { display: inline-flex; align-items: center; gap: var(--sp-4); color: var(--text-2); font-weight: 500; padding: 4px 8px 4px 4px; }
  .step .n { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; font-size: var(--fs-12); font-weight: 600;
    background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line-strong); }
  .step.done .n { background: var(--ok); color: var(--surface); box-shadow: none; }
  .step.cur { color: var(--text); }
  .step.cur .n { background: var(--primary); color: #fff; box-shadow: none; }
  .stepper .ln { flex: 0 1 48px; min-width: 16px; height: 1px; background: var(--line-strong); }

  .done-card { display: flex; align-items: flex-start; gap: var(--sp-5); padding: var(--sp-5) var(--sp-6); }
  .done-card + .done-card { border-top: 1px solid var(--line); }
  .done-card .k { width: 150px; flex: none; color: var(--text-3); font-size: var(--fs-12); line-height: 20px; }
  .done-card .v { flex: 1; min-width: 0; line-height: 20px; }
  .done-card .v b { font-weight: 600; }
  .map { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: var(--fs-12); color: var(--text-3); margin-top: 2px; line-height: 16px; }
  .banner.inline { margin-top: var(--sp-4); align-items: center; }
  .types { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--sp-4); }

  .pv-head { display: flex; align-items: center; gap: var(--sp-5); flex-wrap: wrap; margin: var(--sp-4) 0 var(--sp-4); }
  .h2 { font: 600 var(--fs-13)/18px var(--font); }
  .counts { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
  .readonly { display: inline-flex; align-items: center; gap: 6px; font-size: var(--fs-12); color: var(--text-3); }
  .running { margin-bottom: var(--sp-5); align-items: center; }
  .pv { background: var(--surface); border-radius: var(--r-lg); box-shadow: var(--e1); }
  .pv .table th { position: sticky; top: var(--toolbar); z-index: 2; background: var(--surface); }
  .pv .table thead th:first-child { border-top-left-radius: var(--r-lg); }
  .pv .table thead th:last-child { border-top-right-radius: var(--r-lg); }
  .pv .table td { height: 40px; }
  .pv .c, .pv th:first-child { width: 44px; padding-right: 0; }
  .pv .a { width: 1%; white-space: nowrap; }
  .c-type { width: 40px; }
  .ttl { max-width: 0; width: 100%; }
  .ttl > div { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tt { font-weight: 500; }
  .flag { font-size: 11.5px; color: var(--text-3); display: block; white-space: normal; }
  .flag.warn { color: var(--warn); }
  .pv tr.skip td { color: var(--text-3); }
  .pv tr.skip .tt { font-weight: 400; }
  .c-key { white-space: nowrap; width: 90px; text-align: right; }
  .ticon { width: 18px; height: 18px; border-radius: 4px; display: grid; place-items: center; font: 700 10px/1 var(--font); color: #fff; }
  .ticon.epic { background: #7A5AC8; } .ticon.story { background: #3F8A55; } .ticon.subtask { background: #3F7DC0; } .ticon.nfr { background: #1F6770; }
  .pushbar { position: sticky; bottom: 0; z-index: 5; display: flex; align-items: center; gap: var(--sp-6); padding: var(--sp-5) var(--sp-6);
    background: color-mix(in srgb, var(--surface) 90%, transparent); backdrop-filter: blur(12px); border-top: 1px solid var(--line);
    border-radius: 0 0 var(--r-lg) var(--r-lg); }
  .pushbar p { flex: 1; font-size: var(--fs-12); color: var(--text-3); min-width: 0; }
  .result { margin-top: var(--sp-6); overflow: hidden; }
  .res-h { padding: var(--sp-5) var(--sp-6); border-bottom: 1px solid var(--line); }
  .result .table td { height: 38px; }
  .result .c-key { text-align: left; }
  .failed { padding: var(--sp-5) var(--sp-6); border-top: 1px solid var(--line); }
  .failed ul { margin: var(--sp-2) 0 var(--sp-4); padding-left: 18px; }
  a.mono { color: var(--accent); }
  @media (max-width: 960px) {
    .pv .c-key { display: none; }
    .done-card { flex-wrap: wrap; }
    .done-card .k { width: 100%; }
  }
</style>
