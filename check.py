#!/usr/bin/env python
"""Check that this computer is ready to make videos:  python check.py"""
import importlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import compat  # noqa: F401

ROOT = Path(__file__).resolve().parent
problems = []


def row(ok, name, detail="", fix="", required=True):
    mark = "OK  " if ok else ("FAIL" if required else "warn")
    print(f"[{mark}] {name}" + (f": {detail}" if detail else ""), flush=True)
    if not ok:
        problems.append((required, name, fix))


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception:
        return None


def main():
    v = sys.version_info
    row((3, 10) <= (v.major, v.minor) < (3, 14), "Python", f"{v.major}.{v.minor}.{v.micro}",
        "Install Python 3.10, 3.11 or 3.12 (python.org).")

    for mod, pkg in [("edge_tts", "edge-tts"), ("faster_whisper", "faster-whisper"), ("piper", "piper-tts"),
                     ("playwright", "playwright"), ("trafilatura", "trafilatura"), ("cv2", "opencv-python-headless"),
                     ("PIL", "pillow"), ("numpy", "numpy"), ("yt_dlp", "yt-dlp"), ("gdown", "gdown")]:
        try:
            importlib.import_module(mod)
            row(True, f"package {pkg}")
        except Exception:
            row(False, f"package {pkg}", "missing", "Activate the virtual environment, then: pip install -r requirements.txt")
    try:
        importlib.import_module("vieneu")
        row(True, "package vieneu", "offline VieNeu-TTS voices", required=False)
    except Exception:
        row(False, "package vieneu", "missing (optional)", "pip install vieneu, then python setup_models.py --skip-whisper --vieneu", required=False)

    ff = shutil.which("ffmpeg")
    row(bool(ff), "ffmpeg", ff or "not found", "Windows: winget install Gyan.FFmpeg   |   macOS: brew install ffmpeg")
    if ff:
        filters = run(["ffmpeg", "-hide_banner", "-filters"])
        text = (filters.stdout if filters else "") or ""
        row(" ass " in text, "ffmpeg subtitles filter (libass)", "", "Install a full ffmpeg build (Gyan.FFmpeg or brew ffmpeg).")
        row("rubberband" in text, "ffmpeg rubberband filter", "only for the offline Piper / VieNeu voices", "Optional; the full ffmpeg builds include it.", required=False)

    d = shutil.which("docker")
    row(bool(d), "Docker", d or "not found", "Install Docker Desktop (docker.com) and start it.")
    if d:
        info = run(["docker", "info"])
        up = bool(info and info.returncode == 0)
        row(up, "Docker is running", "", "Start Docker Desktop and wait until it says it is running.")
        if up:
            ps = run(["docker", "ps", "--filter", "name=short-video-maker", "--format", "{{.Status}}"])
            st = (ps.stdout.strip() if ps else "")
            row(bool(st), "short-video-maker container", st or "not running (it starts by itself on the first video)", "docker compose up -d", required=False)

    env = ROOT / ".env"
    key = ""
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("PEXELS_API_KEY="):
                key = line.split("=", 1)[1].strip()
    row(bool(key), "PEXELS_API_KEY in .env", "set" if key else "empty", "Copy .env.example to .env and paste your free Pexels key (pexels.com/api).")

    chrome = shutil.which("google-chrome") or shutil.which("chrome") or any(Path(p).exists() for p in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app"))
    bundled = False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            bundled = Path(p.chromium.executable_path).exists()
    except Exception:
        pass
    row(bool(chrome) or bundled, "Chrome or Playwright Chromium (for /news-video)",
        "Chrome" if chrome else ("bundled Chromium" if bundled else "none"), "python -m playwright install chromium")

    row((ROOT / "models" / "faster-whisper-medium" / "model.bin").exists(), "Whisper medium model",
        "", "python setup_models.py", required=False)
    row((ROOT / "models" / "piper").exists(), "Piper offline voices", "optional", "python setup_models.py --piper", required=False)
    row((ROOT / "models" / "faster-whisper-base" / "model.bin").exists(), "Whisper base (karaoke timing for VieNeu voices)",
        "optional", "python setup_models.py --skip-whisper --vieneu", required=False)

    music = [p for p in (ROOT / "assets" / "music").glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg", ".flac")]
    row(bool(music), "background music in assets/music", f"{len(music)} file(s)",
        "Add a royalty-free .mp3 (see assets/music/README.md). Without it videos have voice only.", required=False)

    try:
        urllib.request.urlopen("https://speech.platform.bing.com", timeout=8)
        net = True
    except urllib.error.HTTPError:
        net = True
    except Exception:
        net = False
    row(net, "internet access to edge-tts voices", "", "edge-tts needs internet. Use the offline voices (--voice vieneu-maianh or piper-vais) without it.", required=False)

    fails = [p for p in problems if p[0]]
    print()
    if fails:
        print("Fix these first:")
        for _, name, fix in fails:
            print(f"  - {name}: {fix}")
        sys.exit(1)
    warns = [p for p in problems if not p[0]]
    print("Ready." + (f" ({len(warns)} optional item(s) above can be improved.)" if warns else ""))


if __name__ == "__main__":
    main()
