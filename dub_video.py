#!/usr/bin/env python
"""Voice-over dubbing: English video -> Vietnamese voice, or Vietnamese video -> English voice.

  1. python dub_video.py prepare <file | YouTube link | Google Drive link> [--from auto|en|vi] [--to vi|en] [--name NAME]
        downloads if needed, transcribes with Whisper medium, cuts the speech into dubbing units and writes
        work/dub/<name>/
          dub.json               units with timing (id, start, end, src text, word budget); cached transcript
          transcript_for_llm.txt what Claude translates: "[12] 01:23-01:31 (8.2 s, max 40 words) text"
  2. Claude translates every unit and writes work/dub/<name>/translations.json   {"0": "translated text", "1": "..."}
  3. python dub_video.py render <name> [--voice KEY] [--rate N] [--bg 0.12] [--subs] [--dry-run]
        voice for every unit (sped up or placed to fit its time slot), the original sound ducked underneath,
        videos/dub/<name>/<name>-<lang>.mp4 (+ .srt, + .txt with the translated script)

Voices: --voice female|male (default female) or any key in voices.json / raw edge-tts name (en-US-GuyNeural).
Re-running render only re-synthesises units whose text, voice or rate changed (cached in work/dub/<name>/units/).
"""
import argparse, asyncio, json, math, re, subprocess, sys, wave
import compat
from pathlib import Path

import numpy as np

import auto_subtitle as asub
import clip_video as cv
import karaoke
import short_video as sv
import voices

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "work" / "dub"
OUT = ROOT / "videos" / "dub"
SR = 44100
LEAD = 0.08            # edge-tts files start a little before the first word; place them this much early
MAX_UNIT = 12.0        # longest dubbing unit in seconds
WORDS_PER_SEC = {"vi": 4.8, "en": 2.9}   # normal speaking pace, used for the word budget shown to the translator


def log(msg):
    print(f"[dub-video] {msg}", flush=True)


# ---------------------------------------------------------------- units
def _split(words):
    """Split a list of timed words into pieces of at most MAX_UNIT seconds, preferring sentence and clause ends."""
    if not words or words[-1]["e"] - words[0]["s"] <= MAX_UNIT or len(words) < 6:
        return [words]
    mid = (words[0]["s"] + words[-1]["e"]) / 2
    best, best_score = None, None
    for i in range(2, len(words) - 2):
        left, right = words[i]["e"] - words[0]["s"], words[-1]["e"] - words[i + 1]["s"]
        if left < 3 or right < 3:
            continue
        w = words[i]["w"]
        rank = 0 if re.search(r"[.?!…]$", w) else 1 if re.search(r"[,;:]$", w) else 2
        score = (rank, abs(words[i]["e"] - mid))
        if best_score is None or score < best_score:
            best, best_score = i, score
    if best is None:
        best = len(words) // 2
    return _split(words[:best + 1]) + _split(words[best + 1:])


def build_units(segments):
    pieces = []
    for s in segments:
        words = s.get("words") or []
        if words and s["end"] - s["start"] > MAX_UNIT:
            for part in _split(words):
                pieces.append({"start": part[0]["s"], "end": part[-1]["e"], "src": " ".join(w["w"] for w in part)})
        else:
            pieces.append({"start": s["start"], "end": s["end"], "src": s["text"].strip()})
    units = []
    for p in pieces:
        last = units[-1] if units else None
        if last and last["end"] - last["start"] < 2.0 and p["start"] - last["end"] < 0.6 and p["end"] - last["start"] <= MAX_UNIT:
            last["end"] = p["end"]
            last["src"] += " " + p["src"]
        else:
            units.append(dict(p))
    for i, u in enumerate(units):
        u["id"] = i
        u["start"], u["end"] = round(u["start"], 2), round(u["end"], 2)
    return units


def budget(dur, lang):
    return max(2, round(dur * WORDS_PER_SEC[lang] * 1.15))


