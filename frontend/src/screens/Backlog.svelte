<script>
  import Icon from "../components/Icon.svelte";
  import { api, pollJob } from "../lib/api.js";
  import { app, t, go, toast } from "../lib/state.svelte.js";

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
    const setup = err.body?.needs_setup;
    toast(err.message, { kind: "danger", ...(setup ? { action: t("nav.settings"), onAction: () => go("/settings") } : {}) });
  }
  async function follow(jobId, kind) {
    job = { kind, progress: 0, message: "" };
    try {
      const j = await pollJob(jobId, x => (job = { kind, progress: x.progress || 0, message: x.progress_msg || "" }), { interval: 800 });
      toast(kind === "invest" ? t("bl.invest_done", { n: j.result.with_findings }) : t("bl.built", { n: j.result.stories }));
    } catch (err) { fail(err); }
    finally { job = null; load(); }
  }
  async function run(kind) {
    try {
      const { job_id } = await api(`/api/projects/${app.currentProjectId}/backlog/${kind}`, { method: "POST" });
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
    {#if body}
      <div class="actions">
        <button class="btn" class:btn-primary={!items.length || body.stale} disabled={!!job || !body.latest}
                onclick={() => run("build")}>{items.length ? t("bl.rebuild") : t("bl.build")}</button>
        {#if items.length}
          <button class="btn" class:btn-primary={!!items.length && !body.stale} disabled={!!job} onclick={() => run("invest")}>{t("bl.invest")}</button>
        {/if}
      </div>
    {/if}
  </header>

  {#if error}<p class="note danger">{error}</p>{/if}

  {#if body}
    <div class="stack">
      {#if job}
        <div class="panel running"><span class="spinner"></span>
          <div class="grow"><div class="bar"><i style="width: {job.progress}%"></i></div></div>
          <span class="mono faint">{job.message}</span></div>
      {/if}

      {#if !body.latest}
        <div class="empty panel">
          <p class="panel-title">{t("bl.no_doc_title")}</p>
          <p>{t("bl.no_doc")}</p>
          <button class="btn" style="margin-top: var(--s-3)" onclick={() => go("/document")}>{t("bl.to_doc")}</button>
        </div>
      {:else if !items.length}
        <div class="empty panel">
          <p class="panel-title">{t("bl.ready_title", { v: body.latest })}</p>
          <p>{t("bl.ready")}</p>
        </div>
      {:else}
        {#if body.stale}
          <p class="note warn row-note"><span>{t("bl.stale", { a: body.built_from, b: body.latest })}</span>
            <button class="btn btn-sm" disabled={!!job} onclick={() => run("build")}>{t("bl.rebuild")}</button></p>
        {/if}
        <p class="hint">{t("bl.hint")}</p>

        <section class="panel tree">
          {#each epics as epic (epic.id)}
            <div class="node epic" class:off={!epic.included}>
              {@render row(epic)}
              <div class="kids">
                {#each children(epic.id) as story (story.id)}
                  <div class="node story" class:off={!story.included}>
                    {@render row(story)}
                    {#if children(story.id).length}
                      <div class="kids">
                        {#each children(story.id) as sub (sub.id)}
                          <div class="node sub" class:off={!sub.included}>{@render row(sub)}</div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}
                <button class="btn btn-sm btn-ghost add" onclick={() => add("story", epic)}><Icon name="plus" /> {t("bl.add_story")}</button>
              </div>
            </div>
          {/each}
          <button class="btn btn-sm btn-ghost add" onclick={() => add("epic", null)}><Icon name="plus" /> {t("bl.add_epic")}</button>
        </section>

        {#if nfrs.length}
          <section class="panel tree">
            <p class="panel-title">{t("bl.nfr_title")}</p>
            <p class="panel-desc">{t("bl.nfr_hint")}</p>
            {#each nfrs as nfr (nfr.id)}
              <div class="node nfr" class:off={!nfr.included}>
                {@render row(nfr)}
                {#each nfr.invest || [] as f, i (i)}
                  {#if f.move_to?.length}
                    <div class="moves">
                      {#each f.move_to as sid (sid)}
                        {#if storyTitle[sid]}
                          <button class="btn btn-sm" onclick={() => moveInto(nfr, sid)}>{t("bl.move_into", { title: storyTitle[sid] })}</button>
                        {/if}
                      {/each}
                    </div>
                  {/if}
                {/each}
              </div>
            {/each}
          </section>
        {/if}

        <div class="foot">
          <span class="hint">{hasFindings ? t("bl.findings_hint") : ""}</span>
          <button class="btn" disabled title={t("nav.soon")}>{t("bl.to_export")} · {t("nav.soon")}</button>
        </div>
      {/if}
    </div>
  {/if}
</div>

{#snippet row(item)}
  <div class="row-line">
    <input type="checkbox" class="inc" checked={item.included} aria-label={item.title}
           onchange={e => include(item, e.currentTarget.checked)} />
    <div class="main">
      {#if editing?.id === item.id}
        <div class="edit">
          <input class="input" bind:value={editing.title} aria-label={t("bl.title")} />
          {#if item.kind === "epic"}
            <input class="input" bind:value={editing.goal} placeholder={t("bl.goal")} />
          {:else if item.kind === "story"}
            <textarea class="input area" rows="2" bind:value={editing.body} placeholder={t("bl.story_ph")}></textarea>
            <p class="label">{t("bl.ac")}</p>
            {#each editing.acceptance as ac, i (i)}
              <div class="ac-edit">
                <input class="input" bind:value={ac.given} placeholder={t("bl.given")} />
                <input class="input" bind:value={ac.when} placeholder={t("bl.when")} />
                <input class="input" bind:value={ac.then} placeholder={t("bl.then")} />
                <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")}
                        onclick={() => editing.acceptance.splice(i, 1)}><Icon name="close" /></button>
              </div>
            {/each}
            <button class="btn btn-sm btn-ghost" onclick={() => editing.acceptance.push({ given: "", when: "", then: "" })}>
              <Icon name="plus" /> {t("bl.add_ac")}</button>
          {/if}
          <div class="actions">
            <button class="btn btn-sm btn-primary" disabled={!editing.title.trim()} onclick={() => saveEdit(item)}>{t("at.save")}</button>
            <button class="btn btn-sm btn-ghost" onclick={() => (editing = null)}>{t("at.cancel")}</button>
          </div>
        </div>
      {:else}
        <p class="title">
          <span class="tag kind-{item.kind}">{t("bl.kind." + item.kind)}</span>
          <span class="t">{item.title}</span>
          {#if item.generated}<span class="tag">{t("bl.generated")}</span>{/if}
          {#if item.pinned}<span class="tag accent">{t("bl.edited")}</span>{/if}
        </p>
        {#if item.kind === "epic" && item.goal}<p class="goal">{t("bl.goal_label")}: {item.goal}</p>{/if}
        {#if item.kind === "story" && item.body}<p class="story">{item.body}</p>{/if}
        {#if item.acceptance?.length}
          <ul class="acs">
            {#each item.acceptance as ac, i (i)}
              <li>{#if ac.given}<b>{t("bl.given")}</b>{" " + ac.given + " "}{/if}{#if ac.when}<b>{t("bl.when")}</b>{" " + ac.when + " "}{/if}<b>{t("bl.then")}</b>{" " + ac.then}</li>
            {/each}
          </ul>
        {/if}
        {#if item.refs?.length}
          <p class="refs">{#each item.refs as r, i (r.id)}<button class="link mono" onclick={() => go("/document")}>{refLabel(r)}</button>{i < item.refs.length - 1 ? ", " : ""}{/each}</p>
        {/if}
        {#if item.kind === "story"}
          {#each item.invest || [] as f, i (i)}
            <div class="note warn invest">
              <span><b>INVEST · {f.letter}</b> — {f.reason}{#if f.fix}<br /><span class="fix">{t("bl.fix")}: {f.fix}</span>{/if}</span>
              {#if f.fix}<button class="btn btn-sm" onclick={() => applyFix(item, f.fix)}>{t("bl.apply")}</button>{/if}
            </div>
          {/each}
        {:else if item.kind === "nfr"}
          {#each item.invest || [] as f, i (i)}<p class="hint">INVEST · {f.letter}: {f.reason}</p>{/each}
        {/if}
      {/if}
    </div>
    {#if editing?.id !== item.id}
      <div class="acts">
        {#if item.kind === "story"}
          <button class="btn btn-ghost btn-sm icon-btn" title={t("bl.add_sub")} aria-label={t("bl.add_sub")} onclick={() => add("subtask", item)}><Icon name="plus" /></button>
        {/if}
        {#if item.kind !== "nfr"}
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.up")} onclick={() => move(item, "up")}>↑</button>
          <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sk.sec.down")} onclick={() => move(item, "down")}>↓</button>
        {/if}
        <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("at.edit")} onclick={() => startEdit(item)}><Icon name="pencil" /></button>
        <button class="btn btn-ghost btn-sm icon-btn" aria-label={t("sources.delete")} onclick={() => remove(item)}><Icon name="trash" /></button>
      </div>
    {/if}
  </div>
{/snippet}

<style>
  .running { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
  .grow { flex: 1; }
  .row-note { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); flex-wrap: wrap; }
  .tree { padding: var(--s-3) var(--s-4); }
  .node { border-top: 1px solid var(--rule); }
  .tree > .node:first-child, .tree > .panel-desc + .node { border-top: 0; }
  .kids { margin-left: 28px; border-left: 1px solid var(--rule); padding-left: var(--s-3); }
  .kids > .node:first-child { border-top: 0; }
  .row-line { display: grid; grid-template-columns: 16px minmax(0, 1fr) auto; gap: var(--s-3); padding: var(--s-3) 0; }
  .inc { width: 15px; height: 15px; margin: 3px 0 0; accent-color: var(--accent); cursor: pointer; }
  .main { min-width: 0; }
  .title { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--s-1) var(--s-2); line-height: 1.45; }
  .epic > .row-line .t { font-weight: 600; font-size: var(--t-md); }
  .story > .row-line .t { font-weight: 500; }
  .sub .t { font-size: var(--t-sm); color: var(--ink-2); }
  .off .t, .off .story, .off .acs { color: var(--ink-3); }
  .kind-epic { background: var(--ink); color: var(--paper); }
  .kind-story { background: var(--accent-bg); color: var(--accent); }
  .kind-nfr { background: var(--warn-bg); color: var(--warn); }
  .goal { margin-top: 2px; font-size: var(--t-sm); color: var(--ink-2); }
  .story { margin-top: var(--s-1); line-height: 1.55; }
  .acs { margin: var(--s-1) 0 0; padding-left: var(--s-4); font-size: var(--t-sm); color: var(--ink-2); line-height: 1.6; }
  .acs b { font-weight: 500; color: var(--ink-3); }
  .refs { margin-top: var(--s-1); font-size: var(--t-xs); }
  .link { border: 0; background: none; padding: 0; color: var(--accent); cursor: pointer; font-size: var(--t-xs); }
  .invest { margin-top: var(--s-2); display: flex; align-items: flex-start; justify-content: space-between; gap: var(--s-3); }
  .invest .fix { color: var(--ink-2); }
  .acts { display: flex; gap: 2px; align-items: flex-start; opacity: .6; }
  .row-line:hover .acts { opacity: 1; }
  .add { margin: var(--s-1) 0 var(--s-2); color: var(--ink-3); }
  .edit { display: flex; flex-direction: column; gap: var(--s-2); }
  .area { height: auto; padding: var(--s-2) var(--s-3); line-height: 1.5; resize: vertical; }
  .ac-edit { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) auto; gap: var(--s-2); }
  .moves { display: flex; flex-wrap: wrap; gap: var(--s-2); margin: 0 0 var(--s-3) 28px; }
  .foot { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); flex-wrap: wrap; }
  @media (max-width: 700px) {
    .kids { margin-left: var(--s-3); }
    .ac-edit { grid-template-columns: 1fr; }
  }
</style>
