"""Local LLM support (Ollama) — detect the machine, recommend a model, link it.

The intent engine works offline by default.  This module adds a third option for
judges who want to see a *real* language model read the user's reason: **Ollama**,
which runs a model entirely on the user's own machine.  Nothing leaves the device.

Four steps, all visible in the Judge panel:

1. **Detect the machine** — RAM, CPU, GPU, free disk, OS (`machine_specs`).
2. **Recommend a model** that fits (`recommend_model`), with the reason why.
3. **Install / start / download** — `ollama_installed`, `ollam_start_server`,
   `ollama_pull`, with the exact commands shown when we cannot run them.
4. **Link** — `ollam_ready` proves the server answers and the model is present,
   and `ollama_generate_json` is the call the intent engine makes.

Every function is written so that a machine with no Ollama at all still gets a
sensible, honest answer ("not installed", "server not running") instead of an
exception — the same design rule as the rest of the app.

Honest boundary: small models handle English far better than Tamil.  The bilingual
lexicon stays the always-available fallback, and the app says so on screen.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
#  Model catalogue — what actually fits on a normal laptop
# --------------------------------------------------------------------------- #

# ram_gb is the *total system memory* needed to run the model comfortably
# (model weights in memory + the OS + this app), not the download size.
MODEL_CATALOGUE: List[Dict[str, Any]] = [
    {
        "model": "gemma2:2b",
        "params": "2 B",
        "download_gb": 1.6,
        "ram_gb": 6,
        "tamil": "weak",
        "note_en": "Smallest useful model. Runs on almost any laptop; understands "
                   "English scam patterns, Tamil only partially.",
        "note_ta": "மிகச்சிறிய மாதிரி. பெரும்பாலான நோட்ட்புக்குகளில் இயங்கும்; ஆங்கிலம் "
                   "நன்றாக, தமிழ் பகுதியளவு.",
    },
    {
        "model": "qwen2.5:3b",
        "params": "3 B",
        "download_gb": 1.9,
        "ram_gb": 8,
        "tamil": "fair",
        "note_en": "Good balance for 8 GB machines. Strong instruction following, "
                   "reasonable Tamil.",
        "note_ta": "8 GB கணினிகளுக்கு நல்ல தேர்வு. தமிழும் ஒப்புமையாக புரியும்.",
    },
    {
        "model": "llama3.1:8b",
        "params": "8 B",
        "download_gb": 4.7,
        "ram_gb": 16,
        "tamil": "fair",
        "note_en": "The default recommendation for 16 GB. Best reasoning per GB; "
                   "Tamil is workable.",
        "note_ta": "16 GB க்கு பரிந்துரைக்கப்படும் மாதிரி. தமிழும் நன்றாக செயல்படும்.",
    },
    {
        "model": "gemma2:9b",
        "params": "9 B",
        "download_gb": 5.4,
        "ram_gb": 24,
        "tamil": "good",
        "note_en": "Needs a roomy machine. Among the better small models for Indian "
                   "languages.",
        "note_ta": "அதிக நினைவகம் தேவை. இந்திய மொழிகளுக்கு இதன் தமிழ் நிலை நல்லது.",
    },
    {
        "model": "qwen2.5:14b",
        "params": "14 B",
        "download_gb": 8.5,
        "ram_gb": 26,
        "tamil": "good",
        "note_en": "For a workstation or a gaming GPU. Multilingual by design.",
        "note_ta": "வேலைநிலை கணினி அல்லது GPU உள்ள கணினிகளுக்கு. பல மொழிகளுக்கு "
                   "रचித்தது.",
    },
]

DEFAULT_MODEL = "llama3.1:8b"
OLLAMA_PORT = 11434


# --------------------------------------------------------------------------- #
#  1. machine detection
# --------------------------------------------------------------------------- #

def _windows_ram_gb() -> Optional[float]:
    try:  # pragma: no cover - Windows only
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(status.ullTotalPhys / 1024 ** 3, 1)
    except Exception:  # noqa: BLE001 - detection must never raise
        return None
    return None


def _linux_ram_gb() -> Optional[float]:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    kb = float(line.split()[1])
                    return round(kb / 1024 ** 2, 1)
    except Exception:  # noqa: BLE001
        return None
    return None


def _mac_ram_gb() -> Optional[float]:
    try:  # pragma: no cover - macOS only
        out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                             text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return round(int(out.stdout.strip()) / 1024 ** 3, 1)
    except Exception:  # noqa: BLE001
        return None
    return None


def total_ram_gb() -> Optional[float]:
    """Total physical memory in GB, or None when it cannot be determined."""
    if sys.platform.startswith("win"):
        return _windows_ram_gb()
    if sys.platform == "darwin":
        return _mac_ram_gb()
    value = _linux_ram_gb()
    if value is not None:
        return value
    try:  # psutil is optional but very reliable when present
        import psutil  # type: ignore

        return round(psutil.virtual_memory().total / 1024 ** 3, 1)
    except Exception:  # noqa: BLE001
        return None


def free_disk_gb(path: str = ".") -> Optional[float]:
    try:
        return round(shutil.disk_usage(path).free / 1024 ** 3, 1)
    except Exception:  # noqa: BLE001
        return None


def gpu_info() -> Dict[str, Any]:
    """Best-effort GPU description (name + VRAM in GB). Never raises."""
    for command in (
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
        ["rocm-smi", "--showproductname"],
    ):
        try:
            out = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=6)
        except Exception:  # noqa: BLE001 - tool not installed
            continue
        if out.returncode != 0 or not out.stdout.strip():
            continue
        first = out.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in first.split(",")]
        vram = None
        for part in parts:
            match = re.search(r"([\d.]+)\s*MiB", part)
            if match:
                vram = round(float(match.group(1)) / 1024, 1)
        return {"name": parts[0], "vram_gb": vram, "source": command[0]}
    return {"name": None, "vram_gb": None, "source": None}


def machine_specs() -> Dict[str, Any]:
    """Everything the recommendation needs, gathered without raising."""
    ram = total_ram_gb()
    gpu = gpu_info()
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": platform.processor() or platform.machine(),
        "cores": os.cpu_count() or 1,
        "ram_gb": ram,
        "ram_text": f"{ram:.0f} GB" if ram else "unknown",
        "gpu": gpu,
        "gpu_text": (f"{gpu['name']} ({gpu['vram_gb']:.0f} GB)"
                     if gpu["name"] and gpu["vram_gb"] else (gpu["name"] or "none detected")),
        "free_disk_gb": free_disk_gb("."),
        "python": platform.python_version(),
    }


# --------------------------------------------------------------------------- #
#  2. model recommendation
# --------------------------------------------------------------------------- #

def recommend_model(specs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Pick the largest model this machine can comfortably run.

    The rule is deliberately simple and explainable: a model needs roughly
    (weights + ~2 GB for the OS and this app) of system memory, and a discrete GPU
    with enough VRAM lets us go one tier higher.  When memory cannot be read we
    recommend the safe middle option and say why.
    """
    specs = specs or machine_specs()
    ram = specs.get("ram_gb")
    gpu_vram = (specs.get("gpu") or {}).get("vram_gb") or 0.0
    usable = float(ram) if ram else 8.0
    budget = usable + (2.0 if gpu_vram >= 6 else 0.0)

    chosen = MODEL_CATALOGUE[0]
    for entry in MODEL_CATALOGUE:
        if float(entry["ram_gb"]) <= budget:
            chosen = entry
    smallest = float(MODEL_CATALOGUE[0]["ram_gb"])
    fits = budget >= smallest

    if ram is None:
        why_en = ("We could not read this machine's memory, so we picked a safe middle "
                  "model. Check the numbers above and choose a bigger one if you have "
                  "more memory.")
        why_ta = ("இந்த கணினியின் நினைவகத்தைப் படிக்க முடியவில்லை, அதனால் பாதுகாப்பான நடுத்தர "
                  "மாதிரியைத் தேர்ந்தெடுத்துள்ளோம். மேலே உள்ள எண்களைப் பார்த்து தேவைப்பட்டால் "
                  "பெரிய மாதிரியைத் தேர்வு செய்யுங்கள்.")
    elif not fits:
        why_en = (f"{ram:.0f} GB of memory detected — that is less than the smallest model "
                  f"wants ({smallest:.0f} GB). The offline lexicon is the honest choice here; "
                  f"if you still want a local model, {chosen['model']} will run but slowly.")
        why_ta = (f"{ram:.0f} GB நினைவகம் கண்டறியப்பட்டது — இது மிகச்சிறிய மாதிரிக்குத் "
                  f"தேவையானதை விட குறைவு ({smallest:.0f} GB). இங்கே இணையத்திற்று இல்லாத "
                  "மொழிப் பட்டியல் தான் சரியான தேர்வு; அப்போதும் உள்ளமை மாதிரி வேண்டுமென்றால் "
                  f"{chosen['model']} மெதுவாக இயங்கும்.")
    else:
        why_en = (f"{ram:.0f} GB of memory detected"
                  + (f" plus a {gpu_vram:.0f} GB GPU" if gpu_vram >= 6 else "")
                  + f" → {chosen['params']} parameters needs about {chosen['ram_gb']} GB, "
                  f"download {chosen['download_gb']:.1f} GB.")
        why_ta = (f"{ram:.0f} GB நினைவகம் கண்டறியப்பட்டது"
                  + (f", {gpu_vram:.0f} GB GPU உடன்" if gpu_vram >= 6 else "")
                  + f" → {chosen['params']} அளவு மாதிரிக்கு சுமார் {chosen['ram_gb']} GB "
                  f"தேவை, பதிவிறக்கம் {chosen['download_gb']:.1f} GB.")
    return {
        "model": chosen["model"],
        "params": chosen["params"],
        "download_gb": chosen["download_gb"],
        "ram_gb": chosen["ram_gb"],
        "tamil": chosen["tamil"],
        "why_en": why_en,
        "why_ta": why_ta,
        "note_en": chosen["note_en"],
        "note_ta": chosen["note_ta"],
        "alternatives": [entry["model"] for entry in MODEL_CATALOGUE
                         if entry["model"] != chosen["model"]],
        "fits": fits,
        "tight": budget < smallest + 4,
    }