# ---------------------------------------------------------------- prepare
def cmd_prepare(a):
    name = a.name or cv.default_name(a.source)
    d = BASE / name
    d.mkdir(parents=True, exist_ok=True)
    src = cv.fetch(a.source, d)
    W, H, dur = asub.ffprobe(src)
    f = d / "dub.json"
    if f.exists() and not a.force:
        data = json.loads(f.read_text(encoding="utf-8"))
        log(f"using the cached transcript ({len(data['units'])} units); --force to transcribe again")
    else:
        language, segments = asub.transcribe(src, getattr(a, "src_lang"), d)
        if not segments:
            sys.exit("no speech found in this video")
        data = {"source": str(src), "duration": dur, "width": W, "height": H, "source_lang": language, "units": build_units(segments)}
    target = a.to or ("en" if data["source_lang"] == "vi" else "vi")
    if target == data["source_lang"]:
        sys.exit(f"the video is already in '{target}'. Choose --to {'en' if target == 'vi' else 'vi'}.")
    data["target_lang"] = target
    for u in data["units"]:
        u["budget"] = budget(u["end"] - u["start"], target)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    unit_word = "words" if target == "en" else "words (syllables)"
    lines = [f"[{u['id']}] {cv.mmss(u['start'])}-{cv.mmss(u['end'])} ({u['end'] - u['start']:.1f} s, max {u['budget']} {unit_word}) {u['src']}"
             for u in data["units"]]
    (d / "transcript_for_llm.txt").write_text(
        f"# {name}  {data['source_lang']} -> {target}  duration={cv.mmss(dur)}  {W}x{H}\n" + "\n".join(lines) + "\n", encoding="utf-8")
    log(f"ready: {d}")
    log(f"  {cv.mmss(dur)}, {data['source_lang']} -> {target}, {len(data['units'])} units, "
        f"{sum(len(u['src'].split()) for u in data['units'])} source words")
    log(f"  next: translate {d / 'transcript_for_llm.txt'} into {d / 'translations.json'}")


# ---------------------------------------------------------------- synthesis
async def synth_retry(cfg, text, rate, out):
    """edge-tts sometimes refuses one text+setting; nearby rate/pitch values work and sound the same."""
    tries = [(0, 0)] + [(d, dp) for k in range(1, 7) for d in (k, -k) for dp in (0, 2, -2)]
    if cfg["engine"] != "edge":
        tries = [(0, 0)]
    r0, p0, v0 = voices.apply_preset(cfg, rate, 0, 0)
    for dr, dp in tries:
        try:
            await voices.synth(cfg, text, r0 + dr, p0 + dp, v0, out)
            return sv.probe_duration(out)
        except Exception:
            await asyncio.sleep(1.0)
    sys.exit(f"voice synthesis failed for: {text[:60]}")


async def make_unit(cfg, u, text, base, allowed, wdir, sem):
    """Synthesise one unit so that it fits `allowed` seconds: faster speech first, then a mild tempo-up."""
    meta, wav, piece = wdir / f"u{u['id']}.json", wdir / f"u{u['id']}.wav", wdir / f"u{u['id']}.mp3"
    key = [text, cfg["key"], base, round(allowed, 2)]
    if meta.exists() and wav.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        if m.get("key") == key:
            return m
    async with sem:
        rate = base
        d = await synth_retry(cfg, text, rate, piece)
        tempo = 1.0
        if d > allowed:
            rate = min(base + 50, base + math.ceil((d / allowed - 1) * 100) + 2)
            d = await synth_retry(cfg, text, rate, piece)
            if d > allowed:
                tempo = min(1.35, d / allowed)
        words = sv._word_times(piece, text)
    args = ["-i", piece] + (["-af", f"atempo={tempo:.4f}"] if tempo > 1.001 else []) + ["-ar", SR, "-ac", 1, wav]
    sv.ff(*args)
    dur = sv.probe_duration(wav)
    m = {"key": key, "rate": rate, "tempo": round(tempo, 3), "dur": dur, "truncated": dur > allowed + 0.03,
         "words": [{"w": w["w"], "s": w["s"] / tempo, "e": w["e"] / tempo} for w in words]}
    meta.write_text(json.dumps(m), encoding="utf-8")
    return m


