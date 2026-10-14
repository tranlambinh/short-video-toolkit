#!/usr/bin/env bash
# macOS / Linux setup:  bash setup.sh
set -e
cd "$(dirname "$0")"
say() { printf "\n\033[36m%s\033[0m\n" "$1"; }
need() { command -v "$1" >/dev/null 2>&1 || { printf "\033[31mMissing: %s. %s\033[0m\n" "$1" "$2"; exit 1; }; }

say "1/6 Checking tools"
PY=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3 || true)
[ -n "$PY" ] || { echo "Install Python 3.10-3.12 (brew install python@3.12)"; exit 1; }
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then say "Installing ffmpeg with Homebrew"; brew install ffmpeg
  else echo "Install ffmpeg (brew install ffmpeg, or your package manager)"; exit 1; fi
fi
need docker "Install Docker Desktop (docker.com) and start it."

say "2/6 Python environment (.venv)"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

say "3/6 Browser for /news-video (used when Chrome is not installed)"
.venv/bin/python -m playwright install chromium

say "4/6 Speech models (Whisper medium 1.5 GB, offline voices about 0.9 GB)"
.venv/bin/python setup_models.py --piper --vieneu

say "5/6 Settings"
if [ ! -f .env ]; then cp .env.example .env; echo "Created .env. Open it and paste your free Pexels key (pexels.com/api)."; fi
mkdir -p assets/music work videos

say "6/6 Docker image for stock footage"
docker compose pull

say "Checking everything"
.venv/bin/python check.py || true
printf "\n\033[32mNext: add a royalty-free .mp3 to assets/music, then every time:\n  source .venv/bin/activate\n  claude\033[0m\n"
