<script>
  // One screen = the window toolbar (title, status line, actions, one primary button) and the workspace under it.
  import Icon from "./Icon.svelte";
  import { app, t, go, toggleSidebar, toggleInspector, inspectorOn, setTheme, isDark } from "../lib/state.svelte.js";

  let { title = "", crumb = "", crumbPath = "", sub = "", inspector = "", heading, actions, children } = $props();
</script>

<header class="toolbar screen-head">
  <button class="btn ghost icon" onclick={toggleSidebar} aria-label={t("nav.toggle")} title={`${t("nav.toggle")} · ⌘\\`}>
    <Icon name="sidebar" /></button>
  {#if crumb}
    <button class="btn ghost icon" onclick={() => go(crumbPath)} aria-label={t("shell.back", { name: crumb })} title={t("shell.back", { name: crumb })}>
      <Icon name="back" /></button>
  {/if}
  <div class="tb-title">
    {#if heading}{@render heading()}
    {:else}
      <h1 class="screen-title">{#if crumb}<button class="tb-crumb" onclick={() => go(crumbPath)}>{crumb}</button><span class="tb-crumb">{" › "}</span>{/if}{title}</h1>
    {/if}
    {#if sub}<p class="screen-sub">{sub}</p>{/if}
  </div>
  <div class="tb-actions">
    {@render actions?.()}
    <span class="tb-sep"></span>
    <button class="btn ghost icon" onclick={() => setTheme(isDark() ? "light" : "dark")}
            aria-label={t("shell.theme")} title={`${t("shell.theme")} · ⌘⇧L`}>
      <Icon name={isDark() ? "sun" : "moon"} /></button>
    {#if inspector}
      <button class="btn ghost icon" class:on={inspectorOn(inspector) || app.inspectorOverlay} onclick={() => toggleInspector(inspector)}
              aria-label={t("shell.inspector")} aria-pressed={inspectorOn(inspector)} title={`${t("shell.inspector")} · ⌥⌘I`}>
        <Icon name="inspector" /></button>
    {/if}
  </div>
</header>
<div class="workspace">
  {@render children?.()}
</div>

<style>
  .on { color: var(--c-accent-text); }
  .tb-title :global(.title-btn) { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: text; text-align: left; max-width: 100%; }
</style>
