<script>
  import Block from "../components/Block.svelte";
  import Icon from "../components/Icon.svelte";
  import { api, pollJob } from "../lib/api.js";
  import { DesktopRecorder, BrowserRecorder, listMicrophones } from "../lib/recorder.js";
  import { fmtDate, fmtDuration, isTranscriptFile } from "../lib/format.js";
  import { app, t, go, loadSources, saveOptions, toast, rememberSource } from "../lib/state.svelte.js";

  // ── upload ────────────────────────────────────────────────────────────────
  let file = $state(null);
  let dragging = $state(false);
  let uploading = $state(false);
  let uploadError = $state("");
  const fileIsTranscript = $derived(file ? isTranscriptFile(file.name) : false);

  function pickFile(f) { if (f) { file = f; uploadError = ""; } }

  function optionsPayload() {
    const o = app.options;
    return { model: o.model, device: o.device, diarize: String(o.diarize),
             word_timestamps: String(!o.diarize && o.word_timestamps) };
  }

  async function submitUpload(f = file, kind = null) {
    uploading = true;
    uploadError = "";
    try {
      const form = new FormData();
      form.append("audio", f);
      form.append("project_id", app.currentProjectId);
      Object.entries(optionsPayload()).forEach(([k, v]) => form.append(k, v));
      if (kind) form.append("kind", kind);
      const res = await api("/transcribe", { method: "POST", form });
      file = null;
      await loadSources();
      if (isTranscriptFile(f.name)) {
        rememberSource(res.source_id);
        go(`/source/${res.source_id}/summarize`);   // imported: go straight to the summary
      } else {
        track(res.source_id, res.job_id);
      }
    } catch (err) {
      uploadError = err.message;
    } finally {
      uploading = false;
    }
  }

  // Follow a transcription job; the list row shows its progress.
  async function track(sourceId, jobId) {
    app.jobs[sourceId] = { jobId, progress: 0, message: "" };
    try {
      await pollJob(jobId, job => {
        app.jobs[sourceId] = { jobId, progress: job.progress || 0, message: job.progress_msg || "" };
      });
      delete app.jobs[sourceId];
      await loadSources();
      const s = app.sources.find(x => x.id === sourceId);
      toast(`${s ? s.title : ""} · ${t("status.ready")}`, { action: t("nav.transcript"), onAction: () => open(sourceId) });
    } catch (err) {
      delete app.jobs[sourceId];
      await loadSources();
      toast(err.message, { kind: "danger" });
    }
  }

  async function transcribeSaved(sourceId) {
    try {
      const res = await api(`/api/sources/${sourceId}/transcribe`, { method: "POST", body: optionsPayload() });
      await loadSources();
      track(sourceId, res.job_id);
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  // ── recording ─────────────────────────────────────────────────────────────
  let mics = $state([]);
  let mic = $state("");
  let recorder = null;
  let recording = $state(false);
  let recStarted = $state(0);
  let elapsed = $state(0);
  let recProblems = $state([]);
  let recError = $state("");
  let timer = null;

  $effect(() => { listMicrophones(app.device.desktop).then(m => (mics = m)); });

  const channelName = c => t(c === "mic" ? "channel.mic" : "channel.sys");

  async function startRecording() {
    recError = "";
    recProblems = [];
    try {
      if (app.device.desktop) {
        recorder = new DesktopRecorder();
        await recorder.start(mic === "" ? null : Number(mic), st => {
          recProblems = Object.entries(st.channels || {}).filter(([, c]) => c.error)
            .map(([n, c]) => `${channelName(n)}: ${c.error}`);
        });
      } else {
        recorder = new BrowserRecorder();
        await recorder.start(mic, which => recProblems = [...recProblems, `${channelName(which)}: —`]);
      }
      recording = true;
      recStarted = Date.now();
      elapsed = 0;
      timer = setInterval(() => (elapsed = Math.floor((Date.now() - recStarted) / 1000)), 500);
    } catch (err) {
      recError = err.message;
    }
  }

  async function stopRecording() {
    clearInterval(timer);
    recording = false;
    try {
      if (recorder instanceof DesktopRecorder) {
        const { sourceId, errors } = await recorder.stop(`${t("rec.title")} ${fmtDate(Date.now() / 1000, app.lang)}`);
        const missing = Object.entries(errors).map(([n, e]) => `${channelName(n)}: ${e}`);
        recProblems = missing;
        if (sourceId) { await loadSources(); transcribeSaved(sourceId); }
      } else {
        const blob = await recorder.stop();
        const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
        await submitUpload(new File([blob], `recording_${ts}.webm`, { type: "audio/webm" }), "recording");
      }
    } catch (err) {
      recError = err.message;
      recProblems = Object.entries(err.errors || {}).map(([n, e]) => `${channelName(n)}: ${e}`);
    }
  }

  const clock = s => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  // ── list ──────────────────────────────────────────────────────────────────
  let editingId = $state(null);
  let editTitle = $state("");

  function open(id) { rememberSource(id); go(`/source/${id}`); }

  function startRename(s) { editingId = s.id; editTitle = s.title; }
  async function saveRename(s) {
    const title = editTitle.trim();
    editingId = null;
    if (!title || title === s.title) return;
    try { await api(`/api/sources/${s.id}`, { method: "PATCH", body: { title } }); await loadSources(); }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function remove(s) {
    await api(`/api/sources/${s.id}`, { method: "DELETE" });
    await loadSources();
    toast(t("sources.deleted", { title: s.title }), {
      action: t("sources.undo"),
      onAction: async () => { await api(`/api/sources/${s.id}/restore`, { method: "POST" }); await loadSources(); },
    });
  }

  const busy = $derived(app.sources.filter(s => s.status === "processing").length);
  const optionsMeta = $derived([app.options.model, app.options.device === "cpu" ? "CPU" : "GPU",
    app.options.diarize ? t("opt.diarize").toLowerCase() : null].filter(Boolean).join(" · "));
  const kindIcon = { audio: "wave", video: "wave", recording: "mic", transcript: "transcript", email: "mail", document: "file" };

  function sourceMeta(s) {
    return [fmtDate(s.created_at, app.lang), t("kind." + s.kind), fmtDuration(s.duration, app.lang),
      s.speakers && !["email", "document"].includes(s.kind) ? t("meta.speakers", { n: s.speakers }) : null]
      .filter(Boolean).join(" · ");
  }
</script>

<div class="screen-inner">
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("sources.title")}</h1>
      <p class="screen-sub">{t("sources.count", { n: app.sources.length }) + (busy ? " · " + t("sources.busy", { busy }) : "")}</p>
    </div>
  </header>

  <div class="capture">
    <section class="card rec-card" class:live={recording}>
      <button class="rec-btn" class:on={recording} onclick={recording ? stopRecording : startRecording}
              aria-label={recording ? t("rec.stop") : t("rec.start")} title={recording ? t("rec.stop") : t("rec.start")}>
        <i></i>
      </button>
      <div class="rec-meta">
        <h2>{t("sources.record.title")}</h2>
        {#if recording}
          <p class="rec-live"><span class="pulse"></span>{t("rec.recording")} <span class="num">{clock(elapsed)}</span></p>
        {:else}
          <p>{app.device.desktop ? t("sources.record.desc") : t("sources.record.desc_browser")}</p>
        {/if}
        <label class="mic-pick" title={t("rec.mic")}>
          <Icon name="mic" size={14} />
          <select class="select" bind:value={mic} disabled={recording} aria-label={t("rec.mic")}>
            <option value="">{t("rec.mic_default")}</option>
            {#each mics as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
          </select>
        </label>
        {#if recProblems.length}
          <p class="note warn below">{recording ? t("rec.problems") : t("rec.saved_partial")}: {recProblems.join(" · ")}</p>
        {/if}
        {#if recError}<p class="note danger below">{recError}</p>{/if}
      </div>
    </section>

    <section class="drop-card" class:dragging class:has-file={file}
             ondragover={e => { e.preventDefault(); dragging = true; }}
             ondragleave={() => (dragging = false)}
             ondrop={e => { e.preventDefault(); dragging = false; pickFile(e.dataTransfer.files[0]); }}>
      <label class="drop">
        <!-- no accept filter: the macOS desktop picker ignores extensions; the server validates -->
        <input type="file" onchange={e => pickFile(e.currentTarget.files[0])} aria-label={t("sources.upload.title")} />
        <span class="ico"><Icon name="upload" /></span>
        <span class="drop-txt">
          <h2>{t("sources.upload.drop")} <span class="link">{t("sources.upload.browse")}</span></h2>
          <span class="desc">{t("sources.upload.desc")}</span>
          <span class="fmts">{#each t("sources.upload.formats").split(" · ") as f (f)}<span class="tag outline">{f}</span>{/each}</span>
        </span>
      </label>
      {#if file}
        <div class="file-row">
          <Icon name={fileIsTranscript ? "transcript" : "wave"} size={14} />
          <span class="file">{file.name}{#if fileIsTranscript}<span class="t3"> · {t("sources.upload.is_transcript")}</span>{/if}</span>
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("at.cancel")} title={t("at.cancel")}
                  onclick={() => (file = null)}><Icon name="close" size={14} /></button>
          <button class="btn btn-primary" disabled={uploading} onclick={() => submitUpload()}>
            {#if uploading}<span class="spinner"></span>{/if}
            {fileIsTranscript ? t("sources.upload.summarize") : t("sources.upload.transcribe")}
          </button>
        </div>
      {/if}
      {#if uploadError}<p class="note danger below">{uploadError}</p>{/if}
    </section>
  </div>

  <div class="stack">
    <Block id="sources-options" title={t("sources.options")} meta={optionsMeta} open={false}>
      <div class="row">
        <div class="field grow">
          <label class="label" for="model">{t("opt.model")}</label>
          <select class="select" id="model" bind:value={app.options.model} onchange={saveOptions}>
            {#each app.models as m (m)}<option value={m}>{m}</option>{/each}
          </select>
        </div>
        <div class="field">
          <span class="label">{t("opt.device")}</span>
          <div class="seg" role="group" aria-label={t("opt.device")}>
            <button aria-pressed={app.options.device === "cpu"} onclick={() => { app.options.device = "cpu"; saveOptions(); }}>CPU</button>
            <button aria-pressed={app.options.device !== "cpu"} disabled={!app.device.cuda && !app.device.mps}
                    onclick={() => { app.options.device = app.device.cuda ? "cuda" : "mps"; saveOptions(); }}>GPU</button>
          </div>
        </div>
      </div>
      <div class="row" style="margin-top: var(--sp-5)">
        <label class="check"><input type="checkbox" class="switch" bind:checked={app.options.diarize} onchange={saveOptions} />
          {t("opt.diarize")} <span class="hint">{t("opt.diarize_hint")}</span></label>
        {#if !app.options.diarize}
          <label class="check"><input type="checkbox" class="switch" bind:checked={app.options.word_timestamps} onchange={saveOptions} />
            {t("opt.words")}</label>
        {/if}
      </div>
    </Block>

    <div>
      <div class="section-h"><h2>{t("sources.list")}</h2><span class="t3 num">{app.sources.length}</span></div>
      {#if !app.sources.length}
        <div class="card empty">
          <div class="glyph"><Icon name="sources" /></div>
          <p class="panel-title">{t("sources.empty.title")}</p>
          <p>{t("sources.empty.desc")}</p>
        </div>
      {:else}
        <ul class="card list">
          {#each app.sources as s (s.id)}
            <li class="item">
              <span class="src-ico"><Icon name={kindIcon[s.kind] || "file"} /></span>
              <div class="item-main">
                {#if editingId === s.id}
                  <!-- svelte-ignore a11y_autofocus -->
                  <input class="input" bind:value={editTitle} autofocus aria-label={t("sources.rename")}
                         onkeydown={e => { if (e.key === "Enter") saveRename(s); if (e.key === "Escape") editingId = null; }}
                         onblur={() => saveRename(s)} />
                {:else}
                  <button class="title-btn" onclick={() => open(s.id)} disabled={s.status === "processing" && !s.duration}
                          title={s.title}>{s.title}</button>
                {/if}
                <p class="meta">{sourceMeta(s)}</p>
                {#if app.jobs[s.id]}
                  <div class="job">
                    <div class="bar"><i style="width: {app.jobs[s.id].progress}%"></i></div>
                    <span class="t3 num">{app.jobs[s.id].message}</span>
                  </div>
                {/if}
                {#if s.status === "failed" && s.error}<p class="hint err">{s.error}</p>{/if}
              </div>
              <div class="item-side">
                {#if s.status === "processing"}
                  <span class="status run"><span class="spinner"></span>{t("status.processing")}</span>
                {:else if s.status === "ready"}
                  <span class="status ok"><Icon name="check" size={14} />{t("status.ready")}</span>
                {:else if s.status === "failed"}
                  <span class="status danger"><Icon name="warn" size={14} />{t("status.failed")}</span>
                {:else}
                  <span class="status warn"><Icon name="clock" size={14} />{t("status." + s.status)}</span>
                {/if}
                {#if s.has_summary}<span class="tag outline">{t("status.summary")}</span>{/if}
                {#if s.status === "recorded" || (s.status === "failed" && s.audio_file)}
                  <button class="btn btn-sm" onclick={() => transcribeSaved(s.id)}>{t("sources.transcribe_now")}</button>
                {/if}
                <span class="row-actions">
                  <button class="btn btn-ghost btn-sm icon-btn" title={t("sources.rename")} aria-label={t("sources.rename")}
                          onclick={() => startRename(s)}><Icon name="pencil" size={14} /></button>
                  <button class="btn btn-ghost btn-sm icon-btn" title={t("sources.delete")} aria-label={t("sources.delete")}
                          onclick={() => remove(s)}><Icon name="trash" size={14} /></button>
                </span>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
</div>

<style>
  .capture { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr); gap: var(--sp-6); margin-bottom: var(--sp-6); }
  @media (max-width: 1120px) { .capture { grid-template-columns: 1fr; } }

  .rec-card { display: flex; align-items: center; gap: var(--sp-7); padding: var(--sp-7) var(--sp-8); transition: box-shadow var(--t-med) var(--ease); }
  .rec-card.live { box-shadow: 0 0 0 1px var(--rec), 0 0 0 4px color-mix(in srgb, var(--rec) 15%, transparent); }
  .rec-btn { width: 64px; height: 64px; border-radius: 50%; border: 0; background: var(--surface); cursor: pointer;
    box-shadow: 0 0 0 1px var(--line-strong), 0 2px 6px rgba(0,0,0,.08); display: grid; place-items: center; flex: none;
    transition: transform var(--t-fast) var(--ease); }
  .rec-btn:hover { transform: scale(1.04); }
  .rec-btn:active { transform: scale(.97); }
  .rec-btn i { width: 28px; height: 28px; border-radius: 50%; background: var(--rec);
    transition: border-radius var(--t-med) var(--ease), width var(--t-med) var(--ease), height var(--t-med) var(--ease); }
  .rec-btn.on { animation: ring 1.6s ease-out infinite; }
  .rec-btn.on i { width: 20px; height: 20px; border-radius: 5px; }
  @keyframes ring { 0% { box-shadow: 0 0 0 1px var(--rec), 0 0 0 0 color-mix(in srgb, var(--rec) 35%, transparent); }
                    100% { box-shadow: 0 0 0 1px var(--rec), 0 0 0 14px transparent; } }
  .rec-meta { min-width: 0; flex: 1; }
  .rec-meta h2, .drop h2 { font: 600 var(--fs-15)/20px var(--font-display); letter-spacing: -.005em; }
  .rec-meta > p { color: var(--text-2); margin: 2px 0 var(--sp-5); max-width: 48ch; }
  .rec-live { display: flex; align-items: center; gap: var(--sp-4); color: var(--rec) !important; font-weight: 500; }
  .pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--rec); animation: pulse 1.4s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .35; } }
  .mic-pick { position: relative; display: flex; align-items: center; color: var(--text-3); max-width: 300px; }
  .mic-pick :global(.icon) { position: absolute; left: var(--sp-4); pointer-events: none; }
  .mic-pick .select { color: var(--text); padding-left: 28px; }
  .below { margin-top: var(--sp-4); }

  .drop-card { display: flex; flex-direction: column; border: 1.5px dashed var(--line-control); border-radius: var(--r-lg);
    transition: background var(--t-fast), border-color var(--t-fast); min-width: 0; }
  .drop-card:hover, .drop-card.dragging { background: var(--surface); border-color: var(--accent); }
  .drop-card.dragging { background: var(--accent-bg); }
  .drop-card.has-file { border-style: solid; border-color: var(--line-strong); background: var(--surface); }
  .drop { position: relative; flex: 1; display: flex; align-items: center; gap: var(--sp-6); padding: var(--sp-7) var(--sp-8); cursor: pointer; }
  .drop input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; }
  .ico { width: 44px; height: 44px; border-radius: 12px; background: var(--surface-2); display: grid; place-items: center; color: var(--text-2); flex: none; }
  .drop-txt { min-width: 0; display: block; }
  .link { color: var(--accent); }
  .desc { display: block; color: var(--text-3); font-size: var(--fs-12); margin-top: 2px; }
  .fmts { display: flex; gap: 4px; flex-wrap: wrap; margin-top: var(--sp-4); }
  .file-row { display: flex; align-items: center; gap: var(--sp-4); padding: var(--sp-4) var(--sp-5) var(--sp-4) var(--sp-8);
    border-top: 1px solid var(--line); color: var(--text-2); }
  .file { flex: 1; min-width: 0; color: var(--text); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .drop-card > .note { margin: 0 var(--sp-5) var(--sp-5); }

  .list { list-style: none; margin: 0; padding: 0; overflow: hidden; }
  .item { display: flex; gap: var(--sp-5); align-items: center; padding: var(--sp-4) var(--sp-6); min-height: 52px; border-bottom: 1px solid var(--line); }
  .item:last-child { border-bottom: 0; }
  .item:hover { background: color-mix(in srgb, var(--surface-2) 50%, transparent); }
  .src-ico { width: 28px; height: 28px; border-radius: 7px; display: grid; place-items: center; background: var(--surface-2); color: var(--text-2); flex: none; }
  .item-main { flex: 1; min-width: 0; }
  .item-main .input { height: 26px; }
  .title-btn { border: 0; background: none; padding: 0; font-weight: 500; text-align: left; cursor: pointer; color: var(--text);
    max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
  .title-btn:hover:not(:disabled) { color: var(--accent); }
  .meta { font-size: var(--fs-12); color: var(--text-3); font-variant-numeric: tabular-nums; }
  .item-side { display: flex; align-items: center; gap: var(--sp-4); flex-wrap: wrap; justify-content: flex-end; }
  .job { display: flex; align-items: center; gap: var(--sp-4); margin-top: var(--sp-3); font-size: var(--fs-12); }
  .job .bar { flex: 0 0 160px; }
  .err { color: var(--danger); margin-top: var(--sp-2); }
  @media (max-width: 600px) {
    .item { flex-wrap: wrap; }
    .item-side { justify-content: flex-start; width: 100%; padding-left: 40px; }
    .rec-card, .drop { padding: var(--sp-6); }
  }
</style>
