#!/usr/bin/env python
"""Make a short sample of every voice in voices.json so they can be compared by ear.

  python voice_demo.py                 # all voices -> videos/voice-samples/<key>.mp3
  python voice_demo.py female-young piper-vais        # only these
  python voice_demo.py --check         # also report pitch per sentence and how well Whisper understands each voice

Each sample uses the same per-sentence delivery as the videos (question rises, closing line slows).
"""
import argparse, asyncio, difflib, re, subprocess, sys, wave
from pathlib import Path

import numpy as np

import short_video as sv
import voices

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "videos" / "voice-samples"
SENTENCES = [
    "Chào các bạn, hôm nay mình muốn kể một câu chuyện nhỏ.",
    "Bạn đã bao giờ tự hỏi, ai sẽ ở bên mình khi mệt?",
    "Hãy cho phép mình nghỉ ngơi một chút!",
    "Cảm ơn bạn đã lắng nghe.",
]


def f0_median(path):
    w = wave.open(str(path))
    sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(float).reshape(-1, ch).mean(1) / 32768
    fl, hop = int(0.04 * sr), int(0.01 * sr)
    lo, hi = int(sr / 400), int(sr / 60)
    out = []
    for s in range(0, len(x) - fl, hop):
        fr = x[s:s + fl] - x[s:s + fl].mean()
        if np.sqrt((fr ** 2).mean()) < 0.01:
            continue
        ac = np.correlate(fr, fr, "full")[fl - 1:]
        ac /= ac[0] + 1e-9
        k = lo + np.argmax(ac[lo:hi])
        if ac[k] > 0.4:
            out.append(sr / k)
    return float(np.median(out)) if out else 0.0


async def make(key, base_rate):
    cfg = voices.resolve(key)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f"_{cfg['key']}"
    tmp.mkdir(exist_ok=True)
    parts, stats = [], []
    for j, text in enumerate(SENTENCES):
        last = j == len(SENTENCES) - 1
        r, pitch, vol, pause = sv.prosody(text, 1, last, base_rate)
        r, pitch, vol = voices.apply_preset(cfg, r, pitch, vol)
        piece = tmp / f"{j}.mp3"
        for attempt, (dr, dp) in enumerate([(0, 0)] + [(d, p) for k in range(1, 7) for d in (k, -k) for p in (0, 2, -2)]):
            try:
                await voices.synth(cfg, text, r + dr, pitch + dp, vol, piece)
                break
            except Exception:
                if cfg["engine"] != "edge":
                    raise
                await asyncio.sleep(1.5)
        else:
            sys.exit(f"{key}: synthesis failed")
        wav = tmp / f"{j}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(piece), "-ar", "24000", "-ac", "1", str(wav)], check=True)
        parts.append(wav)
        stats.append((text, f0_median(wav)))
        if pause > 0:
            gap = tmp / f"gap{int(pause * 100)}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t",
                            str(pause), str(gap)], check=True)
            parts.append(gap)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    sample = OUT / f"{cfg['key']}.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame",
                    "-q:a", "2", str(sample)], check=True)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return sample, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--rate", type=int, default=5, help="base rate %% like a spec file (default +5)")
    a = ap.parse_args()
    keys = a.keys or list(voices.load_voices().keys())
    model = None
    if a.check:
        from faster_whisper import WhisperModel
        model = WhisperModel(str(ROOT / "models" / "faster-whisper-medium"), device="cpu", compute_type="int8", cpu_threads=11)
    norm = lambda s: re.sub(r"[^\wÀ-ỹ ]", "", s.lower()).split()
    for key in keys:
        sample, stats = asyncio.run(make(key, a.rate))
        line = f"{key:18} {sample.relative_to(ROOT)}"
        if a.check:
            segs, _ = model.transcribe(str(sample), language="vi", beam_size=5)
            hyp = " ".join(s.text for s in segs)
            ref = " ".join(t for t, _ in stats)
            match = difflib.SequenceMatcher(None, norm(ref), norm(hyp)).ratio() * 100
            line += "   F0 per sentence: " + " ".join(f"{f:.0f}" for _, f in stats) + f" Hz   Whisper match {match:.0f}%"
        print(line, flush=True)


if __name__ == "__main__":
    main()
