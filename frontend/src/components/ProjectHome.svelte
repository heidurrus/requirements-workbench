<script>
  // The top of Sources (PM-26, PM-29): a setup checklist until the essentials work, then
  // "what's next" from the pipeline state and "since your last visit" from the audit log.
  import Icon from "./Icon.svelte";
  import { api } from "../lib/api.js";
  import { explain } from "../lib/errors.js";
  import { app, t, go, currentProject, loadProjects, toast, writePref } from "../lib/state.svelte.js";

  let settings = $state(null);
  let local = $state(null);
  let jira = $state(null);
  let check = $state(null);              // {running} | {ok, message}
  let nameDraft = $state("");
  let since = $state([]);
  let showSince = $state(false);

  const pid = $derived(app.currentProjectId);
  const project = $derived(currentProject());
  const DEFAULT_NAMES = ["Мой проект", "My project"];

  async function load() {
    const [s, l, j] = await Promise.all([api("/settings").catch(() => null), api("/api/local-llm").catch(() => null),
                                         api("/api/jira/status").catch(() => null)]);
    settings = s; local = l; jira = j;
  }
  $effect(() => { pid; load(); });

  // "Since your last visit": remember when this project was last opened.
  $effect(() => {
    const id = pid;
    if (!id) return;
    let last = null;
    try { last = JSON.parse(localStorage.getItem("wb.lastVisit." + id)); } catch (_) { /* private mode */ }
    since = [];
    if (last) api(`/api/projects/${id}/activity?since=${last}&limit=50`).then(b => (since = b.entries)).catch(() => {});
    writePref("lastVisit." + id, Date.now() / 1000);
  });

  const aiReady = $derived.by(() => {
    if (!settings) return null;
    const localReady = local && local.models?.some(m => m.installed);
    if (project?.local_only) return !!localReady || settings.llm_provider === "ollama";
    if (settings.llm_provider === "claude") return settings.anthropic_key_set;
    if (settings.llm_provider === "local") return !!localReady;
    return true;
  });
  const named = $derived(project && !DEFAULT_NAMES.includes(project.name));
  const steps = $derived([
    { key: "name", done: named },
    { key: "ai", done: aiReady },
    { key: "speakers", done: !!settings?.hf_token_set, optional: true },
    { key: "jira", done: !!jira?.connected, optional: true },
  ]);
  let dismissed = $state(false);
  $effect(() => { try { dismissed = localStorage.getItem("wb.setupDismissed." + pid) === "1"; } catch (_) { dismissed = false; } });
  const showSetup = $derived(settings && !dismissed && steps.some(s => !s.done && !s.optional));

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
  function dismiss() { dismissed = true; writePref("setupDismissed." + pid, "1"); }

  // What's next: the first thing in the pipeline that needs the BA.
  const next = $derived.by(() => {
    const s = app.status;
    if (!s) return null;
    if (!s.sources) return null;                                   // the capture cards below are the next step
    if (s.processing) return { icon: "clock", text: t("home.n.processing", { n: s.processing }), wait: true };
    if (s.atoms.review) return { icon: "atoms", text: t("home.n.review", { n: s.atoms.review }), cta: t("home.cta.review"), go: "/atoms" };
    if (s.atoms.conflicts) return { icon: "warn", text: t("home.n.conflicts", { n: s.atoms.conflicts }), cta: t("at.resolve"), go: "/atoms" };
    if (!s.atoms.total) return { icon: "atoms", text: t("home.n.extract"), cta: t("home.cta.open_source"), go: "/atoms" };
    if (!s.document.version) return { icon: "doc", text: t("home.n.build", { n: s.atoms.accepted }), cta: t("doc.build_cta"), go: "/document" };
    if (s.document.stale) return { icon: "doc", text: t("home.n.doc_stale", { n: s.document.changed }), cta: t("home.cta.update"), go: "/document" };
    if (!s.backlog.items) return { icon: "tree", text: t("home.n.backlog"), cta: t("bl.build"), go: "/backlog" };
    if (s.backlog.stale) return { icon: "tree", text: t("home.n.bl_stale"), cta: t("home.cta.update"), go: "/backlog" };
    if (s.export.pending) return { icon: "export", text: t("home.n.push", { n: s.export.pending }), cta: t("home.cta.push"), go: "/export" };
    if (!s.export.pushed) return { icon: "export", text: t("home.n.first_push"), cta: t("home.cta.push"), go: "/export" };
    if (s.open_items.questions) return { icon: "mail", text: t("home.n.questions", { n: s.open_items.questions }), cta: t("oi.letter"), go: "/atoms" };
    return { icon: "check", text: t("home.n.all_done"), done: true };
  });
  const sinceText = e => `${e.label ? "«" + e.label.slice(0, 80) + "» · " : ""}${t("home.act." + e.entity) === "home.act." + e.entity ? e.entity : t("home.act." + e.entity)}: ${e.action}`;
