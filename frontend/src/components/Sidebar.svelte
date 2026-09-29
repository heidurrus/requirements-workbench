<script>
  import { keyOf } from "../lib/keys.js";
  // Sidebar (redesign §3, §5.17): the project, the pipeline with its state in words, the project's
  // sources and documents one click away, running jobs, tools. A 60-px rail below 1180 px (⌘\).
  import Icon from "./Icon.svelte";
  import { api } from "../lib/api.js";
  import { app, t, go, currentProject, switchProject, loadProjects, toast, sidebarIsRail, toggleSidebar } from "../lib/state.svelte.js";

  let menuOpen = $state(false);
  let newName = $state("");
  let creating = $state(false);
  let query = $state("");
  let wrap = $state(null);

  const steps = [
    { key: "nav.sources", route: "sources", path: "/sources", icon: "sources" },
    { key: "nav.atoms", route: "atoms", path: "/atoms", icon: "atoms" },
    { key: "nav.document", route: "document", path: "/document", icon: "doc" },
    { key: "nav.decomposition", route: "backlog", path: "/backlog", icon: "tree" },
    { key: "nav.export", route: "export", path: "/export", icon: "export" },
  ];

  // A transcript is a detail of a source, not a stage (PM-09): Sources stays lit while one is open.
  const current = $derived(app.route.name === "transcript" ? "sources" : app.route.name);
  const rail = $derived(sidebarIsRail());

  // Where each step stands: a ring (empty, in progress, stale, done) and the state in words.
  // Staleness flows downstream (PM-03): a changed requirement turns documents, backlog and Jira amber.
  function stage(route) {
    const s = app.status;
    const none = { ring: "", p: 0, text: "", kind: "" };
    if (!s) return none;
    if (route === "sources") {
      if (!s.sources) return none;
      if (s.processing) return { ring: "active", p: 50, text: t("nav.st.processing", { n: s.processing }), kind: "todo" };
      return { ring: "done", p: 100, text: String(s.sources), kind: "" };
    }
    if (route === "atoms") {
      const a = s.atoms;
      if (!a.total) return none;
      if (a.review) return { ring: "active", p: Math.round(100 * (a.total - a.review) / a.total), text: t("nav.st.review", { n: a.review }), kind: "todo" };
      if (a.conflicts) return { ring: "stale", p: 100, text: t("nav.st.conflicts", { n: a.conflicts }), kind: "warn" };
      return { ring: "done", p: 100, text: String(a.accepted), kind: "" };
    }
    if (route === "document") {
      const d = s.document;
      if (!d.version) return none;
      if (d.stale || d.others_stale) return { ring: "stale", p: 100, text: t("nav.st.stale"), kind: "warn" };
      if (d.status === "approved") return { ring: "done", p: 100, text: t("nav.st.approved"), kind: "ok" };
      return { ring: "active", p: d.status === "review" ? 66 : 33, text: "v" + d.version, kind: "" };
    }
    if (route === "backlog") {
      const b = s.backlog;
      if (!b.items) return none;
      if (b.stale) return { ring: "stale", p: 100, text: t("nav.st.stale"), kind: "warn" };
      return { ring: "active", p: 100, text: t("nav.st.items", { n: b.included }), kind: "" };
    }
    if (route === "export") {
      const e = s.export;
      if (!e.pushed) return none;
      const total = e.pushed + e.pending;
      if (e.stale || e.orphans) return { ring: "stale", p: Math.round(100 * e.pushed / total), text: t("nav.st.of", { a: e.pushed, b: total }), kind: "warn" };
      return { ring: "done", p: 100, text: t("nav.st.of", { a: e.pushed, b: total }), kind: "ok" };
    }
    return none;
  }

  let tall = $state(typeof window !== "undefined" ? window.innerHeight : 900);
  const recent = $derived([...app.sources].sort((a, b) => (b.created_at || 0) - (a.created_at || 0)).slice(0, tall >= 1000 ? 5 : 3));
  const showChildren = $derived(tall >= 700);

  function monogram(name) {
    const words = (name || "?").trim().split(/\s+/).filter(Boolean);
    return ((words[0] || "?")[0] + (words[1] ? words[1][0] : "")).toUpperCase();
  }

  // Running work: transcription and extraction by source, plus what screens register in app.work.
  const jobs = $derived.by(() => {
    const name = id => app.sources.find(s => s.id === id)?.title || "";
    const list = [];
    for (const [id, j] of Object.entries(app.jobs)) list.push({ key: "t" + id, title: t("job.transcribing", { name: name(id) }), ...j, path: `/source/${id}` });
    for (const [id, j] of Object.entries(app.extracting)) list.push({ key: "x" + id, title: t("job.extracting", { name: name(id) }), ...j, path: `/atoms/source/${id}` });
    for (const [key, j] of Object.entries(app.work || {})) list.push({ key, ...j });
    return list;
  });

  function onKey(e) {
    const key = keyOf(e);
    if (key === "Escape" && menuOpen) { menuOpen = false; return; }
    if (!(e.metaKey || e.ctrlKey) || e.altKey) return;
    if (key === "\\") { e.preventDefault(); toggleSidebar(); return; }
    if (key === ",") { e.preventDefault(); go("/settings"); return; }
    if (e.shiftKey && (key === "p" || key === "P")) { e.preventDefault(); menuOpen = !menuOpen; return; }
    if (key === "0" && !e.shiftKey) { e.preventDefault(); go("/overview"); return; }
    const n = Number(key);
    if (n >= 1 && n <= steps.length && !e.shiftKey) { e.preventDefault(); go(steps[n - 1].path); }
  }
  function onDoc(e) { if (menuOpen && wrap && !wrap.contains(e.target)) menuOpen = false; }

  async function createProject(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    creating = true;
    try {
      const p = await api("/api/projects", { method: "POST", body: { name: newName.trim() } });
      newName = "";
      await loadProjects();
      await switchProject(p.id);
      menuOpen = false;
    } catch (err) {
      toast(err.message, { kind: "danger" });
    } finally {
      creating = false;
    }
  }

  let importInput = $state(null);
  async function importProject(e) {
    const f = e.currentTarget.files[0];
    e.currentTarget.value = "";
    if (!f) return;
    const form = new FormData();
    form.append("file", f);
    try {
      const p = await api("/api/projects/import", { method: "POST", form });
      await loadProjects();
      await switchProject(p.id);
      menuOpen = false;
      toast(t("project.imported", { name: p.name }));
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function pick(id) {
    menuOpen = false;
    if (id !== app.currentProjectId) await switchProject(id);
  }
  const shown = $derived(app.projects.filter(p => p.name.toLowerCase().includes(query.trim().toLowerCase())));
  const device = $derived(app.device?.cuda || app.device?.mps ? (app.device.gpu_name || "GPU") : null);
  const mod = typeof navigator !== "undefined" && /Mac/.test(navigator.platform) ? "⌘" : "Ctrl+";
</script>

<svelte:window onkeydown={onKey} onresize={() => (tall = window.innerHeight)} />
<svelte:document onmousedown={onDoc} />

<nav class="rail sidebar" class:collapsed={rail} aria-label="Main">
  <div class="proj-wrap" bind:this={wrap}>
    <button class="proj" onclick={() => (menuOpen = !menuOpen)} aria-expanded={menuOpen} aria-haspopup="menu"
            title={`${t("project.label")}: ${currentProject()?.name || ""} · ${t("project.switch")} · ${mod}⇧P`}>
      <span class="proj-mark">{monogram(currentProject()?.name)}</span>
      <span class="proj-txt lbl">
        <b class="trunc">{currentProject()?.name || "…"}</b>
        {#if currentProject()?.local_only}
          <span class="lock"><Icon name="lock" size={12} /> {t("project.local_only")}</span>
        {:else}
          <span><Icon name="cloud" size={12} /> {t("project.cloud_ok")}</span>
        {/if}
      </span>
      <span class="lbl t3"><Icon name="updown" size={12} /></span>
    </button>
    {#if menuOpen}
      <div class="menu" role="menu">
        {#if app.projects.length > 6}
          <div class="search find"><Icon name="search" size={14} />
            <!-- svelte-ignore a11y_autofocus -->
            <input bind:value={query} placeholder={t("project.find")} aria-label={t("project.find")} autofocus /></div>
        {/if}
        {#each shown as p (p.id)}
          <button class="menu-item" role="menuitem" class:on={p.id === app.currentProjectId} onclick={() => pick(p.id)}>
            <span class="tick">{#if p.id === app.currentProjectId}<Icon name="check" size={12} />{/if}</span>
            <span class="grow trunc">{p.name}</span>
            {#if p.local_only}<Icon name="lock" size={12} />{/if}
          </button>
        {/each}
        <hr />
        <button class="menu-item import" role="menuitem" onclick={() => importInput.click()}>
          <span class="tick"></span><Icon name="upload" size={14} /> <span>{t("project.import")}</span></button>
        <input type="file" accept=".zip" class="hidden" bind:this={importInput} onchange={importProject} aria-label={t("project.import")} />
        <form class="menu-new" onsubmit={createProject}>
          <input class="input" bind:value={newName} placeholder={t("project.new_placeholder")} aria-label={t("project.new")} />
          <button class="btn sm primary" disabled={creating || !newName.trim()}>{t("project.create")}</button>
        </form>
      </div>
    {/if}
  </div>

  <button class="cmd" onclick={() => (app.palette = true)} title={rail ? `${t("shell.search")} · ${mod}K` : ""} aria-label={t("shell.search")}>
    <Icon name="search" size={14} /><span class="lbl grow trunc">{t("shell.search")}</span><span class="kbd lbl">{mod}K</span>
  </button>

  <div class="side-scroll scroll">
    <div class="nav">
      <button class="nav-row" aria-current={current === "overview" ? "page" : undefined} onclick={() => go("/overview")}
              title={rail ? t("nav.overview") : ""}>
        <Icon name="home" /><span class="lbl grow trunc">{t("nav.overview")}</span>
      </button>
    </div>

    <div class="nav-label lbl">{t("nav.pipeline")}</div>
    <div class="nav">
      {#each steps as s, i (s.route)}
        {@const st = stage(s.route)}
        <button class="nav-row" aria-current={current === s.route ? "page" : undefined} onclick={() => go(s.path)}
                title={rail ? `${t(s.key)}${st.text ? " · " + st.text : ""} · ${mod}${i + 1}` : `${mod}${i + 1}`}>
          <span class="ring {st.ring}" style="--p: {st.p}"></span>
          <span class="lbl grow trunc">{t(s.key)}</span>
          {#if st.text}<span class="count lbl num {st.kind}">{st.text}</span>{/if}
        </button>
        {#if showChildren && s.route === "sources"}
          {#each recent as src (src.id)}
            <button class="nav-row child" aria-current={app.route.name === "transcript" && app.route.id === src.id ? "page" : undefined}
                    onclick={() => go(`/source/${src.id}`)} title={src.title}>
              <span class="grow trunc">{src.title}</span>
              {#if app.jobs[src.id] || app.extracting[src.id] || src.status === "processing"}<span class="spinner"></span>
              {:else if src.status === "failed"}<span class="dot danger"></span>{/if}
            </button>
          {/each}
        {:else if showChildren && s.route === "document"}
          {#each app.documents.filter(d => d.version) as d (d.id)}
            <button class="nav-row child" aria-current={app.route.name === "document" && app.route.doc === d.id ? "page" : undefined}
                    onclick={() => go(`/document/${d.id}`)} title={d.title}>
              <span class="grow trunc">{d.short} · v{d.version}</span>
              {#if d.stale}<span class="dot warn" title={t("nav.st.stale")}></span>
              {:else if d.status === "approved"}<span class="dot ok" title={t("nav.st.approved")}></span>{/if}
            </button>
          {/each}
        {/if}
      {/each}
    </div>
  </div>

  <div class="side-foot">
    {#each jobs.slice(0, 1) as j (j.key)}
      <button class="job" onclick={() => j.path && go(j.path)} title={j.title}>
        <span class="job-title"><span class="spinner"></span><span class="trunc">{j.title}</span></span>
        <span class="progress"><i style="width: {j.progress || 0}%"></i></span>
        <span class="job-sub num"><span class="trunc">{Math.round(j.progress || 0)}%{#if j.message} · {j.message}{/if}{#if j.eta} · {j.eta}{/if}</span>
          {#if jobs.length > 1}<span>{t("job.queue", { n: jobs.length - 1 })}</span>{/if}</span>
      </button>
    {/each}
    <div class="nav">
      <button class="nav-row" aria-current={app.route.name === "skills" ? "page" : undefined} onclick={() => go("/skills")}
              title={rail ? t("nav.skills") : ""}>
        <Icon name="skills" /><span class="lbl grow trunc">{t("nav.skills")}</span>
      </button>
      <button class="nav-row" aria-current={app.route.name === "settings" ? "page" : undefined} onclick={() => go("/settings")}
              title={rail ? `${t("nav.settings")} · ${mod},` : `${mod},`}>
        <Icon name="gear" /><span class="lbl grow trunc">{t("nav.settings")}</span>
      </button>
    </div>
    <p class="about lbl trunc" title={device || t("nav.cpu")}>
      <span class="dot" class:ok={!!device}></span>
      {device || "CPU"}{#if app.health?.version} · v{app.health.version}{/if}
    </p>
  </div>
</nav>

<style>
  .sidebar { display: flex; flex-direction: column; min-width: 0; min-height: 0; height: 100vh;
    background: var(--c-sidebar); -webkit-backdrop-filter: var(--blur-sidebar); backdrop-filter: var(--blur-sidebar);
    border-right: 1px solid var(--c-line); padding: var(--s-5) var(--s-4) var(--s-4); position: relative; z-index: 30; }
  .proj-wrap { position: relative; }
  .proj { display: flex; align-items: center; gap: var(--s-4); width: 100%; height: 44px; padding: 0 var(--s-4);
    border: 0; background: none; border-radius: var(--r-md); text-align: left; cursor: pointer;
    transition: background var(--d-fast) var(--ease-out); }
  .proj:hover { background: var(--c-fill-1); } .proj:active { background: var(--c-fill-2); }
  .proj-mark { width: 28px; height: 28px; border-radius: 7px; background: var(--c-text); color: var(--c-content); display: grid; place-items: center;
    font: var(--w-semibold) 11px/1 var(--font); letter-spacing: .02em; flex: none; }
  .proj-txt { min-width: 0; flex: 1; display: grid; }
  .proj-txt b { font-weight: var(--w-semibold); letter-spacing: -.005em; }
  .proj-txt span { font-size: var(--t-foot); line-height: var(--lh-foot); color: var(--c-text-3); display: flex; align-items: center; gap: var(--s-2); }
  .proj-txt .lock { color: var(--c-ok); }
  .menu { left: 0; top: calc(100% + var(--s-2)); width: max(100%, 264px); }
  .find { margin: var(--s-2) var(--s-2) var(--s-3); }
  .menu-new { display: flex; gap: var(--s-3); padding: var(--s-3) var(--s-2) var(--s-2); }
  .menu-new .input { height: var(--h-ctl-sm); font-size: var(--t-foot); }

  .cmd { display: flex; align-items: center; gap: var(--s-4); height: var(--h-ctl); margin: var(--s-4) var(--s-2) var(--s-5); padding: 0 var(--s-4);
    border: 0; border-radius: var(--r-sm); background: var(--c-fill-2); color: var(--c-text-3); text-align: left; cursor: pointer;
    transition: background var(--d-fast) var(--ease-out); flex: none; }
  .cmd:hover { background: var(--c-fill-3); }
  .cmd .kbd { background: none; color: var(--c-text-3); }

  .side-scroll { flex: 1; min-height: 0; margin: 0 calc(var(--s-4) * -1); padding: 0 var(--s-4); }
  .nav { display: flex; flex-direction: column; gap: 1px; }
  .nav-label { font: var(--w-medium) var(--t-caption)/var(--lh-caption) var(--font); letter-spacing: .01em; color: var(--c-text-3);
    padding: var(--s-6) var(--s-4) var(--s-3); }
  .nav-row { display: flex; align-items: center; gap: var(--s-4); height: var(--h-row); padding: 0 var(--s-4); width: 100%; flex: none;
    border: 0; background: none; border-radius: var(--r-sm); text-align: left; color: var(--c-text); cursor: pointer;
    transition: background var(--d-fast) var(--ease-out); }
  .nav-row:hover { background: var(--c-fill-1); }
  .nav-row:active { background: var(--c-fill-2); }
  .nav-row:focus-visible { box-shadow: var(--ring-inset); }
  .nav-row[aria-current="page"] { background: var(--c-fill-2); font-weight: var(--w-semibold); }
  .nav-row :global(svg) { color: var(--c-text-2); }
  .nav-row[aria-current="page"] :global(svg) { color: var(--c-accent-text); }
  .count { color: var(--c-text-3); font-size: var(--t-foot); font-weight: var(--w-regular); white-space: nowrap; }
  .count.todo { color: var(--c-accent-text); font-weight: var(--w-semibold); }
  .count.warn { color: var(--c-warn); font-weight: var(--w-medium); }
  .count.ok { color: var(--c-ok); }
  .nav-row.child { height: 28px; padding-left: 32px; font-size: var(--t-foot); color: var(--c-text-2); gap: var(--s-3); }
  .nav-row.child[aria-current="page"] { color: var(--c-text); font-weight: var(--w-medium); }

  .side-foot { display: flex; flex-direction: column; gap: var(--s-4); padding-top: var(--s-4); flex: none; }
  .job { margin: 0 var(--s-2); padding: var(--s-5); border-radius: var(--r-md); background: var(--c-fill-1); border: 0; text-align: left;
    display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--s-3); cursor: pointer; }
  .job:hover { background: var(--c-fill-2); }
  .job-title { font-size: var(--t-foot); line-height: var(--lh-foot); font-weight: var(--w-medium); display: flex; gap: var(--s-3); align-items: center; min-width: 0; }
  .job-sub { font-size: var(--t-caption); line-height: var(--lh-caption); color: var(--c-text-3); display: flex; justify-content: space-between; gap: var(--s-4); min-width: 0; }
  .about { font-size: var(--t-caption); line-height: var(--lh-caption); color: var(--c-text-3); padding: 0 var(--s-4) var(--s-2);
    display: flex; align-items: center; gap: var(--s-3); }
  .about .dot { color: var(--c-line-control); } .about .dot.ok { color: var(--c-ok); }

  .collapsed { padding-left: var(--s-5); padding-right: var(--s-5); }
  .collapsed .lbl, .collapsed .nav-row.child, .collapsed .job { display: none; }
  .collapsed .nav-row { justify-content: center; padding: 0; height: 36px; }
  .collapsed .nav { gap: var(--s-2); }
  .collapsed .proj { padding: 0; justify-content: center; }
  .collapsed .cmd { justify-content: center; margin-inline: 0; padding: 0; }
  .collapsed .side-scroll { padding-top: var(--s-2); }
  @media (max-height: 699px) { .job { padding: var(--s-3) var(--s-5); } .job .progress, .job-sub { display: none; } }
</style>
