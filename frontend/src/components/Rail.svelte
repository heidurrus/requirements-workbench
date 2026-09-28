<script>
  // Sidebar: project switcher, the six pipeline steps with state badges, tools,
  // passive status in the footer. Collapses to an icon rail at ≤ 1120 px (⌘\).
  import Icon from "./Icon.svelte";
  import { api } from "../lib/api.js";
  import { app, t, go, currentProject, switchProject, loadProjects, toast, writePref } from "../lib/state.svelte.js";

  let menuOpen = $state(false);
  let newName = $state("");
  let creating = $state(false);

  const steps = [
    { key: "nav.sources", route: "sources", path: "/sources", icon: "sources" },
    { key: "nav.transcript", route: "transcript", path: null, icon: "transcript" },
    { key: "nav.atoms", route: "atoms", path: "/atoms", icon: "atoms" },
    { key: "nav.document", route: "document", path: "/document", icon: "doc" },
    { key: "nav.decomposition", route: "backlog", path: "/backlog", icon: "tree" },
    { key: "nav.export", route: "export", path: "/export", icon: "export" },
  ];

  function open(step) {
    if (step.route === "transcript") go(app.lastSourceId ? `/source/${app.lastSourceId}` : "/transcript");
    else go(step.path);
  }

  // One badge per step: todo (accent), warn, done (green check) or a plain count.
  function badge(route) {
    const s = app.status;
    if (!s) return null;
    if (route === "sources" && s.sources) return { text: String(s.sources) };
    if (route === "atoms" && s.atoms.review) return { kind: "todo", text: String(s.atoms.review),
                                                      title: t("nav.badge_review", { n: s.atoms.review }) };
    if (route === "document" && s.document.version)
      return s.document.stale ? { kind: "warn", text: "v" + s.document.version, title: t("nav.badge_stale") }
                              : { text: "v" + s.document.version };
    if (route === "backlog" && s.backlog.items)
      return s.backlog.stale ? { kind: "warn", text: String(s.backlog.included) } : { text: String(s.backlog.included) };
    if (route === "export" && s.export.pushed) return { kind: "done", text: "✓", title: t("nav.badge_pushed", { n: s.export.pushed }) };
    return null;
  }

  function monogram(name) {
    const words = (name || "?").trim().split(/\s+/).filter(Boolean);
    return ((words[0] || "?")[0] + (words[1] ? words[1][0] : "")).toUpperCase();
  }

  const narrow = typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(max-width: 1120px)") : null;
  let isNarrow = $state(narrow ? narrow.matches : false);
  narrow && narrow.addEventListener("change", e => { isNarrow = e.matches; });
  let collapsed = $derived(app.sidebarCollapsed === null ? isNarrow : app.sidebarCollapsed);
  $effect(() => { document.documentElement.classList.toggle("sb-collapsed", collapsed); });

  export function toggleSidebar() {
    app.sidebarCollapsed = !collapsed;
    writePref("sidebarCollapsed", app.sidebarCollapsed);
  }

  function onKey(e) {
    if (!(e.metaKey || e.ctrlKey) || e.altKey) return;
    if (e.key === "\\") { e.preventDefault(); toggleSidebar(); return; }
    if (e.key === ",") { e.preventDefault(); go("/settings"); return; }
    const n = Number(e.key);
    if (n >= 1 && n <= 6 && !e.shiftKey) { e.preventDefault(); open(steps[n - 1]); }
  }

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

  async function pick(id) {
    menuOpen = false;
    if (id !== app.currentProjectId) await switchProject(id);
  }

  const device = $derived(app.device?.cuda || app.device?.mps ? (app.device.gpu_name || "GPU") : null);
</script>

<svelte:window onkeydown={onKey} />

