<script>
  // First run (redesign §8.10): not a wizard. Three rows in the empty Sources pane.
  import Icon from "./Icon.svelte";
  import { api } from "../lib/api.js";
  import { explain } from "../lib/errors.js";
  import { app, t, go, currentProject, loadProjects, toast } from "../lib/state.svelte.js";

  let { onRecord, onImport } = $props();

  let settings = $state(null);
  let local = $state(null);
  let check = $state(null);              // {running} | {ok, message}
  let nameDraft = $state("");

  const pid = $derived(app.currentProjectId);
  const project = $derived(currentProject());
  const DEFAULT_NAMES = ["Мой проект", "My project"];

  async function load() {
    const [s, l] = await Promise.all([api("/settings").catch(() => null), api("/api/local-llm").catch(() => null)]);
    settings = s; local = l;
  }
  $effect(() => { pid; load(); });

  const aiReady = $derived.by(() => {
    if (!settings) return null;
    const localReady = local && local.models?.some(m => m.installed);
    if (project?.local_only) return !!localReady || settings.llm_provider === "ollama";
    if (settings.llm_provider === "claude") return settings.anthropic_key_set;
    if (settings.llm_provider === "local") return !!localReady;
    return true;
  });
  const named = $derived(!!project && !DEFAULT_NAMES.includes(project.name));
  const aiName = $derived(!settings ? "" : settings.llm_provider === "claude" ? t("first.ai_claude")
    : settings.llm_provider === "local" ? t("first.ai_local") : "Ollama");

  async function saveName() {
    const name = nameDraft.trim();
    if (!name) return;
    try {
      await api(`/api/projects/${pid}`, { method: "PATCH", body: { name } });
      await loadProjects();
      nameDraft = "";
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function runCheck() {
    check = { running: true };
    try {
      const r = await api("/api/ai/check", { method: "POST", body: { project_id: pid } });
      check = r.ok ? { ok: true, message: t("home.ai_ok", { model: r.model }) } : { ok: false, message: explain({ message: r.error || "", body: r }).message };
    } catch (err) { check = { ok: false, message: explain(err).message }; }
  }
</script>

<div class="first">
  <div class="empty-glyph"><Icon name="sources" size={20} /></div>
  <h2>{t("first.title")}</h2>
  <p class="lead">{t("first.lead")}</p>

  <ol>
    <li class:done={named}>
      <span class="n">{#if named}<Icon name="check" size={12} />{:else}1{/if}</span>
      <div class="grow">
        <h3>{t("first.name")}</h3>
        {#if named}<p class="t3">{project.name}</p>
        {:else}
          <p class="t3">{t("home.d.name")}</p>
          <form onsubmit={e => { e.preventDefault(); saveName(); }}>
            <input class="input" bind:value={nameDraft} placeholder={t("home.name_ph")} aria-label={t("home.s.name")} />
            <button class="btn primary" disabled={!nameDraft.trim()}>{t("at.save")}</button>
          </form>
        {/if}
      </div>
    </li>
    <li class:done={!!aiReady}>
      <span class="n">{#if aiReady}<Icon name="check" size={12} />{:else}2{/if}</span>
      <div class="grow">
        <h3>{t("first.ai")}</h3>
        <p class="t3">{aiReady ? aiName : t("home.d.ai")}</p>
        {#if check && !check.running}<p class="check" class:ok={check.ok}>{check.message}</p>{/if}
        <div class="acts">
          {#if !aiReady}<button class="btn primary" onclick={() => go("/settings")}>{t("first.ai_setup")} <Icon name="arrow" size={14} /></button>{/if}
          <button class="btn" onclick={runCheck} disabled={check?.running}>{#if check?.running}<span class="spinner"></span>{/if}{t("first.ai_check")}</button>
        </div>
      </div>
    </li>
    <li>
      <span class="n">3</span>
      <div class="grow">
        <h3>{t("first.source")}</h3>
        <p class="t3">{aiReady === false ? t("first.source_wait") : t("first.source_d")}</p>
        <div class="acts">
          <button class="btn" class:primary={!!aiReady} onclick={onImport}><Icon name="upload" size={14} /> {t("src.import")}</button>
          <button class="btn" onclick={onRecord}><i class="recdot"></i> {t("sources.record.title")}</button>
        </div>
      </div>
    </li>
  </ol>
</div>

<style>
  .first { width: min(560px, 100%); margin: 0 auto; padding: var(--s-11) var(--s-6) var(--s-11); display: grid; grid-template-columns: minmax(0, 1fr); }
  .empty-glyph { margin: 0 auto var(--s-5); }
  h2 { font: var(--w-semibold) var(--t-title-1)/var(--lh-title-1) var(--font-display); letter-spacing: -.016em; text-align: center; }
  .lead { text-align: center; color: var(--c-text-2); font-size: var(--t-item); line-height: var(--lh-item); margin: var(--s-2) 0 var(--s-9); }
  ol { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--c-line); }
  li { display: flex; gap: var(--s-6); padding: var(--s-6) 0; border-bottom: 1px solid var(--c-line); }
  .n { width: 24px; height: 24px; border-radius: 50%; box-shadow: inset 0 0 0 1.5px var(--c-line-control); display: grid; place-items: center; flex: none;
    font: var(--w-semibold) var(--t-foot)/1 var(--font); color: var(--c-text-2); }
  li.done .n { background: var(--c-ok); box-shadow: none; color: #fff; }
  h3 { font: var(--w-medium) var(--t-item)/24px var(--font); }
  li.done h3 { color: var(--c-text-2); }
  form, .acts { display: flex; gap: var(--s-4); margin-top: var(--s-5); flex-wrap: wrap; }
  form .input { flex: 1; min-width: 200px; }
  .check { margin-top: var(--s-3); color: var(--c-danger); font-size: var(--t-foot); }
  .check.ok { color: var(--c-ok); }
  .recdot { width: 10px; height: 10px; border-radius: 50%; background: var(--c-rec); }
</style>
