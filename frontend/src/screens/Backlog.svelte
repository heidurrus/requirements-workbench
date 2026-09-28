<script>
  import Icon from "../components/Icon.svelte";
  import { explain } from "../lib/errors.js";
  import { api, pollJob } from "../lib/api.js";
  import { app, t, go, toast } from "../lib/state.svelte.js";
  import { SvelteSet } from "svelte/reactivity";

  const collapsed = new SvelteSet();          // item ids folded in this session
  const fold = id => (collapsed.has(id) ? collapsed.delete(id) : collapsed.add(id));
  const glyph = { epic: "E", story: "S", subtask: "T", nfr: "N" };

  let body = $state(null);
  let error = $state("");
  let job = $state(null);                // {kind, progress, message}
  let editing = $state(null);            // {id, title, body, goal, acceptance}

  async function load() {
    const pid = app.currentProjectId;
    try {
      const b = await api(`/api/projects/${pid}/backlog`);
      if (pid !== app.currentProjectId) return;
      body = b;
      error = "";
      if (b.running && !job) follow(b.running, "build");
    } catch (err) { error = err.message; }
  }
  $effect(() => { app.currentProjectId; load(); });

  const items = $derived(body?.items || []);
  const byParent = $derived.by(() => {
    const m = {};
    for (const i of items) (m[i.parent_id || "root"] ||= []).push(i);
    return m;
  });
  const epics = $derived((byParent.root || []).filter(i => i.kind !== "nfr"));
  const nfrs = $derived(items.filter(i => i.kind === "nfr"));
  const storyTitle = $derived(Object.fromEntries(items.filter(i => i.kind === "story").map(i => [i.id, i.title])));
  const hasFindings = $derived(items.some(i => i.kind === "story" && i.invest?.length));

  function fail(err) {
    const e = explain(err);
    toast(e.message, { kind: "danger", ...(e.setup ? { action: t("err.open_settings"), onAction: () => go("/settings") } : {}) });
  }
  async function follow(jobId, kind) {
    job = { kind, progress: 0, message: "" };
    try {
      const j = await pollJob(jobId, x => (job = { kind, progress: x.progress || 0, message: x.progress_msg || "" }), { interval: 800 });
      if (kind === "invest") toast(t("bl.invest_done", { n: j.result.with_findings }));
      else {
        const bits = [t("bl.built", { n: j.result.stories })];
        const linked = items.filter(i => i.jira_key).length;
        if (j.result.matched && linked) bits.push(t("bl.kept_links", { n: linked }));
        if (j.result.orphans?.length) bits.push(t("bl.orphans", { n: j.result.orphans.length }));
        toast(bits.join(" · "), j.result.orphans?.length ? { action: t("nav.export"), onAction: () => go("/export") } : {});
      }
    } catch (err) { fail(err); }
    finally { job = null; load(); }
  }
  let refineOpen = $state(false);
  let refineNote = $state("");
  async function run(kind, note = null) {
    refineOpen = false;
    try {
      const { job_id } = await api(`/api/projects/${app.currentProjectId}/backlog/${kind}`, { method: "POST",
                                                                                          body: note ? { note } : {} });
      follow(job_id, kind);
    } catch (err) { fail(err); }
  }

  async function include(item, on) {
    try { body = { ...body, ...(await api(`/api/projects/${app.currentProjectId}/backlog/include`,
      { method: "POST", body: { ids: [item.id], included: on } })) }; }
    catch (err) { fail(err); }
  }
  async function move(item, direction) {
    try { body = await api(`/api/backlog/${item.id}/move`, { method: "POST", body: { direction } }); }
    catch (err) { fail(err); }
  }
  async function remove(item) {
    try {
      await api(`/api/backlog/${item.id}`, { method: "DELETE" });
      await load();
      toast(t("bl.deleted", { title: item.title }), { action: t("at.undo"), onAction: async () => {
        await api(`/api/backlog/${item.id}/restore`, { method: "POST" });
        load();
      } });
    } catch (err) { fail(err); }
  }
  async function add(kind, parent) {
    try {
      const it = await api(`/api/projects/${app.currentProjectId}/backlog`, { method: "POST",
        body: { kind, title: t("bl.new." + kind), parent_id: parent?.id || null } });
      await load();
      startEdit(it);
    } catch (err) { fail(err); }
  }
  function startEdit(item) {
    editing = { id: item.id, title: item.title, body: item.body, goal: item.goal,
                acceptance: (item.acceptance || []).map(a => ({ ...a })) };
  }
  async function saveEdit(item) {
    const e = editing;
    editing = null;
    const changes = {};
    for (const k of ["title", "body", "goal"]) if ((e[k] ?? "") !== (item[k] ?? "")) changes[k] = e[k];
    if (JSON.stringify(e.acceptance) !== JSON.stringify(item.acceptance || [])) changes.acceptance = e.acceptance;
    if (!Object.keys(changes).length) return;
    try { await api(`/api/backlog/${item.id}`, { method: "PATCH", body: changes }); load(); }
    catch (err) { fail(err); }
  }
  async function setPriority(item, priority) {
    try { await api(`/api/backlog/${item.id}`, { method: "PATCH", body: { priority: priority || null } }); load(); }
    catch (err) { fail(err); }
  }
  async function applyFix(item, fix) {
    try { await api(`/api/backlog/${item.id}`, { method: "PATCH", body: { body: fix } }); load(); toast(t("bl.fix_applied")); }
    catch (err) { fail(err); }
  }
  async function moveInto(nfr, storyId) {
    try {
      await api(`/api/backlog/${nfr.id}/move-into/${storyId}`, { method: "POST" });
      load();
      toast(t("bl.moved_into", { title: storyTitle[storyId] || "" }));
    } catch (err) { fail(err); }
  }
  const refLabel = r => `FRD ${r.section} · ${r.id}`;
  const children = id => byParent[id] || [];
