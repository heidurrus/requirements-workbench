// Atom extraction started from any screen; progress lives in app.extracting.
import { explain } from "./errors.js";
import { api, pollJob } from "./api.js";
import { app, t, go, toast, loadSources } from "./state.svelte.js";

export async function extractAtoms(sourceId, note = null) {
  if (app.extracting[sourceId]) return;
  app.extracting[sourceId] = { jobId: null, progress: 0, message: t("at.reading") };
  try {
    const { job_id } = await api(`/api/sources/${sourceId}/atoms/extract`, { method: "POST", body: note ? { note } : {} });
    await followExtraction(sourceId, job_id);
  } catch (err) {
    delete app.extracting[sourceId];
    const e = explain(err);
    toast(e.message, { kind: "danger", ...(e.setup ? { action: t("err.open_settings"), onAction: () => go("/settings") } : {}) });
  }
}

// Follow an extraction job, also one the server started on its own after a transcription (PM-13).
export async function followExtraction(sourceId, jobId, { notifyTitle = null } = {}) {
  app.extracting[sourceId] = { jobId, progress: 0, message: t("at.reading") };
  try {
    const job = await pollJob(jobId, j => {
      app.extracting[sourceId] = { jobId, progress: j.progress || 0, message: j.progress_msg || "" };
    }, { interval: 800 });
    const r = job.result;
    app.atomsVersion++;
    loadSources();
    const parts = [t("at.found", { n: r.extracted })];
    if (r.merged) parts.push(t("at.merged_n", { n: r.merged }));
    if (r.skipped_actions) parts.push(t("at.actions_kept", { n: r.skipped_actions }));
    if (r.conflicts) parts.push(t("at.conflicts_n", { n: r.conflicts }));
    const text = (notifyTitle ? notifyTitle + " · " : "") + parts.join(" · ");
    toast(text, app.route.name === "atoms" ? {} : { action: t("at.open"), onAction: () => go(`/atoms/source/${sourceId}`) });
    if (notifyTitle) notify(notifyTitle, parts.join(" · "));
    return r;
  } finally {
    delete app.extracting[sourceId];
  }
}

// A system notification, only when the window isn't in front (PM-30).
export function notify(title, text) {
  if (typeof document !== "undefined" && document.hasFocus && document.hasFocus()) return;
  api("/api/notify", { method: "POST", body: { title, text } }).catch(() => {});
}
