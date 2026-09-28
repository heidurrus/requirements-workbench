"""Open a URL in a private (incognito) browser window.

Used for the Atlassian sign-in: a normal browser window silently reuses whichever
Atlassian account is already logged in there (often a work account), and the MCP
sign-in doesn't let an app ask for an account choice. A private window has no
login, so the user picks the account.
"""
import ntpath
import os
import posixpath
import shutil
import subprocess
import sys

# (app name / executable, private-window flag), in order of preference.
MAC_BROWSERS = [("Google Chrome", "--incognito"), ("Microsoft Edge", "--inprivate"), ("Brave Browser", "--incognito"),
                ("Chromium", "--incognito"), ("Firefox", "-private-window")]
WIN_BROWSERS = [(r"Google\Chrome\Application\chrome.exe", "--incognito"),
                (r"Microsoft\Edge\Application\msedge.exe", "--inprivate"),
                (r"BraveSoftware\Brave-Browser\Application\brave.exe", "--incognito"),
                (r"Mozilla Firefox\firefox.exe", "-private-window")]
LINUX_BROWSERS = [("google-chrome", "--incognito"), ("chromium", "--incognito"), ("microsoft-edge", "--inprivate"),
                  ("firefox", "-private-window")]


def find_browser(platform=None, exists=os.path.exists, which=shutil.which, env=os.environ):
    """(command list prefix, flag, name) for the first private-capable browser, or None."""
    platform = platform or sys.platform
    if platform == "darwin":
        for app, flag in MAC_BROWSERS:
            for base in ("/Applications", posixpath.expanduser("~/Applications")):
                if exists(posixpath.join(base, f"{app}.app")):
                    return ["open", "-na", app, "--args"], flag, app
    elif platform == "win32":
        roots = [env.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA") if env.get(k)]
        for rel, flag in WIN_BROWSERS:
            for root in roots:
                path = ntpath.join(root, rel)
                if exists(path):
                    return [path], flag, ntpath.basename(path)
    else:
        for exe, flag in LINUX_BROWSERS:
            path = which(exe)
            if path:
                return [path], flag, exe
    return None


def open_private(url, run=subprocess.Popen, **find_kw):
    """Open url in a private window; returns the browser name, or None if no suitable browser was found."""
    found = find_browser(**find_kw)
    if not found:
        return None
    prefix, flag, name = found
    run(prefix + [flag, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return name
