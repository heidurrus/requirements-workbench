<script>
  import Block from "../components/Block.svelte";
  import LocalModel from "../components/LocalModel.svelte";
  import { api } from "../lib/api.js";
  import { LANGS } from "../lib/i18n.js";
  import { app, t, setLang, setTheme, currentProject, loadProjects, switchProject, toast } from "../lib/state.svelte.js";

  let s = $state(null);              // server settings payload
  let keyDraft = $state("");
  let hfDraft = $state("");
  let showKey = $state(false);
  let showHf = $state(false);
  let ollama = $state(null);
  let projectName = $state("");
  let localReady = $state(true);

  async function checkLocal() {
    const st = await api("/api/local-llm").catch(() => null);
    localReady = !st || !st.supported || st.models.some(m => m.installed);
  }

  async function load() {
    s = await api("/settings");
    projectName = currentProject()?.name || "";
    if (s.llm_provider === "ollama") checkOllama();
    checkLocal();
  }
  $effect(() => { load(); });
  $effect(() => { projectName = currentProject()?.name || ""; });

  async function save(body) {
    try { s = await api("/settings", { method: "POST", body }); if (body.llm_provider === "ollama") checkOllama(); }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }
  async function checkOllama() { ollama = (await api("/ollama/status").catch(() => ({ reachable: false }))).reachable; }

  async function saveKey() { if (!keyDraft.trim()) return; await save({ anthropic_api_key: keyDraft.trim() }); keyDraft = ""; }
  async function saveHf() { if (!hfDraft.trim()) return; await save({ hf_token: hfDraft.trim() }); hfDraft = ""; }

  async function updateProject(changes) {
    const p = currentProject();
    if (!p) return;
    try { await api(`/api/projects/${p.id}`, { method: "PATCH", body: changes }); await loadProjects(); }
    catch (err) { toast(err.message, { kind: "danger" }); projectName = p.name; }
  }
  async function archive() {
    await updateProject({ archived: true });
    await loadProjects();
    if (app.projects[0]) await switchProject(app.projects[0].id);
  }
  async function restore(id) {
    await api(`/api/projects/${id}`, { method: "PATCH", body: { archived: false } });
    await loadProjects();
  }

  const env = $derived(app.health ? [
    [t("env.ffmpeg"), app.health.ffmpeg ? t("env.found") : t("env.missing"), app.health.ffmpeg],
    [t("env.gpu"), app.health.gpu.gpu_name || (app.health.gpu.mps ? "Apple Silicon (MPS)" : t("env.cpu_only")),
      app.health.gpu.cuda || app.health.gpu.mps],
    [t("env.hf"), app.health.hf_token ? t("env.set") : t("env.missing"), app.health.hf_token],
    [t("env.ollama"), app.health.ollama ? t("env.running") : t("env.stopped"), app.health.ollama],
    [t("env.sysaudio"), app.health.system_audio_capture ? t("env.supported") : t("env.unsupported"), app.health.system_audio_capture],
  ] : []);
</script>

