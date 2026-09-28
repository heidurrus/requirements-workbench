"""Built-in local model: download it with one click, run it without setup.

The engine is llama.cpp's `llama-server` (a small prebuilt program from its
official releases); the weights are GGUF files from Hugging Face. Both are
pinned to exact versions and checked by SHA-256. The app starts the server as
its own child process on a private port with a random API key, only when a
local model is needed, and stops it when idle or when the app quits, so the
user never installs or starts anything (spec D-02, FR-SET-02).
"""
import atexit
from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass

from core.paths import app_data_dir

ENGINE_BUILD = "b11223"
_RELEASE = f"https://github.com/ggml-org/llama.cpp/releases/download/{ENGINE_BUILD}/"


@dataclass(frozen=True)
class Asset:
    url: str
    sha256: str
    size: int


# Windows x64 uses the Vulkan build: it runs on NVIDIA, AMD and Intel GPUs and
# falls back to the CPU when there is no usable GPU.
ENGINES = {
    ("darwin", "arm64"): Asset(_RELEASE + f"llama-{ENGINE_BUILD}-bin-macos-arm64.tar.gz",
                               "5bacea12237283699a196194b7f62a0e613438bd5feed694359ed6050492bb3e", 11756895),
    ("darwin", "x86_64"): Asset(_RELEASE + f"llama-{ENGINE_BUILD}-bin-macos-x64.tar.gz",
                                "20b0a6f67d384de5efa90ce95968ca5cd9d7d3a0d98b0873da07707d034f8234", 11310524),
    ("win32", "amd64"): Asset(_RELEASE + f"llama-{ENGINE_BUILD}-bin-win-vulkan-x64.zip",
                              "b450e71cfb2204955db784590af51b3f81fbc3bde0c5687f7a85c89edc977fd4", 33062159),
    ("win32", "arm64"): Asset(_RELEASE + f"llama-{ENGINE_BUILD}-bin-win-cpu-arm64.zip",
                              "b04e2a1389fbb04abb1ef5fe238cce7faf1d38925b4d87c9d3966f0dee992078", 12042144),
}


@dataclass(frozen=True)
class Model:
    id: str
    label: str
    file: str
    asset: Asset
    min_ram_gb: int
    context: int


def _hf(repo, revision, file):
    return f"https://huggingface.co/{repo}/resolve/{revision}/{file}"


# Apache-2.0 models that are good in Russian and English. Largest first.
MODELS = [
    Model("gemma-4-12b", "Gemma 4 12B", "gemma-4-12b-it-qat-q4_0.gguf",
          Asset(_hf("google/gemma-4-12B-it-qat-q4_0-gguf", "29d097773436b69ff9feafd636ab4cf873786537",
                    "gemma-4-12b-it-qat-q4_0.gguf"),
                "93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b", 6975879296),
          min_ram_gb=16, context=32768),
    Model("qwen3.5-4b", "Qwen3.5 4B", "Qwen3.5-4B-Q4_K_M.gguf",
          Asset(_hf("unsloth/Qwen3.5-4B-GGUF", "e87f176479d0855a907a41277aca2f8ee7a09523", "Qwen3.5-4B-Q4_K_M.gguf"),
                "00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4", 2740937888),
          min_ram_gb=8, context=32768),
]
MODELS_BY_ID = {m.id: m for m in MODELS}

IDLE_STOP_SECONDS = 15 * 60
START_TIMEOUT_SECONDS = 240
DISK_MARGIN = 1 * 1024 ** 3


class LocalModelError(Exception):
    """A user-facing problem with the built-in model."""


# ── system facts ─────────────────────────────────────────────────────────────

def platform_key():
    machine = platform.machine().lower()
    machine = {"aarch64": "arm64", "x64": "amd64"}.get(machine, machine)
    if sys.platform == "darwin" and machine == "amd64":
        machine = "x86_64"
    return sys.platform, machine


def engine_asset():
    return ENGINES.get(platform_key())


def total_ram_bytes():
    try:
        if sys.platform == "darwin":
            return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True,
                                      timeout=5).stdout.strip())
        if sys.platform == "win32":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return int(status.ullTotalPhys)
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except Exception:
        return None