def read_wav(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


# ---------------------------------------------------------------- mixing
def build_dub_track(units, results, total):
    track = np.zeros(int(total * SR) + SR, dtype=np.int32)
    for u, r in zip(units, results):
        x = read_wav(Path(r["wav"]))
        t0 = max(0.0, u["start"] - LEAD)
        n = min(len(x), int(r["allowed"] * SR + 0.05 * SR))
        x = x[:n].astype(np.int32)
        if r["truncated"] and n > 2000:
            x[-2000:] = (x[-2000:] * np.linspace(1, 0, 2000)).astype(np.int32)       # short fade instead of a click
        o = int(t0 * SR)
        end = min(len(track), o + len(x))
        track[o:end] += x[:end - o]
        r["place"] = t0
    return np.clip(track, -32768, 32767).astype(np.int16)


def mix(orig_wav, dub, bg, out_wav):
    """Original audio ducked to `bg` while the dub speaks, dub normalised to a steady level."""
    hop = SR // 50
    frames = len(dub) // hop + 1
    pad = np.zeros(frames * hop - len(dub), dtype=np.int16)
    d = np.concatenate([dub, pad]).astype(np.float32) / 32768
    rms = np.sqrt((d.reshape(frames, hop) ** 2).mean(axis=1))
    active = (rms > 0.01).astype(np.float32)
    env, cur = np.zeros(frames, dtype=np.float32), 0.0
    for i, v in enumerate(active):                       # fast attack (2 frames), slow release (0.4 s)
        cur = min(v, cur + 0.5) if v > cur else max(v, cur - 0.05)
        env[i] = cur
    gain = 1 - (1 - bg) * env
    act = d[np.repeat(active > 0.5, hop)]
    g_dub = min(4.0, 0.12 / max(1e-4, float(np.sqrt((act ** 2).mean())))) if act.size else 1.0
    block = SR * 20
    with wave.open(str(orig_wav)) as src, wave.open(str(out_wav), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(SR)
        pos = 0
        while True:
            raw = src.readframes(block)
            if not raw:
                break
            o = np.frombuffer(raw, dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768
            n = len(o)
            f0 = pos // hop
            gk = np.repeat(gain[f0:f0 + n // hop + 2], hop)[:n]
            if len(gk) < n:
                gk = np.pad(gk, (0, n - len(gk)), constant_values=1.0)
            dk = d[pos:pos + n] * g_dub
            if len(dk) < n:
                dk = np.pad(dk, (0, n - len(dk)))
            mixed = np.clip(o * gk[:, None] + dk[:, None], -0.99, 0.99)
            out.writeframes((mixed * 32767).astype(np.int16).tobytes())
            pos += n


# ---------------------------------------------------------------- render
def srt_ts(t):
    return karaoke.srt_ts(t)


def resolve_voice(a, target):
    key = (a.voice or "female").strip()
    if target == "en" and key.lower() in ("female", "male"):
        key = "en-" + key.lower()
    if target == "vi" and key.lower().startswith("en-"):
        sys.exit("an English voice was chosen for Vietnamese output; use --voice female|male")
    return voices.resolve(key)


def cmd_render(a):
    d = BASE / a.name
    data = json.loads((d / "dub.json").read_text(encoding="utf-8"))
    tfile = Path(a.translations) if a.translations else d / "translations.json"
    if not tfile.exists():
        sys.exit(f"no translations yet: write {tfile} as {{\"0\": \"text\", ...}} (Claude does this from transcript_for_llm.txt)")
    tr = json.loads(tfile.read_text(encoding="utf-8"))
    units, target = data["units"], data["target_lang"]
    missing = [u["id"] for u in units if not str(tr.get(str(u["id"]), "")).strip()]
    if missing:
        sys.exit(f"{len(missing)} units have no translation, for example ids {missing[:10]}")
    cfg = resolve_voice(a, target)
    total = data["duration"]
    base = int(a.rate)
    log(f"{len(units)} units, voice {cfg['key']}, rate {base:+d}%, original sound at {a.bg:.0%} under the dub")

    over = []
    for i, u in enumerate(units):
        text = " ".join(str(tr[str(u["id"])]).split())
        nxt = units[i + 1]["start"] if i + 1 < len(units) else total
        orig = u["end"] - u["start"]
        u["text"] = text
        u["allowed"] = max(0.8, min(nxt - u["start"] - 0.06, orig * 1.35 + 0.3))
        if len(text.split()) > u["budget"] * 1.4:
            over.append(u["id"])
    if over:
        log(f"warning: {len(over)} translations are much longer than their time slot (ids {over[:12]}); they will be sped up or cut")
    if a.dry_run:
        log("dry run: nothing synthesised")
        return

    wdir = d / "units"
    wdir.mkdir(exist_ok=True)

    async def go():
        sem = asyncio.Semaphore(4)
        return await asyncio.gather(*[make_unit(cfg, u, u["text"], base, u["allowed"], wdir, sem) for u in units])

    results = asyncio.run(go())
    for u, r in zip(units, results):
        r["wav"] = str(wdir / f"u{u['id']}.wav")
        r["allowed"] = u["allowed"]
    fast = sum(1 for r in results if r["rate"] > base + 8 or r["tempo"] > 1.0)
    cut = [u["id"] for u, r in zip(units, results) if r["truncated"]]
    log(f"synthesised {len(units)} units; {fast} sped up to fit, {len(cut)} cut" + (f" (ids {cut[:15]})" if cut else ""))

    src = Path(data["source"])
    log("mixing ...")
    dub = build_dub_track(units, results, total)
    orig_wav = d / "orig.wav"
    sv.ff("-i", src, "-vn", "-ac", 2, "-ar", SR, orig_wav)
    mixed = d / "mixed.wav"
    mix(orig_wav, dub, a.bg, mixed)

    odir = OUT / a.name
    odir.mkdir(parents=True, exist_ok=True)
    out = odir / f"{a.name}-{target}.mp4"
    segs = []
    for u, r in zip(units, results):
        ws = [{"w": w["w"], "s": r["place"] + w["s"], "e": r["place"] + w["e"]} for w in r["words"]]
        segs.append({"start": r["place"], "end": r["place"] + r["dur"], "text": u["text"], "words": ws})
    (odir / f"{a.name}-{target}.srt").write_text(
        "".join(f"{i}\n{srt_ts(s['start'])} --> {srt_ts(s['end'])}\n{s['text']}\n\n" for i, s in enumerate(segs, 1)), encoding="utf-8")
    (odir / f"{a.name}-{target}.txt").write_text("\n".join(f"[{cv.mmss(s['start'])}] {s['text']}" for s in segs), encoding="utf-8")

    mux = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-i", str(mixed), "-map", "0:v:0", "-map", "1:a:0"]
    if a.subs:
        ass = d / "subs.ass"
        ass.write_text(karaoke.build_ass(segs, data["width"], data["height"]), encoding="utf-8")
        log(f"burning {target} subtitles (re-encodes the video) ...")
        cmd = mux + ["-vf", compat.ass_filter(ass.relative_to(ROOT).as_posix()), "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)]
        subprocess.run(cmd, cwd=ROOT, check=True)
    else:
        cmd = mux + ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)]
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:                 # codec not allowed in mp4: re-encode
            log("the video codec cannot be copied into mp4, re-encoding ...")
            cmd = mux + ["-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                         "-movflags", "+faststart", "-shortest", str(out)]
            subprocess.run(cmd, cwd=ROOT, check=True)
    log(f"done: {out.relative_to(ROOT)}  {sv.probe_duration(out):.1f}s  {out.stat().st_size / 1048576:.1f} MB")
    log(f"  translated script: {out.with_suffix('.txt').relative_to(ROOT)}, subtitles file: {out.with_suffix('.srt').relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description="Voice-over dubbing between English and Vietnamese.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("source")
    p.add_argument("--from", dest="src_lang", default="auto", help="language in the video: en, vi or auto")
    p.add_argument("--to", choices=["vi", "en"], help="voice-over language (default: the other one)")
    p.add_argument("--name")
    p.add_argument("--force", action="store_true", help="transcribe again")
    p.set_defaults(fn=cmd_prepare)
    r = sub.add_parser("render")
    r.add_argument("name")
    r.add_argument("--voice", help="female | male | any voices.json key | edge-tts voice name")
    r.add_argument("--rate", type=int, default=0, help="base speaking speed in %% (default 0)")
    r.add_argument("--bg", type=float, default=0.12, help="original sound level under the dub, 0-1 (0 = mute it)")
    r.add_argument("--subs", action="store_true", help="burn karaoke subtitles in the voice-over language")
    r.add_argument("--translations", help="translations file (default work/dub/<name>/translations.json)")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(fn=cmd_render)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