<nav class="rail" class:collapsed aria-label="Main">
  <div class="proj-wrap">
    <button class="proj" onclick={() => (menuOpen = !menuOpen)} aria-expanded={menuOpen} aria-haspopup="menu"
            title={`${t("project.label")}: ${currentProject()?.name || ""} · ${t("project.switch")}`}>
      <span class="proj-mark">{monogram(currentProject()?.name)}</span>
      <span class="proj-txt">
        <b>{currentProject()?.name || "…"}</b>
        {#if currentProject()?.local_only}
          <span class="lock"><Icon name="lock" size={12} /> {t("project.local_only")}</span>
        {:else}
          <span><Icon name="cloud" size={12} /> {t("project.cloud_ok")}</span>
        {/if}
      </span>
      <span class="lbl-only faint"><Icon name="chevd" size={14} /></span>
    </button>
    {#if menuOpen}
      <div class="menu" role="menu">
        {#each app.projects as p (p.id)}
          <button class="menu-item" role="menuitem" class:on={p.id === app.currentProjectId} onclick={() => pick(p.id)}>
            <span>{p.name}</span>
            {#if p.local_only}<Icon name="lock" size={12} />{/if}
          </button>
        {/each}
        <form class="menu-new" onsubmit={createProject}>
          <input class="input" bind:value={newName} placeholder={t("project.new_placeholder")} aria-label={t("project.new")} />
          <button class="btn btn-sm btn-primary" disabled={creating || !newName.trim()}>{t("project.create")}</button>
        </form>
      </div>
    {/if}
  </div>

  <div class="nav-label">{t("nav.pipeline")}</div>
  <div class="nav">
    {#each steps as s, i (s.route)}
      {@const b = badge(s.route)}
      <button class="navitem" aria-current={app.route.name === s.route ? "page" : undefined} onclick={() => open(s)}
              title={collapsed ? `${t(s.key)} · ⌘${i + 1}` : `⌘${i + 1}`}>
        <span class="step-ico"><Icon name={s.icon} /></span>
        <span class="lbl">{t(s.key)}</span>
        {#if b}<span class="badge {b.kind || ''}" title={b.title || ""}>{b.text}</span>{/if}
      </button>
    {/each}
  </div>

  <div class="nav-label">{t("nav.tools")}</div>
  <div class="nav-sep" aria-hidden="true"></div>
  <div class="nav">
    <button class="navitem" aria-current={app.route.name === "skills" ? "page" : undefined} onclick={() => go("/skills")}
            title={collapsed ? t("nav.skills") : ""}>
      <span class="step-ico"><Icon name="skills" /></span><span class="lbl">{t("nav.skills")}</span>
    </button>
    <button class="navitem" aria-current={app.route.name === "settings" ? "page" : undefined} onclick={() => go("/settings")}
            title={collapsed ? `${t("nav.settings")} · ⌘,` : "⌘,"}>
      <span class="step-ico"><Icon name="gear" /></span><span class="lbl">{t("nav.settings")}</span>
    </button>
  </div>

  <div class="foot">
    <div class="foot-row" title={device || t("nav.cpu")}>
      <span class="status-dot" class:cpu={!device}></span><span class="txt">{device || "CPU"}</span>
    </div>
    <div class="foot-row txt">
      <span>{t("app.name")}{#if app.health?.version} · <span class="num">v{app.health.version}</span>{/if}</span>
    </div>
    <button class="btn btn-ghost icon-btn btn-sm toggle" onclick={toggleSidebar} aria-label={t("nav.toggle")} title={`${t("nav.toggle")} · ⌘\\`}>
      <Icon name="sidebar" size={14} />
    </button>
  </div>
</nav>

<style>
  .rail { position: sticky; top: 0; height: 100vh; overflow-y: auto; background: var(--sidebar); border-right: 1px solid var(--line);
    display: flex; flex-direction: column; padding: var(--sp-5) var(--sp-4); gap: var(--sp-2); z-index: 30; }
  @supports (backdrop-filter: blur(1px)) {
    .rail { background: color-mix(in srgb, var(--sidebar) 88%, transparent); backdrop-filter: blur(24px) saturate(1.4); }
  }
  .proj-wrap { position: relative; margin-bottom: var(--sp-2); }
  .proj { display: flex; align-items: center; gap: var(--sp-4); width: 100%; padding: var(--sp-3) var(--sp-4); border: 0;
    background: transparent; border-radius: var(--r-md); text-align: left; cursor: pointer; }
  .proj:hover { background: var(--surface-3); }
  .proj-mark { width: 28px; height: 28px; border-radius: 7px; background: var(--primary); color: #fff; display: grid; place-items: center;
    font-weight: 600; font-size: var(--fs-12); flex: none; }
  .proj-txt { min-width: 0; flex: 1; }
  .proj-txt b { display: block; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .proj-txt span { display: flex; align-items: center; gap: 4px; font-size: var(--fs-11); line-height: 14px; color: var(--text-3); }
  .proj-txt .lock { color: var(--ok); }
  .menu { position: absolute; z-index: 50; left: 0; width: max(100%, 232px); top: calc(100% + var(--sp-2)); background: var(--surface);
    border-radius: var(--r-md); box-shadow: var(--e2); padding: var(--sp-2); }
  .menu-item { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-4); width: 100%;
    padding: var(--sp-3) var(--sp-4); border: 0; background: none; border-radius: var(--r-sm); cursor: pointer; text-align: left; }
  .menu-item:hover, .menu-item.on { background: var(--surface-2); }
  .menu-item.on { font-weight: 600; }
  .menu-new { display: flex; gap: var(--sp-2); padding: var(--sp-4) var(--sp-2) var(--sp-2); border-top: 1px solid var(--line); margin-top: var(--sp-2); }
  .menu-new .input { height: 24px; font-size: var(--fs-12); }

  .nav-label { font-size: var(--fs-11); font-weight: 600; color: var(--text-3); padding: var(--sp-5) var(--sp-4) var(--sp-2); }
  .nav-sep { display: none; }
  .nav { display: flex; flex-direction: column; gap: 1px; }
  .navitem { display: flex; align-items: center; gap: var(--sp-4); height: 30px; padding: 0 var(--sp-4); border-radius: var(--r-sm);
    border: 0; background: none; width: 100%; text-align: left; color: var(--text-2); font-weight: 500; cursor: pointer; position: relative; }
  .navitem:hover { background: var(--surface-3); color: var(--text); }
  .navitem[aria-current="page"] { background: var(--surface); color: var(--text); box-shadow: var(--e1); }
  .navitem[aria-current="page"] .step-ico { color: var(--accent); }
  .step-ico { width: 20px; display: grid; place-items: center; color: var(--text-3); flex: none; }
  .lbl { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .badge { font-size: var(--fs-11); line-height: 16px; min-width: 18px; padding: 0 5px; border-radius: var(--r-full); text-align: center;
    color: var(--text-3); font-variant-numeric: tabular-nums; }
  .badge.todo { background: var(--accent-bg); color: var(--accent); font-weight: 600; }
  .badge.warn { background: var(--warn-bg); color: var(--warn); font-weight: 600; }
  .badge.done { color: var(--ok); }

  .foot { margin-top: auto; padding: var(--sp-4); font-size: var(--fs-11); color: var(--text-3); display: flex; flex-direction: column;
    gap: var(--sp-2); position: relative; }
  .foot-row { display: flex; align-items: center; gap: 6px; min-width: 0; }
  .foot-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ok); flex: none; }
  .status-dot.cpu { background: var(--line-control); }
  .toggle { position: absolute; right: 0; bottom: var(--sp-3); color: var(--text-3); }

  .rail.collapsed { padding: var(--sp-5) var(--sp-3); align-items: center; }
  .rail.collapsed .lbl, .rail.collapsed .proj-txt, .rail.collapsed .lbl-only, .rail.collapsed .nav-label,
  .rail.collapsed .txt { display: none; }
  .rail.collapsed .nav-sep { display: block; width: 28px; height: 1px; background: var(--line-strong); margin: var(--sp-4) 0; }
  .rail.collapsed .proj { justify-content: center; padding: 6px; width: auto; }
  .rail.collapsed .navitem { width: 40px; height: 36px; justify-content: center; padding: 0; }
  .rail.collapsed .badge { position: absolute; top: 3px; right: 2px; min-width: 8px; height: 8px; padding: 0; font-size: 0; }
  .rail.collapsed .badge:not(.todo):not(.warn) { display: none; }
  .rail.collapsed .badge.todo { background: var(--accent); }
  .rail.collapsed .badge.warn { background: var(--warn); }
  .rail.collapsed .foot { align-items: center; padding: 0 0 var(--sp-2); }
  .rail.collapsed .toggle { position: static; }

  @media (max-width: 720px) {
    .rail, .rail.collapsed { position: static; height: auto; flex-direction: row; flex-wrap: wrap; align-items: center; border-right: 0;
      border-bottom: 1px solid var(--line); padding: var(--sp-4); }
    .rail .nav { flex-direction: row; overflow-x: auto; }
    .rail .nav-label, .rail .nav-sep, .rail .foot { display: none; }
    .rail .navitem { width: auto; }
    .rail .lbl { display: inline; }
  }
</style>