def recommended_model_id(ram=None):
    """The largest model the machine's memory comfortably holds."""
    ram = total_ram_bytes() if ram is None else ram
    gb = (ram or 0) / 1024 ** 3
    # A "16 GB" machine reports slightly less; allow for that.
    return next((m.id for m in MODELS if gb >= m.min_ram_gb * 0.9), MODELS[-1].id)


# ── files ────────────────────────────────────────────────────────────────────

def root_dir():
    path = os.path.join(app_data_dir(), "local-llm")
    os.makedirs(path, exist_ok=True)
    return path


def models_path():
    path = os.path.join(root_dir(), "models")
    os.makedirs(path, exist_ok=True)
    return path


def engine_dir():
    return os.path.join(root_dir(), "engine", ENGINE_BUILD)


def server_binary():
    """Path of llama-server if the engine is installed, else None."""
    name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    base = engine_dir()
    if not os.path.isdir(base):
        return None
    for folder, _dirs, files in os.walk(base):
        if name in files:
            return os.path.join(folder, name)
    return None


def model_file(model_id):
    return os.path.join(models_path(), MODELS_BY_ID[model_id].file)


def model_installed(model_id):
    m = MODELS_BY_ID.get(model_id)
    return bool(m) and os.path.isfile(model_file(model_id)) and os.path.getsize(model_file(model_id)) == m.asset.size


def installed_models():
    return [m.id for m in MODELS if model_installed(m.id)]


def ready():
    return server_binary() is not None and bool(installed_models())


def delete_model(model_id):
    if model_id not in MODELS_BY_ID:
        raise LocalModelError("unknown model")
    runtime.stop_if(model_id)
    for path in (model_file(model_id), model_file(model_id) + ".part"):
        if os.path.exists(path):
            os.remove(path)


# ── downloads ────────────────────────────────────────────────────────────────

class Cancelled(Exception):
    pass


def download(asset, dest, on_bytes=None, cancel=None, opener=urllib.request.urlopen, retries=4, sleep=time.sleep):
    """Download to dest with resume (dest.part + Range) and a SHA-256 check."""
    part = dest + ".part"
    for attempt in range(retries + 1):
        try:
            have = os.path.getsize(part) if os.path.exists(part) else 0
            if have > asset.size:
                os.remove(part)
                have = 0
            if have < asset.size:
                req = urllib.request.Request(asset.url, headers={"Range": f"bytes={have}-"} if have else {})
                with opener(req, timeout=60) as resp:
                    if have and getattr(resp, "status", 206) != 206:   # server ignored Range: start over
                        have = 0
                    with open(part, "ab" if have else "wb") as f:
                        while True:
                            if cancel is not None and cancel.is_set():
                                raise Cancelled()
                            chunk = resp.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            have += len(chunk)
                            if on_bytes:
                                on_bytes(have)
            if os.path.getsize(part) != asset.size:
                raise OSError("the download ended early")
            digest = hashlib.sha256()
            with open(part, "rb") as f:
                for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    digest.update(chunk)
            if digest.hexdigest() != asset.sha256:
                os.remove(part)
                raise LocalModelError("The downloaded file is damaged (checksum mismatch). Please try again.")
            os.replace(part, dest)
            return dest
        except (Cancelled, LocalModelError):
            raise
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            if attempt == retries:
                raise LocalModelError(f"Download failed: {getattr(e, 'reason', e)}. Check your internet connection and try again.")
            sleep(min(30, 2 ** attempt))


def _extract(archive, dest):
    tmp = dest + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
    else:
        with tarfile.open(archive) as t:
            t.extractall(tmp, filter="data")
    shutil.rmtree(dest, ignore_errors=True)
    os.replace(tmp, dest)
    if sys.platform != "win32":
        for folder, _dirs, files in os.walk(dest):
            for name in files:
                if name.startswith("llama-") or name == "ggml-rpc-server":
                    path = os.path.join(folder, name)
                    os.chmod(path, os.stat(path).st_mode | 0o755)


