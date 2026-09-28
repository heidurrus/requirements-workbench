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
  const actionTag = { create: "ok", update: "accent", unchanged: "", skip: "", blocked: "danger" };
  const indent = { epic: 0, story: 1, nfr: 1, subtask: 2 };
</script>

<div class="screen-inner">
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("jr.title")}</h1>
      <p class="screen-sub">
        {#if target}{[target.project_key, target.project_name, target.site_url.replace("https://", "")].filter(Boolean).join(" · ")}
        {:else}{t("jr.sub_empty")}{/if}
      </p>
    </div>
    <span class="tag">Jira · MCP</span>
  </header>

  <div class="stack">
    <!-- 1. connection -->
    <section class="panel step">
      <div class="step-head">
        <span class="num">1</span>
        <p class="panel-title">{t("jr.account")}</p>
        <span class="spacer"></span>
        {#if connected}<span class="tag ok">{t("jr.is_connected")}</span>
          <button class="btn btn-sm btn-ghost" onclick={disconnect}>{t("jr.disconnect")}</button>
        {/if}
      </div>
      {#if connected && sites.length}
        <p class="hint">{t("jr.access", { sites: sites.map(s => s.url.replace("https://", "")).join(", ") })}</p>
        {#if target && !sites.some(s => s.cloud_id === target.cloud_id)}
          <p class="note danger">{t("jr.target_not_visible", { site: target.site_url.replace("https://", "") })}</p>
        {:else}
          <p class="hint">{t("jr.wrong_account")}</p>
        {/if}
      {/if}
      {#if connected === false}
        <p class="panel-desc">{t("jr.connect_hint")}</p>
        <div class="actions">
          <button class="btn btn-primary" disabled={waiting} onclick={() => connect(true)}>
            {#if waiting}<span class="spinner"></span> {t("jr.waiting")}{:else}{t("jr.connect")}{/if}</button>
          {#if !waiting}<button class="btn btn-ghost btn-sm" onclick={() => connect(false)}>{t("jr.normal_window")}</button>{/if}
        </div>
        {#if privateNote}<p class="hint" style="margin-top: var(--s-2)">{privateNote}</p>{/if}
      {/if}
    </section>

    <!-- 2. target -->
    {#if connected}
      <section class="panel step">
        <div class="step-head">
          <span class="num">2</span>
          <p class="panel-title">{t("jr.target")}</p>
          <span class="spacer"></span>
          {#if target && !editingTarget}<button class="btn btn-sm btn-ghost" onclick={() => { editingTarget = true; loadSites(); }}>{t("jr.change")}</button>{/if}
        </div>
        {#if target && !editingTarget}
          <p class="target-line"><b>{target.project_key}</b>{target.project_name ? " · " + target.project_name : ""}
            <span class="faint">{" · " + target.site_url}</span></p>
          <p class="hint">{KINDS.map(k => `${t("bl.kind." + k)} → ${target.types?.[k] || "—"}`).join(" · ")}</p>
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
            <div class="field" style="margin-top: var(--s-3)">
              <label class="label" for="jr-project">{t("jr.project")}</label>
              <select class="select" id="jr-project" value={pick.project_key} onchange={e => chooseProject(e.currentTarget.value)}>
                <option value="" disabled>{t("jr.choose_project")}</option>
                {#each projects as p (p.key)}<option value={p.key}>{p.key} · {p.name}</option>{/each}
              </select>
            </div>
          {/if}
          {#if chosenProject}
            <p class="label" style="margin-top: var(--s-3)">{t("jr.types")}</p>
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
          <div class="actions" style="margin-top: var(--s-3)">
            <button class="btn btn-primary" disabled={!pick.project_key} onclick={saveTarget}>{t("at.save")}</button>
            {#if target}<button class="btn btn-ghost" onclick={() => (editingTarget = false)}>{t("at.cancel")}</button>{/if}
          </div>
        {/if}
      </section>
    {/if}

    <!-- 3. preview and push -->
    {#if connected && target && !editingTarget}
      <section class="panel step">
        <div class="step-head">
          <span class="num">3</span>
          <p class="panel-title">{t("jr.preview")}</p>
          <span class="spacer"></span>
          <button class="btn" class:btn-primary={!preview} disabled={!!busy} onclick={runPreview}>
            {preview ? t("jr.refresh") : t("jr.show_preview")}</button>
        </div>
        <p class="panel-desc">{t("jr.no_writes")}</p>
        {#if busy}
          <div class="running"><span class="spinner"></span><div class="grow"><div class="bar"><i style="width: {busy.progress}%"></i></div></div>
            <span class="mono faint">{busy.message}</span></div>
        {/if}
        {#if preview}
          <div class="counts">
            {#each ["create", "update", "unchanged", "skip", "blocked"] as a (a)}
              {#if preview.counts[a]}<span class="tag {actionTag[a]}">{t("jr.action." + a)}: {preview.counts[a]}</span>{/if}
            {/each}
          </div>
          <table class="rows"><tbody>
            {#each preview.rows as r (r.item_id)}
              <tr class:dim={["skip", "blocked", "unchanged"].includes(r.action) && !selected[r.item_id]}>
                <td class="c"><input type="checkbox" disabled={!["create", "update", "unchanged"].includes(r.action)}
                                     bind:checked={selected[r.item_id]} aria-label={r.title} /></td>
                <td class="a"><span class="tag {actionTag[r.action]}">{t("jr.action." + r.action)}</span></td>
                <td class="k"><span class="tag">{t("bl.kind." + r.kind)}</span></td>
                <td class="ti" style="padding-left: calc({indent[r.kind]} * var(--s-4))">
                  {r.title}
                  {#if r.kind === "subtask" && r.parent_title}<span class="faint">{" ← " + r.parent_title}</span>{/if}
                  {#if r.reason}<span class="hint"> — {t("jr.reason." + r.reason)}</span>{/if}
                  {#each r.flags as f (f)}<span class="tag {f === 'changed_in_jira' ? 'warn' : ''}">{t("jr.flag." + f)}</span>{/each}
                </td>
                <td class="key">{#if r.key}<a href={r.url} target="_blank" rel="noreferrer" class="mono">{r.key}</a>{/if}</td>
              </tr>
            {/each}
          </tbody></table>
          <div class="foot">
            <span class="hint">{t("jr.target_note", { key: target.project_key })}</span>
            {#if !confirming}
              <button class="btn btn-primary" disabled={!pushable.length || !!busy} onclick={() => (confirming = true)}>
                {pushable.length ? t("jr.push", { n: pushable.length }) : t("jr.nothing")}</button>
            {/if}
          </div>
          {#if confirming}
            <div class="note warn confirm">
              <span>{t("jr.confirm", { n: pushable.length, key: target.project_key, site: target.site_url.replace("https://", "") })}</span>
              <span class="actions">
                <button class="btn btn-sm btn-ghost" onclick={() => (confirming = false)}>{t("at.cancel")}</button>
                <button class="btn btn-sm btn-primary" onclick={() => push()}>{t("jr.confirm_yes", { key: target.project_key })}</button>
              </span>
            </div>
          {/if}
        {/if}

        {#if result}
          <div class="result">
            <p class="label">{t("jr.result", { n: result.done.length })}</p>
            <ul>
              {#each result.done as d (d.item_id)}
                <li><span class="tag ok">{t("jr.did." + d.action)}</span> <a href={d.url} target="_blank" rel="noreferrer" class="mono">{d.key}</a> {d.title}</li>
              {/each}
            </ul>
            {#if result.failed.length}
              <p class="label danger-text">{t("jr.failed", { n: result.failed.length })}</p>
              <ul>{#each result.failed as f (f.item_id)}<li><b>{f.title}</b> — <span class="faint">{f.error}</span></li>{/each}</ul>
              <button class="btn btn-sm" disabled={!!busy} onclick={() => push(result.failed.map(f => f.item_id))}>{t("jr.retry")}</button>
            {/if}
          </div>
        {/if}
      </section>
    {/if}

    <button class="btn btn-ghost back" onclick={() => go("/backlog")}>← {t("nav.decomposition")}</button>
  </div>
</div>

<style>
  .step-head { display: flex; align-items: center; gap: var(--s-2); margin-bottom: var(--s-2); }
  .num { width: 22px; height: 22px; border-radius: 50%; display: inline-grid; place-items: center; background: var(--sunk);
    font-family: var(--mono); font-size: var(--t-xs); color: var(--ink-2); flex: none; }
  .spacer { flex: 1; }
  .grow { flex: 1; }
  .target-line { font-size: var(--t-md); }
  .types { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--s-2); }
  .running { display: flex; align-items: center; gap: var(--s-3); margin: var(--s-2) 0; }
  .counts { display: flex; flex-wrap: wrap; gap: var(--s-2); margin: var(--s-2) 0 var(--s-3); }
  .rows { width: 100%; border-collapse: collapse; font-size: var(--t-sm); }
  .rows td { padding: 6px var(--s-2); border-top: 1px solid var(--rule); vertical-align: top; }
  .rows tr.dim td { color: var(--ink-3); }
  .rows .c { width: 24px; } .rows .a { width: 1%; white-space: nowrap; } .rows .k { width: 1%; }
  .rows .key { width: 1%; white-space: nowrap; text-align: right; }
  .rows .ti .tag { margin-left: var(--s-1); }
  .foot { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); margin-top: var(--s-3); flex-wrap: wrap; }
  .confirm { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); flex-wrap: wrap; margin-top: var(--s-3); }
  .result { margin-top: var(--s-4); border-top: 1px solid var(--rule); padding-top: var(--s-3); }
  .result ul { list-style: none; padding: 0; margin: var(--s-1) 0 var(--s-3); line-height: 1.8; font-size: var(--t-sm); }
  .danger-text { color: var(--danger); }
  .back { align-self: flex-start; }
  a.mono { color: var(--accent); }
</style>
