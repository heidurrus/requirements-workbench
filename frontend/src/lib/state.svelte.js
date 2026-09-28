// App-wide state (Svelte 5 runes). Components read and mutate `app` directly.
import { api } from "./api.js";
import { translate } from "./i18n.js";

function readPref(key, fallback) {
  try { const v = localStorage.getItem("wb." + key); return v === null ? fallback : JSON.parse(v); }
  catch (_) { return fallback; }
}
export function writePref(key, value) {
  try { localStorage.setItem("wb." + key, JSON.stringify(value)); } catch (_) { /* private mode */ }
}

export function parseRoute(hash = location.hash) {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "source" && parts[1]) return { name: "transcript", id: parts[1], summarize: parts[2] === "summarize",
                                                  seg: parts[2] === "seg" ? Number(parts[3]) : null };
  if (parts[0] === "document") return { name: "document" };
  if (parts[0] === "backlog") return { name: "backlog" };
  if (parts[0] === "export") return { name: "export" };
  if (parts[0] === "skills") return { name: "skills", skill: parts[1] || null };
  if (parts[0] === "atoms") return { name: "atoms", source: parts[1] === "source" ? parts[2] : null };
  if (parts[0] === "settings") return { name: "settings" };
  if (parts[0] === "transcript") return { name: "transcript", id: null };
  return { name: "sources" };
}

export const app = $state({
  route: parseRoute(),
  lang: readPref("lang", "ru"),
  projects: [],
  archivedProjects: [],
  currentProjectId: null,
  sources: [],
  lastSourceId: readPref("lastSource", null),
  device: { cuda: false, mps: false, gpu_name: null, desktop: false },
  health: null,
  models: [],
  options: readPref("asrOptions", { model: "v3_e2e_rnnt", device: "cpu", diarize: false, word_timestamps: false }),
  toasts: [],               // at most 2; they belong to the screen that raised them
  status: null,             // per-step counts for the sidebar badges
  theme: readPref("theme", "auto"),
  sidebarCollapsed: readPref("sidebarCollapsed", null),   // null = automatic by width
  // source id → { jobId, progress, message } for work started in this session
  jobs: {},
  // source id → { jobId, progress, message } for atom extraction
  extracting: {},
  atomsVersion: 0,          // bumped when atoms change elsewhere, so open screens reload
});

export const t = (key, vars) => translate(app.lang, key, vars);

export function go(path) {
  if (location.hash !== "#" + path) location.hash = path;
  else app.route = parseRoute();
}
window.addEventListener("hashchange", () => {
  const prev = app.route.name;
  app.route = parseRoute();
  if (app.route.name !== prev) app.toasts = [];      // toasts belong to the screen that raised them
  loadStatus();
});

export function setTheme(theme) {
  app.theme = theme;
  writePref("theme", theme);
  applyTheme();
}
export function applyTheme() {
  if (app.theme === "auto") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = app.theme;
}
export function isDark() {
  if (app.theme !== "auto") return app.theme === "dark";
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

let statusTimer = null;
export function loadStatus() {
  clearTimeout(statusTimer);            // coalesce bursts of changes
  statusTimer = setTimeout(async () => {
    if (!app.currentProjectId) return;
    try { app.status = await api(`/api/projects/${app.currentProjectId}/status`); }
    catch (_) { /* badges are optional */ }
  }, 150);
}

export function setLang(lang) {
  app.lang = lang;
  writePref("lang", lang);
  document.documentElement.lang = lang;
}

export function saveOptions() { writePref("asrOptions", app.options); }

export function currentProject() {
  return app.projects.find(p => p.id === app.currentProjectId) || null;
}

export async function loadProjects() {
  const body = await api("/api/projects?archived=1");
  app.projects = body.projects.filter(p => !p.archived);
  app.archivedProjects = body.projects.filter(p => p.archived);
  app.currentProjectId = body.current_project_id;
}

export async function loadSources() {
  if (!app.currentProjectId) return;
  const body = await api(`/api/projects/${app.currentProjectId}/sources`);
  app.sources = body.sources;
}

export async function switchProject(id) {
  await api(`/api/projects/${id}/current`, { method: "POST" });
  app.currentProjectId = id;
  app.sources = [];
  await loadSources();
  app.status = null;
  loadStatus();
  go("/sources");
}

let toastSeq = 0;
export function dismissToast(id) {
  app.toasts = app.toasts.filter(x => x.id !== id);
}
// The most recent undo stays available to ⌘Z for as long as its toast would have (PM-10: ≥ 10 s).
let lastUndo = null;
export function undoLast() {
  if (!lastUndo || Date.now() > lastUndo.until) return false;
  const u = lastUndo;
  lastUndo = null;
  dismissToast(u.id);
  u.run();
  return true;
}

export function toast(message, { action, onAction, kind = "info", ms } = {}) {
  ms = ms ?? (action ? 10000 : 6000);
  if (action) ms = Math.max(ms, 10000);
  const id = ++toastSeq;
  if (action && onAction && kind !== "danger") lastUndo = { id, run: onAction, until: Date.now() + ms };
  // Only one undo at a time: a newer action toast replaces an older one.
  const keep = action ? app.toasts.filter(x => !x.action) : app.toasts;
  app.toasts = [...keep, { id, message, action, onAction, kind }].slice(-2);
  setTimeout(() => dismissToast(id), ms);
  loadStatus();                         // most toasts follow a change worth counting
}

export function rememberSource(id) {
  app.lastSourceId = id;
  writePref("lastSource", id);
}