<div class="screen-inner narrow">
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("set.title")}</h1>
      <p class="screen-sub">{t("set.sub")}</p>
    </div>
  </header>

  {#if currentProject()}
    <h2 class="group-t">{t("set.project")}</h2>
    <section class="card">
      <div class="form-row">
        <label class="l" for="pname"><b>{t("set.project_name")}</b></label>
        <div class="c grow-c">
          <input class="input" id="pname" bind:value={projectName}
                 onblur={() => projectName.trim() && projectName.trim() !== currentProject().name && updateProject({ name: projectName.trim() })}
                 onkeydown={e => e.key === "Enter" && e.currentTarget.blur()} />
        </div>
      </div>
      <label class="form-row">
        <span class="l"><b>{t("project.local_only")}</b><span>{t("set.local_only_hint")}</span></span>
        <span class="c"><input type="checkbox" class="switch" checked={currentProject().local_only}
               onchange={e => updateProject({ local_only: e.currentTarget.checked })} /></span>
      </label>
      {#if currentProject().local_only && !localReady && s && s.llm_provider !== "ollama"}
        <div class="form-row col">
          <p class="banner warn"><span>{t("llm.local_only_needs")}</span></p>
          <LocalModel only="recommended" selected={s.local_model} onSelect={id => save({ local_model: id })} onReady={checkLocal} />
        </div>
      {/if}
      <div class="form-row">
        <span class="l"><b>{t("set.out_lang")}</b><span>{t("set.out_lang_hint")}</span></span>
        <div class="c">
          <div class="seg out-lang" role="group" aria-label={t("set.out_lang")}>
            {#each ["auto", "ru", "en"] as l (l)}
              <button aria-pressed={(currentProject().language || "auto") === l}
                      onclick={() => updateProject({ language: l })}>{t("set.out_lang." + l)}</button>
            {/each}
          </div>
        </div>
      </div>
      <div class="form-row">
        <span class="l"><b>{t("set.archive")}</b><span>{t("set.archive_hint")}</span></span>
        <div class="c"><button class="btn btn-danger" onclick={archive} disabled={app.projects.length < 2}>{t("set.archive")}</button></div>
      </div>
      {#if app.archivedProjects.length}
        <div class="form-row col">
          <span class="label">{t("project.archived")}</span>
          {#each app.archivedProjects as p (p.id)}
            <div class="archived-row"><span>{p.name}</span>
              <button class="btn btn-ghost btn-sm" onclick={() => restore(p.id)}>{t("project.restore")}</button></div>
          {/each}
        </div>
      {/if}
    </section>
  {/if}

  {#if s}
    <h2 class="group-t">{t("set.ai")}</h2>
    <section class="card">
      <div class="form-row">
        <span class="l"><b>{t("set.provider")}</b><span>{t("set.provider_hint." + s.llm_provider)}</span></span>
        <div class="c">
          <div class="seg provider" role="group" aria-label={t("set.provider")}>
            {#each ["claude", "local", "ollama"] as p (p)}
              <button aria-pressed={s.llm_provider === p} onclick={() => save({ llm_provider: p })}>{t("set.provider." + p)}</button>
            {/each}
          </div>
        </div>
      </div>
      {#if s.llm_provider === "claude"}
        <div class="form-row col">
          <label class="l" for="akey"><b>{t("set.anthropic_key")}</b>
            <span class:ok={s.anthropic_key_set} class:bad={!s.anthropic_key_set}>{s.anthropic_key_set ? t("set.key_set") : t("set.key_unset")}</span></label>
          <div class="input-row">
            <input class="input code" id="akey" type={showKey ? "text" : "password"} bind:value={keyDraft} autocomplete="off"
                   placeholder={s.anthropic_key_set ? t("set.key_saved_placeholder") : "sk-ant-..."} />
            <button class="btn" onclick={() => (showKey = !showKey)}>{showKey ? t("set.hide") : t("set.show")}</button>
            <button class="btn btn-primary" onclick={saveKey} disabled={!keyDraft.trim()}>{t("set.save")}</button>
          </div>
        </div>
        <div class="form-row">
          <label class="l" for="cmodel"><b>{t("set.claude_model")}</b><span>{t("set.claude_note")}</span></label>
          <div class="c">
            <select class="select" id="cmodel" value={s.claude_model} onchange={e => save({ claude_model: e.currentTarget.value })}>
              {#each s.claude_models as m (m.id)}<option value={m.id}>{t("model." + m.id) === "model." + m.id ? m.label : t("model." + m.id)}</option>{/each}
            </select>
          </div>
        </div>
        <div class="form-row col">
          <span class="l"><b>{t("llm.for_local_only")}</b></span>
          <LocalModel selected={s.local_model} onSelect={id => save({ local_model: id })} onReady={checkLocal} />
        </div>
      {:else if s.llm_provider === "local"}
        <div class="form-row col">
          <LocalModel selected={s.local_model} onSelect={id => save({ local_model: id })} onReady={checkLocal} />
          <p class="hint">{t("llm.quality_note")}</p>
        </div>
      {:else}
        <div class="form-row">
          <label class="l" for="omodel"><b>{t("set.ollama_model")}</b>
            {#if ollama !== null}<span class:ok={ollama} class:bad={!ollama}>{ollama ? t("set.ollama_running") : t("set.ollama_stopped")}</span>{/if}</label>
          <div class="c">
            <input class="input code" id="omodel" value={s.ollama_model} placeholder="qwen3:8b"
                   onchange={e => save({ ollama_model: e.currentTarget.value.trim() || "qwen3:8b" })} />
          </div>
        </div>
        <div class="form-row col"><p class="hint">{t("set.ollama_note")}</p></div>
      {/if}
    </section>

    <h2 class="group-t">{t("set.hf")}</h2>
    <section class="card">
      <div class="form-row col">
        <label class="l" for="hf"><b>{t("set.hf_token")}</b>
          <span class:ok={s.hf_token_set} class:bad={!s.hf_token_set}>{s.hf_token_set ? t("set.hf_set") : t("set.hf_unset")}</span></label>
        <div class="input-row">
          <input class="input code" id="hf" type={showHf ? "text" : "password"} bind:value={hfDraft} autocomplete="off"
                 placeholder={s.hf_token_set ? t("set.key_saved_placeholder") : "hf_..."} />
          <button class="btn" onclick={() => (showHf = !showHf)}>{showHf ? t("set.hide") : t("set.show")}</button>
          <button class="btn btn-primary" onclick={saveHf} disabled={!hfDraft.trim()}>{t("set.save")}</button>
        </div>
        <div class="hint hf-note">
          {t("set.hf_note")}
          <ul>
            <li><a href="https://huggingface.co/settings/tokens" target="_blank" rel="noopener">huggingface.co/settings/tokens</a></li>
            <li><a href="https://huggingface.co/pyannote/segmentation-3.0" target="_blank" rel="noopener">pyannote/segmentation-3.0</a></li>
            <li><a href="https://huggingface.co/pyannote/speaker-diarization-3.1" target="_blank" rel="noopener">pyannote/speaker-diarization-3.1</a></li>
            <li><a href="https://huggingface.co/pyannote/speaker-diarization-community-1" target="_blank" rel="noopener">pyannote/speaker-diarization-community-1</a></li>
          </ul>
        </div>
      </div>
    </section>
  {/if}

  <h2 class="group-t">{t("set.interface")}</h2>
  <section class="card">
    <div class="form-row">
      <span class="l"><b>{t("set.language")}</b></span>
      <div class="c">
        <div class="seg" role="group" aria-label={t("set.language")}>
          {#each LANGS as l (l.id)}
            <button aria-pressed={app.lang === l.id} onclick={() => setLang(l.id)}>{l.label}</button>
          {/each}
        </div>
      </div>
    </div>
    <div class="form-row">
      <span class="l"><b>{t("set.theme")}</b><span>{t("set.theme_hint")}</span></span>
      <div class="c">
        <div class="seg" role="group" aria-label={t("set.theme")}>
          {#each ["auto", "light", "dark"] as th (th)}
            <button aria-pressed={app.theme === th} onclick={() => setTheme(th)}>{t("theme.s." + th)}</button>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <div class="env-block">
    <Block id="set-env" title={t("set.env")} open={false}>
      <div class="env">
        {#each env as [name, value, ok] (name)}
          <div class="env-cell"><span class="label">{name}</span><span class:ok class:bad={!ok}>{value}</span></div>
        {/each}
      </div>
    </Block>
  </div>
</div>

<style>
  .group-t { font-size: var(--fs-12); font-weight: 600; color: var(--text-2); margin: var(--sp-8) 0 var(--sp-4) var(--sp-5); }
  .group-t:first-of-type { margin-top: var(--sp-4); }
  .form-row { display: flex; align-items: center; gap: var(--sp-6); padding: var(--sp-5) var(--sp-6); min-height: 48px; }
  .form-row + .form-row { border-top: 1px solid var(--line); }
  label.form-row { cursor: pointer; }
  .form-row.col { flex-direction: column; align-items: stretch; gap: var(--sp-4); }
  .l { flex: 1; min-width: 0; }
  .l b { display: block; font-weight: 500; }
  .l span { display: block; font-size: var(--fs-12); color: var(--text-3); margin-top: 1px; line-height: 16px; }
  .c { flex: none; display: flex; gap: var(--sp-4); align-items: center; max-width: 60%; }
  .grow-c { flex: 1; max-width: 320px; }
  .c .select, .c .input { width: auto; min-width: 200px; max-width: 100%; }
  .grow-c .input { width: 100%; }
  .l .ok, .ok { color: var(--ok) !important; }
  .l .bad, .bad { color: var(--danger) !important; }
  .archived-row { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-4); }
  .hf-note ul { margin: var(--sp-2) 0 0; padding-left: var(--sp-6); }
  .env-block { margin-top: var(--sp-8); }
  .env { display: grid; gap: var(--sp-4); grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
  .env-cell { display: flex; flex-direction: column; gap: 2px; padding: var(--sp-4) var(--sp-5); background: var(--surface-2); border-radius: var(--r-md); }
  @media (max-width: 720px) {
    .form-row:not(.col) { flex-direction: column; align-items: stretch; gap: var(--sp-4); }
    .c { max-width: none; }
  }
</style>