class Installer:
    """One background download at a time (engine if missing, then the model)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._thread = None
        self.state = {"status": "idle"}

    def status(self):
        with self._lock:
            return dict(self.state)

    def _set(self, **kw):
        with self._lock:
            self.state = {**self.state, **kw}

    def start(self, model_id):
        if model_id not in MODELS_BY_ID:
            raise LocalModelError("unknown model")
        if engine_asset() is None:
            raise LocalModelError("The built-in model isn't available for this computer. Use Claude or Ollama.")
        with self._lock:
            if self.state.get("status") in ("downloading", "verifying"):
                return dict(self.state)
        model = MODELS_BY_ID[model_id]
        need = (0 if server_binary() else engine_asset().size) + (0 if model_installed(model_id) else model.asset.size)
        partial = model_file(model_id) + ".part"
        need -= os.path.getsize(partial) if os.path.exists(partial) else 0
        free = shutil.disk_usage(root_dir()).free
        if need + DISK_MARGIN > free:
            raise LocalModelError(f"Not enough disk space: {_gb(need + DISK_MARGIN)} needed, {_gb(free)} free.")
        self._cancel.clear()
        total = (0 if server_binary() else engine_asset().size) + model.asset.size
        self.state = {"status": "downloading", "model": model_id, "done": 0, "total": total, "error": None}
        self._thread = threading.Thread(target=self._run, args=(model,), daemon=True)
        self._thread.start()
        return self.status()

    def cancel(self):
        self._cancel.set()

    def _run(self, model):
        offset = 0
        try:
            if not server_binary():
                asset = engine_asset()
                archive = os.path.join(root_dir(), os.path.basename(asset.url))
                download(asset, archive, on_bytes=lambda n: self._set(done=n), cancel=self._cancel)
                _extract(archive, engine_dir())
                os.remove(archive)
                if not server_binary():
                    raise LocalModelError("The engine archive doesn't contain llama-server.")
                offset = asset.size
            if not model_installed(model.id):
                def progress(n):
                    self._set(done=offset + n, status="verifying" if n >= model.asset.size else "downloading")
                download(model.asset, model_file(model.id), on_bytes=progress, cancel=self._cancel)
            self._set(status="done", done=self.state["total"])
        except Cancelled:
            self._set(status="cancelled")
        except LocalModelError as e:
            self._set(status="error", error=str(e))
        except Exception as e:  # keep the thread's failure visible in the UI
            self._set(status="error", error=f"Download failed: {e}")


def _gb(n):
    return f"{n / 1024 ** 3:.1f} GB"


# ── running the server ───────────────────────────────────────────────────────

def _pid_file():
    return os.path.join(root_dir(), "server.pid")


def _is_our_server(pid):
    """True if pid is a running llama-server (so a recycled pid is never killed)."""
    try:
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True,
                                 text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).stdout
        else:
            out = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, timeout=5).stdout
        return "llama-server" in out
    except (OSError, subprocess.SubprocessError):
        return False


def cleanup_stale():
    """Stop a server left behind by a crash or force-quit, which would otherwise hold gigabytes of memory."""
    try:
        with open(_pid_file(), encoding="utf-8") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return False
    try:
        os.remove(_pid_file())
    except OSError:
        pass
    if pid == os.getpid() or not _is_our_server(pid):
        return False
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.kill(pid, 15)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Runtime:
    """Starts llama-server on demand and stops it when idle or at exit."""

    def __init__(self, idle_seconds=IDLE_STOP_SECONDS, clock=time.monotonic):
        self._lock = threading.RLock()
        self._proc = None
        self._model = None
        self._url = None
        self._key = None
        self._last_used = 0.0
        self._busy = 0
        self._idle = idle_seconds
        self._clock = clock
        self._watcher = None
        atexit.register(self.stop)

    def running_model(self):
        with self._lock:
            return self._model if self._proc and self._proc.poll() is None else None

    def log_path(self):
        return os.path.join(root_dir(), "server.log")

    def acquire(self, model_id):
        """Make sure the server runs the model; returns (base_url, api_key). Pair with release()."""
        with self._lock:
            if not model_installed(model_id):
                raise LocalModelError("The local model isn't downloaded yet. Download it in Settings → AI.")
            binary = server_binary()
            if not binary:
                raise LocalModelError("The local engine isn't installed yet. Download the model in Settings → AI.")
            if self.running_model() != model_id:
                self._stop_locked()
                self._start_locked(binary, model_id)
            self._busy += 1
            self._last_used = self._clock()
            return self._url, self._key

    def release(self):
        with self._lock:
            self._busy = max(0, self._busy - 1)
            self._last_used = self._clock()

    def _start_locked(self, binary, model_id):
        model = MODELS_BY_ID[model_id]
        port, key = _free_port(), secrets.token_urlsafe(24)
        cmd = [binary, "-m", model_file(model_id), "--host", "127.0.0.1", "--port", str(port),
               "--api-key", key, "--no-webui", "-c", str(model.context), "-np", "1",
               "--reasoning", "off", "--jinja"]
        log = open(self.log_path(), "w", encoding="utf-8", errors="replace")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self._proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                      cwd=os.path.dirname(binary), creationflags=flags)
        log.close()
        with open(_pid_file(), "w", encoding="utf-8") as f:
            f.write(str(self._proc.pid))
        self._url, self._key, self._model = f"http://127.0.0.1:{port}", key, model_id
        deadline = time.monotonic() + START_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                tail = _tail(self.log_path())
                self._proc = self._model = None
                raise LocalModelError("The local model could not start"
                                      + (f": {tail}" if tail else ". Your computer may not have enough memory."))
            try:
                with urllib.request.urlopen(self._url + "/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(0.5)
        else:
            self._stop_locked()
            raise LocalModelError("The local model took too long to start.")
        if self._watcher is None:
            self._watcher = threading.Thread(target=self._watch_idle, daemon=True)
            self._watcher.start()

    def _watch_idle(self):
        while True:
            time.sleep(30)
            with self._lock:
                if self._proc and not self._busy and self._clock() - self._last_used > self._idle:
                    self._stop_locked()          # frees several GB of memory

    def _stop_locked(self):
        proc, self._proc, self._model = self._proc, None, None
        if proc:
            try:
                os.remove(_pid_file())
            except OSError:
                pass
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    def stop(self):
        with self._lock:
            self._stop_locked()

    def stop_if(self, model_id):
        with self._lock:
            if self._model == model_id:
                self._stop_locked()


def _tail(path, lines=3):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = [ln.strip() for ln in f.readlines()[-40:] if ln.strip()]
        errors = [ln for ln in text if "error" in ln.lower() or "failed" in ln.lower()]
        return " ".join((errors or text)[-lines:])[:300]
    except OSError:
        return ""


runtime = Runtime()
installer = Installer()


def status():
    ram = total_ram_bytes()
    recommended = recommended_model_id(ram)
    return {
        "supported": engine_asset() is not None,
        "engine_installed": server_binary() is not None,
        "ram": ram,
        "disk_free": shutil.disk_usage(root_dir()).free,
        "recommended": recommended,
        "running": runtime.running_model(),
        "download": installer.status(),
        "models": [{"id": m.id, "label": m.label, "size": m.asset.size, "min_ram_gb": m.min_ram_gb,
                    "installed": model_installed(m.id), "recommended": m.id == recommended,
                    "fits": ram is None or ram >= m.min_ram_gb * 0.9 * 1024 ** 3} for m in MODELS],
    }


def resolve_model(preferred):
    """The model to use: the chosen one if downloaded, else any downloaded one."""
    if preferred and model_installed(preferred):
        return preferred
    have = installed_models()
    if not have:
        raise LocalModelError("The local model isn't downloaded yet. Download it in Settings → AI.")
    return have[0]


@contextmanager
def chat(model_id, body, timeout=900, opener=urllib.request.urlopen):
    """POST an OpenAI-style chat request to the built-in server; yields the open response.

    The server is started if needed and isn't stopped for idleness while a request runs."""
    url, key = runtime.acquire(model_id)
    req = urllib.request.Request(url + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with opener(req, timeout=timeout) as resp:
            yield resp
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        try:
            detail = json.loads(detail)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        if "context" in str(detail).lower() and ("exceed" in str(detail).lower() or "too long" in str(detail).lower()):
            raise LocalModelError("This text is too long for the local model. Use Claude for long sources.")
        raise LocalModelError(f"Local model error ({e.code}): {str(detail)[:200]}")
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise LocalModelError(f"The local model stopped responding ({getattr(e, 'reason', e)}).")
    finally:
        runtime.release()
