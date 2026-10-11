#!/usr/bin/env python
"""Download the speech models this toolbox needs (they are too large to keep in git).

  python setup_models.py              # Whisper medium (about 1.5 GB) - needed by /auto-subtitle and /clip-video
  python setup_models.py --piper      # also the 3 offline Vietnamese Piper voices (about 90 MB, optional)
  python setup_models.py --skip-whisper --piper
"""
import argparse
import sys
import urllib.request
from pathlib import Path

import compat  # noqa: F401  (UTF-8 console on Windows)

ROOT = Path(__file__).resolve().parent
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN"
PIPER = [
    "vais1000/medium/vi_VN-vais1000-medium",
    "25hours_single/low/vi_VN-25hours_single-low",
    "vivos/x_low/vi_VN-vivos-x_low",
]


def whisper():
    dest = ROOT / "models" / "faster-whisper-medium"
    if (dest / "model.bin").exists():
        print(f"Whisper medium already there: {dest}")
        return
    from huggingface_hub import snapshot_download
    print("Downloading Whisper medium (about 1.5 GB), this takes a few minutes ...")
    snapshot_download("Systran/faster-whisper-medium", local_dir=str(dest))
    print("done:", dest)


def piper():
    dest = ROOT / "models" / "piper"
    dest.mkdir(parents=True, exist_ok=True)
    for item in PIPER:
        name = item.split("/")[-1]
        for ext in (".onnx", ".onnx.json"):
            out = dest / (name + ext)
            if out.exists():
                continue
            print("downloading", out.name)
            urllib.request.urlretrieve(f"{PIPER_BASE}/{item}{ext}", out)
    print("Piper voices ready:", dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--piper", action="store_true", help="also download the offline Piper voices")
    ap.add_argument("--skip-whisper", action="store_true")
    a = ap.parse_args()
    try:
        if not a.skip_whisper:
            whisper()
        if a.piper:
            piper()
    except Exception as e:
        sys.exit(f"download failed: {type(e).__name__}: {e}\nCheck the internet connection and run again (finished files are kept).")


if __name__ == "__main__":
    main()
