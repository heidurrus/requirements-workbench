// Saving files: a native Save dialog in the desktop app (downloads are off in its window),
// a normal download in the browser.
import { t, toast } from "./state.svelte.js";

const desktop = () => window.pywebview && window.pywebview.api && window.pywebview.api.save_file;

function done(result) {
  if (result?.saved) {
    toast(t("save.saved"), { action: t("save.show"), onAction: () => window.pywebview.api.reveal(result.saved) });
  } else if (result?.error) {
    toast(result.error, { kind: "danger" });
  }
}

export async function saveUrl(url, filename) {
  if (desktop()) return done(await window.pywebview.api.save_file(url, filename));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
}

export async function saveText(filename, text) {
  if (desktop()) return done(await window.pywebview.api.save_text(filename, text));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