</script>

{#if showSetup}
  <section class="card setup">
    <div class="head">
      <h2>{t("home.setup")}</h2>
      <p class="t3">{t("home.setup_hint")}</p>
      <button class="btn btn-ghost btn-sm dismiss" onclick={dismiss}>{t("home.later")}</button>
    </div>
    {#each steps as st (st.key)}
      <div class="step" class:done={st.done}>
        <span class="mark">{#if st.done}<Icon name="check" size={12} />{/if}</span>
        <div class="grow">
          <b>{t("home.s." + st.key)}{#if st.optional} <span class="t3 opt">{t("home.optional")}</span>{/if}</b>
          <p class="t3">{t("home.d." + st.key)}</p>
          {#if st.key === "name" && !st.done}
            <form class="inline" onsubmit={e => { e.preventDefault(); saveName(); }}>
              <input class="input" bind:value={nameDraft} placeholder={t("home.name_ph")} aria-label={t("home.s.name")} />
              <button class="btn btn-sm btn-primary" disabled={!nameDraft.trim()}>{t("at.save")}</button>
            </form>
          {/if}
          {#if st.key === "ai" && check && !check.running}<p class="check" class:ok={check.ok}>{check.message}</p>{/if}
        </div>
        {#if st.key === "ai"}
          <button class="btn btn-sm" onclick={runCheck} disabled={check?.running}>{#if check?.running}<span class="spinner"></span>{/if}{t("home.check")}</button>
          {#if !st.done}<button class="btn btn-sm btn-primary" onclick={() => go("/settings")}>{t("err.open_settings")}</button>{/if}
        {:else if st.key === "speakers" && !st.done}
          <button class="btn btn-sm btn-ghost" onclick={() => go("/settings")}>{t("err.open_settings")}</button>
        {:else if st.key === "jira" && !st.done}
          <button class="btn btn-sm btn-ghost" onclick={() => go("/export")}>{t("jr.connect")}</button>
        {/if}
      </div>
    {/each}
  </section>
{/if}

{#if next}
  <div class="next" class:done={next.done}>
    <span class="ico"><Icon name={next.icon} size={14} /></span>
    <span class="grow"><b>{t("home.next")}:</b> {next.text}</span>
    {#if since.length}
      <button class="btn btn-sm btn-ghost" onclick={() => (showSince = !showSince)}>{t("home.since", { n: since.length })}</button>
    {/if}
    {#if next.cta}<button class="btn btn-sm btn-primary" onclick={() => go(next.go)}>{next.cta} <Icon name="arrow" size={12} /></button>{/if}
  </div>
  {#if showSince}
    <ol class="since card">
      {#each since as e, i (i)}<li><span class="t3 num">{new Date(e.at * 1000).toLocaleString(app.lang)}</span> {sinceText(e)}</li>{/each}
    </ol>
  {/if}
{/if}

<style>
  .setup { margin-bottom: var(--sp-6); overflow: hidden; }
  .head { display: flex; align-items: baseline; gap: var(--sp-4); flex-wrap: wrap; padding: var(--sp-5) var(--sp-6) var(--sp-3); }
  .head h2 { font: 600 var(--fs-15)/20px var(--font-display); }
  .head p { flex: 1; font-size: var(--fs-12); }
  .step { display: flex; gap: var(--sp-5); align-items: flex-start; padding: var(--sp-4) var(--sp-6); border-top: 1px solid var(--line); }
  .mark { width: 18px; height: 18px; border-radius: 50%; box-shadow: inset 0 0 0 1.5px var(--line-control); display: grid; place-items: center;
    flex: none; margin-top: 1px; color: #fff; }
  .step.done .mark { background: var(--ok); box-shadow: none; }
  .step.done b { color: var(--text-2); }
  .grow { flex: 1; min-width: 0; }
  .step p { font-size: var(--fs-12); margin-top: 1px; }
  .opt { font-weight: 400; font-size: var(--fs-12); }
  .inline { display: flex; gap: var(--sp-4); margin-top: var(--sp-4); max-width: 420px; }
  .check { margin-top: var(--sp-3); color: var(--danger); font-size: var(--fs-12); }
  .check.ok { color: var(--ok); }
  .next { display: flex; align-items: center; gap: var(--sp-4); padding: var(--sp-4) var(--sp-4) var(--sp-4) var(--sp-5); margin-bottom: var(--sp-6);
    border-radius: var(--r-lg); background: var(--accent-bg); color: var(--accent); flex-wrap: wrap; }
  .next.done { background: var(--ok-bg); color: var(--ok); }
  .next b { font-weight: 600; }
  .next .ico { display: grid; }
  .since { margin: calc(-1 * var(--sp-4)) 0 var(--sp-6); padding: var(--sp-4) var(--sp-6) var(--sp-4) 36px; font-size: var(--fs-12); line-height: 20px;
    max-height: 240px; overflow: auto; }
</style>
