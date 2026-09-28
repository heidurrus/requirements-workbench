<script>
  // The focused atom in full, next to the list on wide windows (design-system §7.10): the statement,
  // the evidence in context (the lines around each quote), its facts, its history and the actions.
  import Icon from "./Icon.svelte";
  import { api } from "../lib/api.js";
  import { fmtTime, speakerDisplay } from "../lib/format.js";
  import { app, t, go } from "../lib/state.svelte.js";

  let { atom, statementOf = {}, onDecide, onEdit } = $props();

  const cache = new Map();                // source id → segments
  let context = $state([]);               // [{ev, lines:[{idx, text, speaker, start, hit}]}]
  let history = $state([]);

  async function segmentsOf(sourceId) {
    if (!cache.has(sourceId)) cache.set(sourceId, api(`/api/sources/${sourceId}`).then(s => s.segments).catch(() => []));
    return cache.get(sourceId);
  }
  $effect(() => {
    const a = atom;
    if (!a) { context = []; history = []; return; }
    Promise.all(a.evidence.map(async ev => {
      const segs = await segmentsOf(ev.source_id);
      const i = segs.findIndex(s => s.idx === ev.segment_idx);
      const lines = i < 0 ? [] : segs.slice(Math.max(0, i - 1), i + 2).map(s => ({ ...s, hit: s.idx === ev.segment_idx }));
      return { ev, lines };
    })).then(c => { if (atom?.id === a.id) context = c; });
    api(`/api/audit?entity=atom&entity_id=${a.id}&limit=20`).then(b => { if (atom?.id === a.id) history = b.entries; }).catch(() => {});
  });

  function mark(text, quote) {
    const i = text.toLowerCase().indexOf((quote || "").toLowerCase());
    if (!quote || i < 0) return [{ t: text }];
    return [{ t: text.slice(0, i) }, { t: text.slice(i, i + quote.length), m: true }, { t: text.slice(i + quote.length) }];
  }
  const typeClass = { functional: "fr", nfr: "nfr", question: "q" };
  const hText = e => (t("at.h." + e.action) === "at.h." + e.action ? e.action : t("at.h." + e.action));
</script>

{#if atom}
  <aside class="inspector card" aria-label={t("at.inspector")}>
    <div class="head">
      <span class="tag {typeClass[atom.type]}">{t("at.type." + atom.type)}</span>
      {#if atom.status === "accepted"}<span class="status ok"><Icon name="check" size={12} /> {t("at.status.accepted")}</span>
      {:else if atom.status === "rejected"}<span class="status">{t("at.status.rejected")}{#if atom.reject_reason} · {t("at.reason." + atom.reject_reason)}{/if}</span>
      {:else}<span class="status run">{t("at.f.pending")}</span>{/if}
    </div>
    <p class="stmt">{atom.statement}</p>
    {#if atom.statement !== atom.original_statement}<p class="hint">{t("at.was", { text: atom.original_statement })}</p>{/if}

    {#each context as c (c.ev.id)}
      <div class="ctx">
        <p class="src">
          <button class="link" onclick={() => go(`/source/${c.ev.source_id}/seg/${c.ev.segment_idx}`)}>{c.ev.source_title}</button>
          {#if c.ev.start != null}<span class="t3 num"> · {fmtTime(c.ev.start)}</span>{/if}
        </p>
        {#each c.lines as l (l.idx)}
          <p class:hit={l.hit}>
            {#if l.start != null}<span class="time">{fmtTime(l.start)}</span>{/if}
            {#if l.speaker}<b class="who">{speakerDisplay(l.speaker, l.speaker_name, t)}:</b>{/if}
            {#if l.hit}{#each mark(l.text, c.ev.quote) as part, k (k)}{#if part.m}<mark>{part.t}</mark>{:else}{part.t}{/if}{/each}{:else}{l.text}{/if}
          </p>
        {:else}
          <p class="hit">«{c.ev.quote}»</p>
        {/each}
      </div>
    {/each}
    {#if !atom.evidence.length}<p class="hint">{atom.origin === "ba" ? t("at.ba_origin") : ""}</p>{/if}

    <dl class="kv">
      {#if atom.priority}<dt>{t("at.priority")}</dt><dd>{t("at.prio." + atom.priority)}</dd>{/if}
      {#if atom.type === "question"}<dt>{t("oi.questions")}</dt><dd>{t("oi.st." + (atom.q_state || "open"))}{#if atom.answer} — {atom.answer}{/if}</dd>{/if}
      {#each atom.conflicts as c (c.id)}
        <dt class="danger-t">{t("at.conflicts")}</dt><dd>{c.description}{#if statementOf[c.other]}<span class="t3"> — {statementOf[c.other]}</span>{/if}</dd>
      {/each}
      {#if atom.model}<dt>{t("at.model")}</dt><dd class="t3">{atom.model}</dd>{/if}
    </dl>

    <div class="acts">
      <button class="btn btn-primary" onclick={() => onDecide(atom, "accepted")}><Icon name="check" size={14} /> {t("at.accept")} <span class="kbd">A</span></button>
      <button class="btn" onclick={() => onDecide(atom, "rejected")}><Icon name="close" size={14} /> {t("at.reject")} <span class="kbd">X</span></button>
      <button class="btn btn-ghost" onclick={() => onEdit(atom)}><Icon name="pencil" size={14} /> {t("at.edit")} <span class="kbd">E</span></button>
    </div>

    {#if history.length}
      <p class="h-title">{t("at.history")}</p>
      <ol class="hist">
        {#each history as h, i (i)}<li><span class="t3 num">{new Date(h.at * 1000).toLocaleString(app.lang)}</span> {hText(h)}</li>{/each}
      </ol>
    {/if}
  </aside>
{/if}

<style>
  .inspector { position: sticky; top: calc(var(--toolbar) + var(--sp-4)); padding: var(--sp-6); max-height: calc(100vh - var(--toolbar) - 32px);
    overflow-y: auto; display: flex; flex-direction: column; gap: var(--sp-5); }
  .head { display: flex; align-items: center; gap: var(--sp-4); }
  .stmt { font: 600 var(--fs-15)/22px var(--font-display); }
  .ctx { border-radius: var(--r-md); background: var(--surface-2); padding: var(--sp-4) var(--sp-5); font-size: var(--fs-13); line-height: 19px; }
  .ctx p { padding: 3px 0; color: var(--text-2); }
  .ctx p.hit { color: var(--text); }
  .ctx .src { font-size: var(--fs-12); padding-bottom: var(--sp-2); }
  .time { font: 11px var(--mono); color: var(--text-3); margin-right: 6px; }
  .who { font-weight: 600; margin-right: 4px; }
  .link { border: 0; background: none; padding: 0; color: var(--accent); cursor: pointer; font: inherit; font-weight: 500; }
  .kv { display: grid; grid-template-columns: 110px 1fr; gap: 6px var(--sp-5); font-size: 12.5px; margin: 0; }
  .kv dt { color: var(--text-3); } .kv dd { margin: 0; min-width: 0; }
  .danger-t { color: var(--danger) !important; }
  .acts { display: flex; gap: var(--sp-3); flex-wrap: wrap; }
  .h-title { font-size: var(--fs-11); font-weight: 600; color: var(--text-3); }
  .hist { margin: 0; padding-left: 18px; font-size: var(--fs-12); line-height: 18px; }
</style>
