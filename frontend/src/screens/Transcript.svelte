<script>
  import Block from "../components/Block.svelte";
  import Icon from "../components/Icon.svelte";
  import { api, pollJob } from "../lib/api.js";
  import { extractAtoms } from "../lib/atoms.js";
  import { fmtTime, fmtDate, fmtDuration, renderMarkdown, speakerClass, speakerDisplay } from "../lib/format.js";
  import { saveText } from "../lib/save.js";
  import { app, t, go, loadSources, toast, rememberSource } from "../lib/state.svelte.js";

  let { id, autoSummarize = false, focusSeg = null } = $props();

  let source = $state(null);
  let loadError = $state("");
  let audio = $state(null);
  let playing = $state(false);
  let now = $state(0);
  let duration = $state(0);

  let summaryText = $state("");
  let summaryMeta = $state("");
  let summaryError = $state("");
  let summarizing = $state(false);
  let summaryStarted = $state(0);
  let tick = $state(0);

  let editingTitle = $state(false);
  let titleDraft = $state("");
  let names = $state({});
  let copied = $state(false);

  async function load() {
    loadError = "";
    try {
      source = await api(`/api/sources/${id}`);
      names = { ...source.speaker_names };
      summaryText = source.summary?.text || "";
      summaryMeta = source.summary ? t("tr.summarised_with", { model: source.summary.model }) : "";
      rememberSource(id);
    } catch (err) {
      source = null;
      loadError = err.message;
    }
  }

  // Reload when the route points at another source; keep polling while it's being processed.
  $effect(() => {
    const current = id;
    let stop = false;
    load().then(async () => {
      if (autoSummarize && source?.status === "ready" && !summaryText) summarize();
      if (focusSeg != null) showSegment(focusSeg);
      while (!stop && source && source.id === current && source.status === "processing") {
        await new Promise(r => setTimeout(r, 2000));
        if (!stop) await load();
      }
    });
    return () => { stop = true; };
  });

  const speakerOrder = $derived(source ? [...new Set(source.segments.map(s => s.speaker).filter(Boolean))] : []);
  // Documents and emails have no timing: shown as paragraphs, without the time column.
  const isText = $derived(source ? !source.segments.some(s => s.start != null) : false);
  const blockTitle = $derived(source?.kind === "email" ? t("tr.block.email")
    : source?.kind === "document" ? t("tr.block.document") : t("nav.transcript"));
  const email = $derived(source?.meta?.email || null);
  const activeIdx = $derived.by(() => {
    if (!source || !playing && !now) return -1;
    const segs = source.segments;
    for (let i = segs.length - 1; i >= 0; i--) if (segs[i].start != null && segs[i].start <= now + 0.05) return segs[i].idx;
    return -1;
  });

  // Opened from an atom's quote: bring its line into view and mark it briefly.
  let flashIdx = $state(null);
  function showSegment(idx) {
    const seg = source?.segments.find(s => s.idx === idx);
    if (!seg) return;
    flashIdx = idx;
    requestAnimationFrame(() => document.getElementById(`seg-${idx}`)?.scrollIntoView({ block: "center" }));
    if (audio && seg.start != null) audio.currentTime = seg.start;
    setTimeout(() => (flashIdx = null), 2400);
  }

  const atomCount = $derived(app.sources.find(s => s.id === id)?.atom_count || 0);

  function seek(seconds) {
    if (!audio || seconds == null) return;
    audio.currentTime = seconds;
    audio.play();
  }
  function togglePlay() { if (!audio) return; audio.paused ? audio.play() : audio.pause(); }

  $effect(() => {
    // Keep the playing line in view.
    if (activeIdx < 0 || !playing) return;
    document.getElementById(`seg-${activeIdx}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });

  async function saveTitle() {
    editingTitle = false;
    const title = titleDraft.trim();
    if (!title || title === source.title) return;
    try { source = { ...source, ...(await api(`/api/sources/${id}`, { method: "PATCH", body: { title } })) }; loadSources(); }
    catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function renameSpeaker(label) {
    const name = (names[label] || "").trim();
    if ((source.speaker_names[label] || "") === name) return;
    try {
      await api(`/api/sources/${id}/speakers/${encodeURIComponent(label)}`, { method: "PUT", body: { name } });
      await load();
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function summarize() {
    summarizing = true;
    summaryError = "";
    summaryText = "";
    summaryStarted = Date.now();
    const timer = setInterval(() => (tick = Math.round((Date.now() - summaryStarted) / 1000)), 500);
    try {
      const { job_id } = await api("/summarize", { method: "POST", body: { source_id: id } });
      const job = await pollJob(job_id, j => { if (j.partial) summaryText = j.partial; }, { interval: 600 });
      summaryText = job.result.summary;
      summaryMeta = t("tr.summarised_with", { model: job.result.model });
      loadSources();
    } catch (err) {
      summaryError = err.message;
      if (err.body?.needs_setup || /API key|Settings/.test(err.message)) {
        toast(err.message, { action: t("nav.settings"), onAction: () => go("/settings"), kind: "danger" });
      }
    } finally {
      clearInterval(timer);
      summarizing = false;
    }
  }

  async function retranscribe() {
    const o = app.options;
    try {
      const res = await api(`/api/sources/${id}/transcribe`, { method: "POST", body: {
        model: o.model, device: o.device, diarize: String(o.diarize), word_timestamps: String(!o.diarize && o.word_timestamps) } });
      await load();
      pollJob(res.job_id).finally(() => { load(); loadSources(); });
    } catch (err) { toast(err.message, { kind: "danger" }); }
  }

  async function copyText() {
    await navigator.clipboard.writeText(source.text);
    copied = true;
    setTimeout(() => (copied = false), 1500);
  }

  const meta = $derived(source ? [fmtDate(source.created_at, app.lang), t("kind." + source.kind), fmtDuration(source.duration, app.lang),
    source.speakers && !["email", "document"].includes(source.kind) ? t("meta.speakers", { n: source.speakers }) : null,
    source.asr_model || source.import_format]
    .filter(Boolean).join(" · ") : "");
</script>

<div class="screen-inner">
  {#if !id}
    <div class="empty panel"><p>{t("tr.none")}</p>
      <button class="btn" style="margin-top: var(--s-3)" onclick={() => go("/sources")}>{t("tr.back")}</button></div>
  {:else if loadError}
    <div class="note danger">{loadError}</div>
  {:else if source}
    <header class="screen-head">
      <div class="head-main">
        <button class="btn btn-ghost icon-btn back" onclick={() => go("/sources")} aria-label={t("tr.back")} title={t("tr.back")}>
          <Icon name="back" />
        </button>
        <div class="head-txt">
          {#if editingTitle}
            <!-- svelte-ignore a11y_autofocus -->
            <input class="input title-input" bind:value={titleDraft} autofocus onblur={saveTitle} aria-label={t("tr.edit_title")}
                   onkeydown={e => { if (e.key === "Enter") saveTitle(); if (e.key === "Escape") editingTitle = false; }} />
          {:else}
            <h1 class="screen-title">
              <button class="title-btn" title={t("tr.edit_title")} onclick={() => { titleDraft = source.title; editingTitle = true; }}>
                {source.title} <span class="pen"><Icon name="pencil" size={12} /></span>
              </button>
            </h1>
          {/if}
          <p class="screen-sub">{meta}{#if email && (email.from || email.to)}{" · "}{#if email.from}{t("tr.email_from")}: {email.from}{/if}{email.from && email.to ? " · " : ""}{#if email.to}{t("tr.email_to")}: {email.to}{/if}{/if}</p>
        </div>
      </div>
      <div class="actions">
        {#if source.audio_url && source.status !== "processing"}
          <button class="btn btn-ghost" onclick={retranscribe}>{source.status === "ready" ? t("tr.retranscribe") : t("tr.transcribe")}</button>
        {/if}
        {#if source.status === "ready"}
          <button class="btn icon-btn" onclick={copyText} aria-label={copied ? t("tr.copied") : t("tr.copy")} title={copied ? t("tr.copied") : t("tr.copy")}>
            <Icon name={copied ? "check" : "copy"} /></button>
          <button class="btn icon-btn" onclick={() => saveText(`${source.title}.txt`, source.text)} aria-label={t("tr.export")} title={t("tr.export")}>
            <Icon name="download" /></button>
          <span class="tb-sep"></span>
          <button class="btn" class:btn-primary={!summaryText && !atomCount} onclick={summarize} disabled={summarizing}>
            {#if summarizing}<span class="spinner"></span>{/if}{summaryText ? t("tr.resummarize") : t("tr.summarize")}
          </button>
          <button class="btn" class:btn-primary={!!summaryText || !!atomCount} onclick={() => atomCount ? go(`/atoms/source/${id}`) : extractAtoms(id)}
                  disabled={!!app.extracting[id]} title={atomCount ? "" : t("at.extract")}>
            {#if app.extracting[id]}<span class="spinner"></span> {app.extracting[id].message}
            {:else if atomCount}{t("at.count", { n: atomCount })} <Icon name="arrow" size={14} />
            {:else}{t("at.extract")}{/if}
          </button>
        {/if}
      </div>
    </header>

    {#if source.status === "processing"}
      <p class="note"><span class="spinner"></span> {t("tr.processing")}</p>
    {:else if source.status === "recorded"}
      <p class="note warn">{t("tr.recorded")}</p>
    {:else if source.status === "failed"}
      <p class="note danger">{t("tr.failed", { error: source.error || "" })}</p>
    {/if}

    {#if source.audio_url}
      <div class="player card">
        <audio bind:this={audio} src={source.audio_url} preload="metadata"
               ontimeupdate={() => (now = audio.currentTime)} onloadedmetadata={() => (duration = audio.duration)}
               onplay={() => (playing = true)} onpause={() => (playing = false)}></audio>
        <button class="btn btn-primary icon-btn" onclick={togglePlay} aria-label={playing ? t("tr.pause") : t("tr.play")}>
          <Icon name={playing ? "pause" : "play"} />
        </button>
        <span class="mono num">{fmtTime(now)}</span>
        <input class="scrub" type="range" min="0" max={duration || 0} step="0.1" value={now}
               oninput={e => { audio.currentTime = Number(e.currentTarget.value); }} aria-label="Seek" />
        <span class="mono faint">{fmtTime(duration)}</span>
      </div>
    {/if}

    {#if source.status === "ready"}
      <div class="layout">
        <div class="stack main-col">
          {#if speakerOrder.length && !isText}
            <Block id="tr-speakers" title={t("tr.speakers")} meta={String(speakerOrder.length)}>
              <p class="hint" style="margin-bottom: var(--s-3)">{t("tr.speaker_hint")}</p>
              <div class="speakers">
                {#each speakerOrder as label (label)}
                  <label class="speaker">
                    <span class="spk {speakerClass(label, speakerOrder)}">{speakerDisplay(label, null, t)}</span>
                    <input class="input" bind:value={names[label]} placeholder={speakerDisplay(label, null, t)}
                           onblur={() => renameSpeaker(label)} onkeydown={e => e.key === "Enter" && e.currentTarget.blur()} />
                  </label>
                {/each}
              </div>
            </Block>
          {/if}

          <Block id="tr-transcript" title={blockTitle}
                 meta={isText ? t("meta.paragraphs", { n: source.segments.length }) : t("meta.segments", { n: source.segments.length })}>
            {#if !source.segments.length}
              <p class="muted">{t("tr.no_segments")}</p>
            {:else}
              <div class="segments" class:prose={isText}>
                {#each source.segments as seg (seg.idx)}
                  {#if isText}
                    <p class="para" id="seg-{seg.idx}" class:flash={seg.idx === flashIdx}>{seg.text}</p>
                  {:else}
                  <div class="seg-row" class:active={seg.idx === activeIdx} class:flash={seg.idx === flashIdx} id="seg-{seg.idx}">
                    <div class="seg-meta">
                      {#if seg.start != null}
                        <button class="time" disabled={!source.audio_url} onclick={() => seek(seg.start)}>{fmtTime(seg.start)}</button>
                      {/if}
                      {#if seg.speaker}<span class="spk {speakerClass(seg.speaker, speakerOrder)}" title={speakerDisplay(seg.speaker, seg.speaker_name, t)}>{speakerDisplay(seg.speaker, seg.speaker_name, t)}</span>{/if}
                    </div>
                    <p class="seg-text">{seg.text}</p>
                  </div>
                  {/if}
                {/each}
              </div>
            {/if}
          </Block>
        </div>

        <div class="side-col">
          <Block id="tr-summary" title={t("tr.summary")} meta={summaryMeta}>
            {#if summaryText}
              <div class="md">{@html renderMarkdown(summaryText)}</div>
            {:else if !summarizing && !summaryError}
              <p class="muted">{t("tr.no_summary")}</p>
            {/if}
            {#if summarizing && !summaryText}<p class="hint"><span class="spinner"></span> {t("tr.writing", { s: tick })}</p>{/if}
            {#if summaryError}<p class="note danger">{summaryError}</p>{/if}
          </Block>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .head-main { min-width: 0; flex: 1; display: flex; align-items: center; gap: var(--sp-4); }
  .head-txt { min-width: 0; flex: 1; }
  .back { flex: none; margin-left: -6px; }
  .screen-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .title-btn { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: text; text-align: left; max-width: 100%; }
  .title-btn .pen { color: var(--text-3); opacity: 0; display: inline-block; vertical-align: middle; transition: opacity var(--t-fast); }
  .title-btn:hover .pen, .title-btn:focus-visible .pen { opacity: 1; }
  .title-input { font: 600 var(--fs-15)/20px var(--font-display); max-width: 520px; }
  .screen-sub { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tb-sep { width: 1px; height: 18px; background: var(--line-strong); margin: 0 var(--sp-2); }

  .player { display: flex; align-items: center; gap: var(--sp-5); margin-bottom: var(--sp-6); padding: var(--sp-4) var(--sp-5);
    position: sticky; top: calc(var(--toolbar) + var(--sp-2)); z-index: 10; }
  .player .icon-btn { border-radius: 50%; width: 32px; height: 32px; }
  .scrub { flex: 1; min-width: 80px; accent-color: var(--accent); }
  .layout { display: grid; gap: var(--sp-8); grid-template-columns: minmax(0, 1fr) 340px; align-items: start; }
  /* Sticky, but never taller than the window: a long summary scrolls inside its column. */
  .side-col { position: sticky; top: calc(var(--toolbar) + var(--sp-4));
    max-height: calc(100vh - var(--toolbar) - var(--sp-8)); overflow-y: auto; overscroll-behavior: contain;
    border-radius: var(--r-lg); scrollbar-width: thin; }
  .side-col :global(details.block > summary) { position: sticky; top: 0; z-index: 1; background: var(--surface); }
  @media (max-width: 1120px) {
    .layout { grid-template-columns: 1fr; }
    .side-col { position: static; order: -1; max-height: none; overflow: visible; }
  }

  .speakers { display: grid; gap: var(--sp-4); grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr)); }
  .speaker { display: flex; align-items: center; gap: var(--sp-4); }
  .spk { display: inline-flex; align-items: center; gap: 6px; height: 20px; font-size: var(--fs-12); font-weight: 600; min-width: 0;
    white-space: nowrap; max-width: 180px; overflow: hidden; text-overflow: ellipsis; flex: none; }
  .spk::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; flex: none; }

  .segments { display: flex; flex-direction: column; margin: 0 calc(-1 * var(--sp-6)) calc(-1 * var(--sp-6)); }
  .seg-row { display: grid; grid-template-columns: 56px 120px minmax(0, 1fr); gap: var(--sp-5); padding: var(--sp-5) var(--sp-6);
    border-top: 1px solid var(--line); scroll-margin: 120px; font-size: var(--fs-14); line-height: 20px; }
  .seg-row.active { background: var(--accent-bg); }
  .seg-row:last-child { border-radius: 0 0 var(--r-lg) var(--r-lg); }
  .seg-meta { display: contents; }
  .time { border: 0; background: none; padding: 0; font: 12px/20px var(--mono); color: var(--text-3); cursor: pointer; text-align: left; align-self: start; }
  .time:hover:not(:disabled) { color: var(--accent); }
  .time:disabled { cursor: default; }
  .seg-text { min-width: 0; grid-column: 3; }
  .prose { max-width: 72ch; margin: 0; }
  .para { font-size: var(--fs-15); line-height: 24px; margin: 0 0 var(--sp-5); scroll-margin: 120px; border-radius: var(--r-sm); }
  .para:last-child { margin-bottom: 0; }
  .flash { background: var(--mark) !important; transition: background .6s ease; }
  @media (max-width: 600px) {
    .seg-row { grid-template-columns: 56px minmax(0, 1fr); }
    .seg-text { grid-column: 1 / -1; }
  }
</style>