</script>

<div class="screen-inner">
  <header class="screen-head">
    <div>
      <h1 class="screen-title">{t("nav.decomposition")}</h1>
      <p class="screen-sub">
        {#if body && items.length}{t("bl.sub", { e: body.counts.epic, s: body.counts.story, t: body.counts.subtask, n: body.included })}
        {:else}{t("bl.sub_empty")}{/if}
      </p>
    </div>
    {#if body && body.latest}
      <div class="actions">
        {#if items.length}
          <button class="btn btn-ghost" onclick={() => (refineOpen = !refineOpen)} title={t("ai.refine_hint")}>{t("ai.refine")}</button>
          <button class="btn" class:btn-ghost={!body.stale} disabled={!!job} onclick={() => run("build")}>
            <Icon name="refresh" size={14} /> {t("bl.rebuild")}</button>
          <button class="btn" disabled={!!job} onclick={() => run("invest")}><Icon name="check" size={14} /> {t("bl.invest")}</button>
          <button class="btn btn-primary" onclick={() => go("/export")}>{t("bl.to_export")} <Icon name="arrow" size={14} /></button>
        {:else}
          <button class="btn btn-primary" disabled={!!job} onclick={() => run("build")}>{t("bl.build")}</button>
        {/if}
      </div>
    {/if}
  </header>

  {#if error}<p class="note danger">{error}</p>{/if}

  {#if body}
    <div class="stack">
      {#if job}
        <div class="banner info running"><span class="spinner"></span>
          <span class="num">{job.message}</span>
          <div class="grow"><div class="bar"><i style="width: {job.progress}%"></i></div></div></div>
      {/if}

      {#if refineOpen}
        <div class="card refine">
          <!-- svelte-ignore a11y_autofocus -->
          <textarea class="input" rows="2" bind:value={refineNote} autofocus placeholder={t("ai.refine_ph.backlog")} aria-label={t("ai.refine")}></textarea>
          <div class="actions"><span class="hint">{t("bl.refine_hint")}</span><span class="spacer"></span>
            <button class="btn btn-sm btn-ghost" onclick={() => (refineOpen = false)}>{t("at.cancel")}</button>
            <button class="btn btn-sm btn-primary" disabled={!refineNote.trim() || !!job} onclick={() => run("build", refineNote)}>{t("ai.refine_run")}</button>
          </div>
        </div>
      {/if}

      {#if !body.latest}
        <div class="card empty">
          <div class="glyph"><Icon name="tree" /></div>
          <p class="panel-title">{t("bl.no_doc_title")}</p>
          <p>{t("bl.no_doc")}</p>
          <button class="btn btn-lg btn-primary" onclick={() => go("/document")}>{t("bl.to_doc")}</button>
        </div>
      {:else if !items.length}
        <div class="card empty">
          <div class="glyph"><Icon name="tree" /></div>
          <p class="panel-title">{t("bl.ready_title", { v: body.latest })}</p>
          <p>{t("bl.ready")}</p>
        </div>
      {:else}
        {#if body.stale}
          <p class="banner warn row-note"><Icon name="warn" /><span class="grow">{t("bl.stale", { a: body.built_from, b: body.latest })}</span>
            <button class="btn btn-sm" disabled={!!job} onclick={() => run("build")}>{t("bl.rebuild")}</button></p>
        {/if}
        <p class="hint-line"><Icon name="info" size={12} /> {t("bl.hint")}{#if hasFindings}{" "}<b class="warn-t">{t("bl.findings_hint")}</b>{/if}</p>

        <div class="tree" role="tree" aria-label={t("nav.decomposition")}>
          {#each epics as epic (epic.id)}
            <div class="node epic" class:off={!epic.included} class:folded={collapsed.has(epic.id)} role="treeitem" aria-selected="false"
                 aria-expanded={!collapsed.has(epic.id)}>
              {@render row(epic, children(epic.id).length > 0)}
              {#if !collapsed.has(epic.id)}
                <div class="kids" role="group">
                  {#each children(epic.id) as story (story.id)}
                    <div class="node story" class:off={!story.included} role="treeitem" aria-selected="false"
                         aria-expanded={!collapsed.has(story.id)}>
                      {@render row(story, true)}
                      {#if !collapsed.has(story.id) && children(story.id).length}
                        <div class="kids" role="group">
                          {#each children(story.id) as sub (sub.id)}
                            <div class="node sub" class:off={!sub.included} role="treeitem" aria-selected="false">{@render row(sub, false)}</div>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  {/each}
                  <button class="btn btn-sm btn-ghost add lvl-1" onclick={() => add("story", epic)}><Icon name="plus" size={14} /> {t("bl.add_story")}</button>
                </div>
              {/if}
            </div>
          {/each}
          <button class="btn btn-sm btn-ghost add" onclick={() => add("epic", null)}><Icon name="plus" size={14} /> {t("bl.add_epic")}</button>
        </div>

        {#if nfrs.length}
          <div>
            <div class="section-h"><h2>{t("bl.nfr_title")}</h2><span class="t3 num">{nfrs.length}</span></div>
            <p class="hint nfr-hint">{t("bl.nfr_hint")}</p>
            <section class="tree">
              {#each nfrs as nfr (nfr.id)}
                <div class="node nfr" class:off={!nfr.included}>
                  {@render row(nfr, false)}
                  {#each nfr.invest || [] as f, i (i)}
                    {#if f.move_to?.length}
                      <div class="moves">
                        {#each f.move_to as sid (sid)}
                          {#if storyTitle[sid]}
                            <button class="btn btn-sm" onclick={() => moveInto(nfr, sid)}><Icon name="arrow" size={12} /> {t("bl.move_into", { title: storyTitle[sid] })}</button>
                          {/if}
                        {/each}
                      </div>
                    {/if}
                  {/each}
                </div>
              {/each}
            </section>
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>

{#snippet row(item, foldable)}
  <div class="row-line">
    <span class="cb-hit"><input type="checkbox" class="inc" checked={item.included} aria-label={item.title}
           onchange={e => include(item, e.currentTarget.checked)} /></span>
    <div class="main">
      {#if editing?.id === item.id}
        <div class="edit">
          <input class="input" bind:value={editing.title} aria-label={t("bl.title")} />
          {#if item.kind === "epic"}
            <input class="input" bind:value={editing.goal} placeholder={t("bl.goal")} aria-label={t("bl.goal")} />
          {:else if item.kind === "story"}
            <textarea class="input area" rows="2" bind:value={editing.body} placeholder={t("bl.story_ph")} aria-label={t("bl.story_ph")}></textarea>
            <p class="label">{t("bl.ac")}</p>
            {#each editing.acceptance as ac, i (i)}
              <div class="ac-edit">
                <input class="input" bind:value={ac.given} placeholder={t("bl.given")} aria-label={t("bl.given")} />
                <input class="input" bind:value={ac.when} placeholder={t("bl.when")} aria-label={t("bl.when")} />
                <input class="input" bind:value={ac.then} placeholder={t("bl.then")} aria-label={t("bl.then")} />
                <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")}
                        onclick={() => editing.acceptance.splice(i, 1)}><Icon name="close" size={14} /></button>
              </div>
            {/each}
            <div><button class="btn btn-sm btn-ghost" onclick={() => editing.acceptance.push({ given: "", when: "", then: "" })}>
              <Icon name="plus" size={14} /> {t("bl.add_ac")}</button></div>
          {/if}
          <div class="actions">
            <button class="btn btn-sm btn-primary" disabled={!editing.title.trim()} onclick={() => saveEdit(item)}>{t("at.save")}</button>
            <button class="btn btn-sm btn-ghost" onclick={() => (editing = null)}>{t("at.cancel")}</button>
          </div>
        </div>
      {:else}
        <p class="title">
          {#if foldable}
            <button class="tw" class:open={!collapsed.has(item.id)} onclick={() => fold(item.id)}
                    aria-label={item.title} aria-expanded={!collapsed.has(item.id)}><Icon name="chevron" size={14} /></button>
          {:else}<span class="tw-gap"></span>{/if}
          <span class="ticon {item.kind}" title={t("bl.kind." + item.kind)}>{glyph[item.kind]}</span>
          <span class="t">{item.title}</span>
          {#if item.pinned}<span class="tag outline">{t("bl.edited")}</span>{:else if item.generated}<span class="tag outline">{t("bl.generated")}</span>{/if}
          {#if item.kind === "story" && item.invest?.length}<span class="tag warn">INVEST · {item.invest.map(f => f.letter).join("")}</span>{/if}
          {#if item.jira_key}<a class="jira-chip" href={item.jira_url} target="_blank" rel="noreferrer" title={t("bl.in_jira")}>{item.jira_key}</a>{/if}
          {#if item.kind !== "subtask"}
            <select class="mini" class:set={item.priority} value={item.priority || ""} aria-label={t("at.priority")} title={t("at.prio_hint")}
                    onchange={e => setPriority(item, e.currentTarget.value)}>
              <option value="">{t("at.priority")}…</option>
              {#each ["must", "should", "could", "wont"] as p (p)}<option value={p}>{t("at.prio." + p)}</option>{/each}
            </select>
          {/if}
        </p>
        {#if !collapsed.has(item.id) || !foldable}
          {#if item.kind === "epic" && item.goal}<p class="goal">{t("bl.goal_label")}: {item.goal}</p>{/if}
          {#if item.kind === "story" && item.body}<p class="story-text">{item.body}</p>{/if}
          {#if item.acceptance?.length}
            <div class="acs" role="table" aria-label={t("bl.ac")}>
              <div class="ac-row h" role="row"><b role="columnheader">{t("bl.given")}</b><b role="columnheader">{t("bl.when")}</b><b role="columnheader">{t("bl.then")}</b></div>
              {#each item.acceptance as ac, i (i)}
                <div class="ac-row" role="row"><span role="cell">{ac.given}</span><span role="cell">{ac.when}</span><span role="cell">{ac.then}</span></div>
              {/each}
            </div>
          {/if}
          {#if item.refs?.length}
            <p class="refs">{#each item.refs as r (r.id)}<button class="link" onclick={() => go("/document")}>{refLabel(r)}</button>{/each}</p>
          {/if}
          {#if item.kind === "story"}
            {#each item.invest || [] as f, i (i)}
              <div class="invest">
                <span class="L">{f.letter}</span>
                <div class="grow"><p>INVEST · {f.letter} — {f.reason}</p>{#if f.fix}<p class="fix">{t("bl.fix")}: {f.fix}</p>{/if}</div>
                {#if f.fix}<button class="btn btn-sm" onclick={() => applyFix(item, f.fix)}>{t("bl.apply")}</button>{/if}
              </div>
            {/each}
          {:else if item.kind === "nfr"}
            {#each item.invest || [] as f, i (i)}<p class="hint">INVEST · {f.letter}: {f.reason}</p>{/each}
          {/if}
        {/if}
      {/if}
    </div>
    {#if editing?.id !== item.id}
      <div class="acts row-actions">
        {#if item.kind === "story"}
          <button class="btn btn-ghost btn-sm icon-btn" title={t("bl.add_sub")} aria-label={t("bl.add_sub")} onclick={() => add("subtask", item)}><Icon name="plus" size={14} /></button>
        {/if}
        {#if item.kind !== "nfr"}
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.up")} title={t("sk.sec.up")} onclick={() => move(item, "up")}><Icon name="up" size={14} /></button>
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.down")} title={t("sk.sec.down")} onclick={() => move(item, "down")}><Icon name="down" size={14} /></button>
        {/if}
        <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("at.edit")} title={t("at.edit")} onclick={() => startEdit(item)}><Icon name="pencil" size={14} /></button>
        <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")} title={t("sources.delete")} onclick={() => remove(item)}><Icon name="trash" size={14} /></button>
      </div>
    {/if}
  </div>
{/snippet}

<style>
  .grow { flex: 1; min-width: 0; }
  .spacer { flex: 1; }
  .refine { padding: var(--sp-5); display: flex; flex-direction: column; gap: var(--sp-4); }
  .refine textarea { height: auto; }
  .jira-chip { font: 600 11px/18px var(--mono); padding: 0 6px; border-radius: var(--r-xs); background: var(--accent-bg); color: var(--accent); }
  .jira-chip:hover { text-decoration: none; filter: brightness(0.97); }
  .mini { height: 20px; border: 0; background: transparent; color: var(--text-3); font: 500 var(--fs-11) var(--font); padding: 0 2px;
    border-radius: var(--r-xs); cursor: pointer; }
  .mini:hover { background: var(--surface-2); }
  .mini.set { background: var(--accent-bg); color: var(--accent); }
  .row-line:not(:hover) .mini:not(.set) { opacity: 0; }
  @media (hover: none) { .mini { opacity: 1 !important; } }
  .running { align-items: center; }
  .warn-t { color: var(--warn); font-weight: 500; }
  .hint-line { font-size: var(--fs-12); color: var(--text-3); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .nfr-hint { margin: calc(-1 * var(--sp-2)) 0 var(--sp-4); max-width: 80ch; }
  .section-h { margin-top: var(--sp-4); }

  .tree { background: var(--surface); border-radius: var(--r-lg); box-shadow: var(--e1); overflow: hidden; }
  .node { border-top: 1px solid var(--line); }
  .tree > .node:first-child { border-top: 0; }
  .kids > .node { border-top: 1px solid var(--line); }
  .row-line { display: grid; grid-template-columns: 16px minmax(0, 1fr) auto; gap: var(--sp-5); align-items: start;
    padding: var(--sp-4) var(--sp-6); min-height: 40px; transition: background var(--t-fast); }
  .row-line:hover { background: color-mix(in srgb, var(--surface-2) 50%, transparent); }
  .row-line .cb-hit { margin: -4px -6px; }
  .main { min-width: 0; }
  .story > .row-line .main, .sub > .row-line .main { padding-left: 22px; }
  .sub > .row-line .main { padding-left: 48px; }
  .title { display: flex; align-items: flex-start; gap: 6px; min-height: 20px; line-height: 20px; }
  .title > :not(.t) { flex: none; }
  .title .ticon, .title .tw { margin-top: 1px; }
  .tw { width: 20px; height: 20px; border: 0; background: transparent; border-radius: 4px; display: grid; place-items: center;
    color: var(--text-3); flex: none; padding: 0; cursor: pointer; }
  .tw:hover { background: var(--surface-3); color: var(--text); }
  .tw :global(.icon) { transition: transform var(--t-med) var(--ease); }
  .tw.open :global(.icon) { transform: rotate(90deg); }
  .tw-gap { width: 20px; flex: none; }
  .ticon { width: 18px; height: 18px; border-radius: 4px; display: grid; place-items: center; flex: none; font: 700 10px/1 var(--font); color: #fff; }
  .ticon.epic { background: #7A5AC8; } .ticon.story { background: #3F8A55; } .ticon.subtask { background: #3F7DC0; } .ticon.nfr { background: #1F6770; }
  .t { min-width: 0; }
  .epic > .row-line .t { font-weight: 600; }
  .story > .row-line .t { font-weight: 500; }
  .sub .t { color: var(--text-2); }
  .off > .row-line .t, .off > .row-line .story-text, .off > .row-line .acs { color: var(--text-3); }
  .off > .row-line .ticon { opacity: .5; }
  .goal { margin: 2px 0 0 46px; font-size: var(--fs-12); color: var(--text-2); }
  .story-text, .acs, .refs, .invest { margin-left: 46px; }
  .story-text { margin-top: var(--sp-3); font-size: var(--fs-14); line-height: 21px; max-width: 72ch; }
  .acs { margin-top: var(--sp-5); border-radius: var(--r-md); overflow: hidden; box-shadow: 0 0 0 1px var(--line); max-width: 760px; }
  .ac-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); font-size: 12.5px; line-height: 18px; }
  .ac-row > * { padding: 7px var(--sp-5); border-right: 1px solid var(--line); min-width: 0; overflow-wrap: anywhere; }
  .ac-row > *:last-child { border-right: 0; }
  .ac-row + .ac-row > * { border-top: 1px solid var(--line); }
  .ac-row.h > * { background: var(--surface-2); font-weight: 600; font-size: var(--fs-11); color: var(--text-3); padding: 5px var(--sp-5); }
  .refs { margin-top: var(--sp-4); display: flex; flex-wrap: wrap; gap: 6px; }
  .link { display: inline-flex; align-items: center; padding: 2px 7px; border-radius: var(--r-full); border: 0; background: var(--surface-2);
    color: var(--text-2); cursor: pointer; font: 500 11.5px/16px var(--mono); }
  .link:hover { background: var(--accent-bg); color: var(--accent); }
  .invest { margin-top: var(--sp-5); display: flex; gap: var(--sp-4); align-items: flex-start; padding: var(--sp-4) var(--sp-5);
    border-radius: var(--r-md); background: var(--warn-bg); color: var(--warn); max-width: 760px; font-size: 12.5px; line-height: 18px; }
  .invest .L { width: 20px; height: 20px; border-radius: 5px; background: var(--warn); color: var(--surface); display: grid; place-items: center;
    font: 700 11px var(--font); flex: none; }
  .invest p { color: var(--text); }
  .invest .fix { color: var(--text-2); margin-top: 2px; }
  .invest .btn { margin: -2px 0; }
  .add { margin: var(--sp-2) var(--sp-6) var(--sp-4); color: var(--text-3); }
  .add.lvl-1 { margin-left: calc(var(--sp-6) + 16px + var(--sp-5) + 22px); }
  .edit { display: flex; flex-direction: column; gap: var(--sp-4); }
  .area { resize: vertical; }
  .ac-edit { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) auto; gap: var(--sp-4); }
  .moves { display: flex; flex-wrap: wrap; gap: var(--sp-4); padding: 0 var(--sp-6) var(--sp-5) calc(var(--sp-6) + 16px + var(--sp-5) + 46px); }
  @media (max-width: 720px) {
    .story-text, .acs, .refs, .invest, .goal { margin-left: 0; }
    .sub > .row-line .main { padding-left: 22px; }
    .ac-edit { grid-template-columns: 1fr; }
    .ac-row { grid-template-columns: 1fr; }
    .ac-row.h { display: none; }
  }
</style>