# --------------------------------------------------------------------------- #
#  3. ollama control plane
# --------------------------------------------------------------------------- #

def ollama_host(cfg: Optional[Dict[str, Any]] = None) -> str:
    host = str(((cfg or {}).get("ai", {}) or {}).get("ollama_host")
               or f"http://127.0.0.1:{OLLAMA_PORT}")
    return host.rstrip("/")


def ollama_installed() -> Tuple[bool, str]:
    """(installed, detail) — detail is the version string or the reason it failed."""
    path = shutil.which("ollama")
    if not path:
        return False, "ollama was not found on PATH"
    try:
        out = subprocess.run(["ollama", "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        version = (out.stdout or out.stderr or "").strip().splitlines()[0]
        return True, version or f"found at {path}"
    except Exception as exc:  # noqa: BLE001
        return True, f"found at {path} (version check failed: {type(exc).__name__})"


def _http_json(url: str, payload: Optional[Dict[str, Any]] = None,
               timeout: float = 4.0) -> Tuple[bool, Any, str]:
    """Minimal JSON over HTTP. Returns (ok, data, detail) and never raises."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST" if data else "GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = response.read().decode("utf-8", "replace")
        return True, json.loads(body) if body else {}, ""
    except urllib.error.HTTPError as exc:
        return False, None, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - not running, no network, bad JSON
        return False, None, f"{type(exc).__name__}: {exc}"


def ollama_server_running(cfg: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    ok, _, detail = _http_json(f"{ollama_host(cfg)}/api/tags", timeout=3.0)
    return (True, "server answered") if ok else (False, detail or "server not running")


def ollama_models(cfg: Optional[Dict[str, Any]] = None) -> List[str]:
    """Models already downloaded on this machine (empty when unreachable)."""
    ok, data, _ = _http_json(f"{ollama_host(cfg)}/api/tags", timeout=3.0)
    if not ok or not isinstance(data, dict):
        return []
    names = []
    for entry in data.get("models", []) or []:
        name = entry.get("name") or entry.get("model")
        if name:
            names.append(str(name))
    return sorted(names)


def ollama_ready(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One honest status object for the UI: installed / server / model / linked."""
    installed, installed_detail = ollama_installed()
    running, running_detail = ollama_server_running(cfg)
    models = ollama_models(cfg) if running else []
    wanted = str(((cfg or {}).get("ai", {}) or {}).get("ollama_model") or DEFAULT_MODEL)
    have_model = any(m == wanted or m.startswith(f"{wanted}:") for m in models)
    return {
        "installed": installed,
        "installed_detail": installed_detail,
        "server_running": running,
        "server_detail": running_detail,
        "models": models,
        "model": wanted,
        "model_present": have_model,
        "linked": bool(installed and running and have_model),
    }


def install_commands() -> List[Dict[str, str]]:
    """The exact commands a user runs, per platform, with nothing hidden."""
    if sys.platform.startswith("win"):
        return [
            {"label": "Install Ollama (winget)",
             "command": "winget install Ollama.Ollama"},
            {"label": "…or download the installer",
             "command": "https://ollama.com/download/OllamaSetup.exe"},
            {"label": "Start the server (opens its own window)",
             "command": "ollama serve"},
            {"label": "Download a model",
             "command": f"ollama pull {DEFAULT_MODEL}"},
        ]
    if sys.platform == "darwin":
        return [
            {"label": "Install Ollama (Homebrew)",
             "command": "brew install ollama"},
            {"label": "…or download the installer",
             "command": "https://ollama.com/download/Ollama-darwin.zip"},
            {"label": "Start the server", "command": "ollama serve"},
            {"label": "Download a model", "command": f"ollama pull {DEFAULT_MODEL}"},
        ]
    return [
        {"label": "Install Ollama (one line)",
         "command": "curl -fsSL https://ollama.com/install.sh | sh"},
        {"label": "Start the server", "command": "ollama serve"},
        {"label": "Download a model", "command": f"ollama pull {DEFAULT_MODEL}"},
    ]


def ollama_start_server(cfg: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """Try to start `ollama serve` in the background. Never raises."""
    installed, detail = ollama_installed()
    if not installed:
        return False, "Ollama is not installed — run the install command first."
    running, _ = ollama_server_running(cfg)
    if running:
        return True, "The Ollama server is already running."
    try:
        flags = 0
        if sys.platform.startswith("win"):  # pragma: no cover - Windows only
            flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | \
                getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, creationflags=flags,
            start_new_session=not sys.platform.startswith("win"),
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"Could not start the server: {type(exc).__name__}: {exc}"
    for _ in range(10):
        running, _ = ollama_server_running(cfg)
        if running:
            return True, "Ollama server started."
    return False, "The server did not answer yet — open a terminal and run: ollama serve"


def ollama_pull(model: str, cfg: Optional[Dict[str, Any]] = None,
                timeout: float = 1800.0,
                progress: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
    """Download a model, streaming `ollama pull` output line by line.

    Long by nature (a GB or two over a slow line), so `progress` is called with each
    line the moment it arrives — the caller shows it, and the page stays alive.
    Returns (ok, log tail).
    """
    installed, detail = ollama_installed()
    if not installed:
        return False, "Ollama is not installed — run the install command first."

    def say(line: str) -> None:
        if progress and line:
            try:
                progress(line)
            except Exception:  # noqa: BLE001 — a UI hiccup must never kill the download
                pass

    started = time.time()
    try:
        flags = 0
        if sys.platform.startswith("win"):  # pragma: no cover - Windows only
            flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        proc = subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=flags,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"

    tail = ""
    while True:
        if time.time() - started > timeout:
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
            say("download timed out")
            how_long = (f"{timeout / 60:.0f} minutes" if timeout >= 120
                        else f"{timeout:.0f} seconds")
            return False, (f"`ollama pull {model}` was still running after {how_long} — "
                           f"on a slow connection a multi-gigabyte model takes longer "
                           f"than one button press. Run it in a terminal instead "
                           f"(ollama pull {model}); Ollama resumes what it already "
                           f"downloaded, then press Link now.")
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        tail = line.strip()
        say(tail)

    code = proc.wait()
    if code != 0:
        return False, (tail[-600:] or f"`ollama pull {model}` failed (exit {code}).")
    return True, (tail[-600:] or f"`ollama pull {model}` finished")


# --------------------------------------------------------------------------- #
#  4. the call the intent engine makes
# --------------------------------------------------------------------------- #

def ollama_generate_json(prompt: str, cfg: Optional[Dict[str, Any]] = None,
                         timeout: Optional[float] = None) -> Tuple[bool, Any, str]:
    """Ask the local model for a JSON answer. Returns (ok, parsed, detail)."""
    ai_cfg = ((cfg or {}).get("ai", {}) or {})
    model = str(ai_cfg.get("ollama_model") or DEFAULT_MODEL)
    host = ollama_host(cfg)
    limit = float(timeout or ai_cfg.get("ollama_timeout_s", 30))
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},
    }
    ok, data, detail = _http_json(f"{host}/api/generate", payload, timeout=limit)
    if not ok or not isinstance(data, dict):
        return False, None, detail or "no answer from the local model"
    text = str(data.get("response", "")).strip()
    if not text:
        return False, None, "the local model returned an empty answer"
    try:
        return True, json.loads(text), ""
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                return True, json.loads(match.group(0)), ""
            except json.JSONDecodeError:
                pass
        return False, None, "the local model did not return valid JSON"


PROBE_PROMPT = (
    "You are a payment-fraud social-engineering analyst for India.\n"
    "Read the reason a user gave for a payment and answer with JSON only:\n"
    '{"risk": 0-100, "signals": ["short phrases"], "explanation": "one line"}\n\n'
    "Reason: \"bank officer said my account will be blocked, pay now\"\n\nJSON:"
)


def test_link(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """End-to-end proof the link works: server up, model present, sensible answer."""
    status = ollama_ready(cfg)
    if not status["linked"]:
        return {"ok": False, "stage": "not_linked", "detail": status, "latency_s": None}
    ok, parsed, detail = ollama_generate_json(PROBE_PROMPT, cfg)
    if not ok:
        return {"ok": False, "stage": "model_call", "detail": detail, "latency_s": None}
    try:
        risk = float(parsed.get("risk", -1))
    except (TypeError, ValueError):
        risk = -1.0
    if not 0.0 <= risk <= 100.0:
        return {"ok": False, "stage": "bad_answer", "detail": parsed, "latency_s": None}
    return {"ok": True, "stage": "linked", "detail": parsed, "latency_s": None}
