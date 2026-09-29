<script>
  import Sidebar from "./components/Sidebar.svelte";
  import CommandPalette from "./components/CommandPalette.svelte";
  import RecordingHud from "./components/RecordingHud.svelte";
  import Overview from "./screens/Overview.svelte";
  import Toast from "./components/Toast.svelte";
  import Sources from "./screens/Sources.svelte";
  import Transcript from "./screens/Transcript.svelte";
  import Settings from "./screens/Settings.svelte";
  import Atoms from "./screens/Atoms.svelte";
  import DocumentScreen from "./screens/Document.svelte";
  import Skills from "./screens/Skills.svelte";
  import Backlog from "./screens/Backlog.svelte";
  import Export from "./screens/Export.svelte";
  import { api, setProgressTranslator, setLangSource } from "./lib/api.js";
  import { progressText } from "./lib/progress.js";
  import { app, t, go, loadProjects, loadSources, setLang, applyTheme, setTheme, isDark, loadStatus, undoLast, sidebarIsRail, toggleInspector } from "./lib/state.svelte.js";

  let ready = $state(false);
  let error = $state("");

  applyTheme();
  setProgressTranslator(progressText);
  setLangSource(() => app.lang);
  // Screens rebuilt on panes; the others still scroll as one page inside the main area.
  const INSPECTOR = { transcript: "source", atoms: "atoms", document: "document", backlog: "backlog", skills: "skills", sources: "sources" };
  function onKey(e) {
    if ((e.metaKey || e.ctrlKey) && !e.shiftKey && (e.key === "z" || e.key === "Z")
        && !e.target.closest?.("input:not([type=checkbox]), textarea, [contenteditable]")) {
      if (undoLast()) e.preventDefault();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === "l" || e.key === "L")) {
      e.preventDefault();
      setTheme(isDark() ? "light" : "dark");
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.altKey && e.code === "KeyI" && INSPECTOR[app.route.name]) {
      e.preventDefault();
      toggleInspector(INSPECTOR[app.route.name]);
    }
  }
  // The empty address opens the overview, or Sources while the project has nothing in it.
  $effect(() => {
    if (ready && app.route.name === "home") go(app.sources.length ? "/overview" : "/sources");
  });
  $effect(() => { app.atomsVersion; loadStatus(); });

  async function boot() {
    setLang(app.lang);
    try {
      const [device, models, health] = await Promise.all([
        api("/device-info"), api("/models"), api("/health").catch(() => null)]);
      app.device = device;
      app.models = models;
      app.health = health;
      if (!models.includes(app.options.model)) app.options.model = models[0];
      if (app.options.device !== "cpu" && !device.cuda && !device.mps) app.options.device = "cpu";
      if (app.options.device === "cuda" && !device.cuda && device.mps) app.options.device = "mps";
      await loadProjects();
      await loadSources();
      ready = true;
    } catch (err) {
      error = err.message;
    }
  }
  boot();
</script>

<svelte:window onkeydown={onKey} />

{#if error}
  <div class="boot-error note danger">{t("err.generic", { error })}</div>
{:else if ready}
  <div class="app" class:rail-mode={sidebarIsRail()}>
    <Sidebar />
    <main class="main">
      {#if app.route.name === "overview"}
        <Overview />
      {:else if app.route.name === "atoms"}
        <Atoms />
      {:else if app.route.name === "sources"}
        <Sources />
      {:else if app.route.name === "transcript"}
        {#key app.route.id}<Transcript id={app.route.id} autoSummarize={app.route.summarize} focusSeg={app.route.seg} />{/key}
      {:else}
        <div class="legacy scroll">
          {#if app.route.name === "document"}
            <DocumentScreen />
          {:else if app.route.name === "backlog"}
            <Backlog />
          {:else if app.route.name === "export"}
            <Export />
          {:else if app.route.name === "skills"}
            <Skills />
          {:else if app.route.name === "settings"}
            <Settings />
          {/if}
        </div>
      {/if}
    </main>
  </div>
  <CommandPalette />
  <RecordingHud />
  <Toast />
{/if}

<style>
  .boot-error { margin: var(--sp-9) auto; width: min(560px, 90vw); }
</style>
