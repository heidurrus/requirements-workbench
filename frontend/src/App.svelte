<script>
  import Rail from "./components/Rail.svelte";
  import Toast from "./components/Toast.svelte";
  import Sources from "./screens/Sources.svelte";
  import Transcript from "./screens/Transcript.svelte";
  import Settings from "./screens/Settings.svelte";
  import Atoms from "./screens/Atoms.svelte";
  import DocumentScreen from "./screens/Document.svelte";
  import Skills from "./screens/Skills.svelte";
  import Backlog from "./screens/Backlog.svelte";
  import Export from "./screens/Export.svelte";
  import { api, setProgressTranslator } from "./lib/api.js";
  import { progressText } from "./lib/progress.js";
  import { app, t, loadProjects, loadSources, setLang, applyTheme, setTheme, isDark, loadStatus, undoLast } from "./lib/state.svelte.js";

  let ready = $state(false);
  let error = $state("");

  applyTheme();
  setProgressTranslator(progressText);
  // The toolbar hairline appears only once the page has scrolled (HIG scroll edge).
  const onScroll = () => document.body.classList.toggle("scrolled", window.scrollY > 4);
  function onKey(e) {
    if ((e.metaKey || e.ctrlKey) && !e.shiftKey && (e.key === "z" || e.key === "Z")
        && !e.target.closest?.("input:not([type=checkbox]), textarea, [contenteditable]")) {
      if (undoLast()) e.preventDefault();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === "l" || e.key === "L")) {
      e.preventDefault();
      setTheme(isDark() ? "light" : "dark");
    }
  }
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

<svelte:window onscroll={onScroll} onkeydown={onKey} />

{#if error}
  <div class="boot-error note danger">{t("err.generic", { error })}</div>
{:else if ready}
  <div class="shell">
    <Rail />
    <main class="screen">
      {#if app.route.name === "transcript"}
        {#key app.route.id}<Transcript id={app.route.id} autoSummarize={app.route.summarize} focusSeg={app.route.seg} />{/key}
      {:else if app.route.name === "atoms"}
        <Atoms />
      {:else if app.route.name === "document"}
        <DocumentScreen />
      {:else if app.route.name === "backlog"}
        <Backlog />
      {:else if app.route.name === "export"}
        <Export />
      {:else if app.route.name === "skills"}
        <Skills />
      {:else if app.route.name === "settings"}
        <Settings />
      {:else}
        <Sources />
      {/if}
    </main>
  </div>
  <Toast />
{/if}

<style>
  .boot-error { margin: var(--s-6) auto; width: min(560px, 90vw); }
</style>
