#!/usr/bin/env python
"""Turn a Vietnamese scene script into vertical (9:16) short videos with karaoke subtitles.

Usage:  python short_video.py specs/<slug>.json [--mode voice|music|both] [--voice KEY]
        python short_video.py --list-voices      (voice keys come from voices.json)
        defaults: --mode voice  --voice female   (--reuse-footage / --skip-render for quick re-mixes)

Spec JSON:
{
  "slug": "tuoi-40",                                  (optional, default: file name)
  "voice": "vi-VN-HoaiMyNeural", "rate": "+10%",      (optional)
  "music": "No.2 Remembering Her - Esther Abrami.mp3",(optional, from short-video-maker library)
  "scenes": [ {"vi": "Vietnamese narration/subtitle text", "terms": ["english pexels", "search terms"]} ]
}

Outputs (videos/<slug>/):
  <slug>-voice.mp4        (default) female voice-over + quiet music + purple karaoke subtitles
  <slug>-voice-male.mp4   same with the male voice (--voice male); other voices: <slug>-voice-<key>.mp4
  <slug>-music.mp4        loud music + purple karaoke subtitles, no voice-over (--mode music or both)
Both are 1080x1920 H.264/AAC, fine for TikTok, YouTube Shorts and Reels.
"""
import argparse, asyncio, json, math, os, re, subprocess, sys, textwrap, time, urllib.request
import compat
from pathlib import Path

import profiles
import voices

ROOT = Path(__file__).resolve().parent
API = "http://localhost:3123"
CONTAINER = "short-video-maker"
DEFAULT_MUSIC = "No.2 Remembering Her - Esther Abrami.mp3"
TAIL = 1.0                 # seconds of picture after the last word
SUB_Y = 1242               # fixed top of the first subtitle line: text starts 676 px above the bottom edge (frame is 1920 high)
KOKORO_WORDS_PER_SEC = 2.57
FILLER = ("breathe slowly and enjoy this quiet moment of life while time keeps moving gently "
          "forward and everything finds its place").split()


def log(msg):
    print(f"[short-video] {msg}", flush=True)


def run(args, **kw):
    return subprocess.run(args, cwd=ROOT, check=True, **kw)


def ff(*args):
    run(["ffmpeg", "-v", "error", "-y", *map(str, args)])


def probe_duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], cwd=ROOT)
    return float(out.decode().strip())


def http_json(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ---------------------------------------------------------------- server
def ensure_server():
    try:
        http_json(f"{API}/health", timeout=5)
    except Exception:
        log("short-video-maker is not running, starting it with docker compose ...")
        run(["docker", "compose", "up", "-d"])
        for _ in range(30):
            time.sleep(3)
            try:
                http_json(f"{API}/health", timeout=5)
                break
            except Exception:
                pass
        else:
            sys.exit("short-video-maker did not come up. Check: docker logs short-video-maker")
    patched = subprocess.run(
        ["docker", "exec", CONTAINER, "grep", "-c", "hidden", "/app/dist/components/videos/PortraitVideo.js"],
        capture_output=True, text=True)
    if patched.stdout.strip() in ("", "0"):
        sys.exit("The caption-hiding patch is not mounted (patch/PortraitVideo.js in docker-compose.yml).")


def ensure_music(name, workdir, need=False):
    """Background track from assets/music. The named file is used when present; otherwise the first audio file in
    that folder; with no music at all, a silent track (voice-only video). need=True (music-only mode) refuses to go silent."""
    folder = ROOT / "assets" / "music"
    named = folder / name if name else None
    if named and named.exists():
        return named
    found = sorted(p for p in folder.glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg", ".flac")) if folder.exists() else []
    if found:
        log(f"music '{name}' not found in assets/music, using '{found[0].name}' instead")
        return found[0]
    if need:
        sys.exit("No music in assets/music. Put a royalty-free .mp3 there (see assets/music/README.md), then run again.")
    log("no music in assets/music: the video will have the voice only (add an .mp3 there to get background music)")
    silent = workdir / "silence.wav"
    if not silent.exists():
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", 180, silent)
    return silent


# ---------------------------------------------------------------- voice
def split_sentences(text):
    return [p.strip() for p in re.split(r"(?<=[.?!])\s+", text.strip()) if p.strip()]


def prosody(sentence, scene_idx, is_last, base):
    """Return (rate %, pitch Hz, volume %, pause seconds after) so the delivery rises and falls with meaning."""
    rate, pitch, vol, pause = base, 0, 0, 0.25
    if sentence.endswith("?"):
        rate, pitch, pause = base - 4, 10, 0.40          # questions: slower, rising pitch
    elif sentence.endswith("!"):
        rate, pitch, vol, pause = base + 2, 8, 10, 0.30   # calls to action: brighter, louder
    elif scene_idx == 0:
        pitch, vol = 5, 8                                 # hook: a little higher and louder
    if is_last:
        rate, pitch, pause = base - 6, pitch - 3, 0.0     # closing line: warmer and slower
    return rate, pitch, vol, pause


def _word_times(piece, text):
    """Spoken word times (relative to the sentence start) from edge-tts, or [] when they do not match the text."""
    f = Path(piece).with_suffix(".words.json")
    try:
        ws = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []
    toks = text.split()
    if not ws or len(ws) != len(toks):
        return []
    out = []
    for k, (w, tok) in enumerate(zip(ws, toks)):
        end = ws[k + 1]["s"] if k + 1 < len(ws) else w["e"]      # a word lasts until the next one starts
        out.append({"w": tok, "s": w["s"], "e": max(end, w["s"] + 0.05)})
    return out


async def _tts_all(spec, workdir):
    """Per sentence synthesis with its own prosody, joined with natural pauses. Returns sentence timings."""
    base = int(spec["rate"].rstrip("%"))
    expressive = spec.get("expressive", True)
    n = len(spec["scenes"])
    res = []
    for i, sc in enumerate(spec["scenes"]):
        sents = split_sentences(sc["vi"]) if expressive else [sc["vi"].strip()]
        parts, timing, t = [], [], 0.0
        for j, text in enumerate(sents):
            last = expressive and i == n - 1 and j == len(sents) - 1
            r, pitch, vol, pause = prosody(text, i, last, base) if expressive else (base, 0, 0, 0.0)
            k = float(spec.get("express", 1.0))         # >1 = more expressive: bigger rises, falls and tempo changes
            if k != 1.0:
                r, pitch, vol = base + round((r - base) * k), round(pitch * k), round(vol * k)
                pause = pause * (1 + (k - 1) * 0.5)
            r, pitch, vol = voices.apply_preset(spec["voice_cfg"], r, pitch, vol)
            piece = workdir / f"s{i}_{j}.mp3"
            # edge-tts sometimes returns NoAudioReceived for one text+rate combo but accepts a rate that is
            # 1-3 % different (or a pitch 2 Hz different), so retries walk through nearby values (inaudible difference).
            tries = [(0, 0)] + [(d, dp) for k in range(1, 7) for d in (k, -k) for dp in (0, 2, -2)]
            if spec["voice_cfg"]["engine"] != "edge":
                tries = [(0, 0)]                          # offline voices do not need the retry dance
            for attempt, (dr, dp) in enumerate(tries):
                try:
                    await voices.synth(spec["voice_cfg"], text, r + dr, pitch + dp, vol, piece)
                    if attempt:
                        log(f"  scene {i + 1}.{j + 1}: ok at rate {r + dr:+d}% pitch {pitch + dp:+d}Hz after {attempt} retries")
                    break
                except Exception:
                    await asyncio.sleep(1.5)
            else:
                sys.exit(f"voice synthesis failed for scene {i + 1}, sentence {j + 1}, at every setting tried")
            wav = workdir / f"s{i}_{j}.wav"
            ff("-i", piece, "-ar", 44100, "-ac", 2, wav)
            d = probe_duration(wav)
            timing.append({"start": t, "dur": d, "text": text, "words": _word_times(piece, text)})
            parts.append(f"file '{wav.name}'\n")
            t += d
            if pause > 0:
                gap = workdir / f"gap{int(pause * 100)}.wav"
                if not gap.exists():
                    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", pause, gap)
                parts.append(f"file '{gap.name}'\n")
                t += pause
        (workdir / f"l{i}.txt").write_text("".join(parts), encoding="utf-8")
        ff("-f", "concat", "-safe", "0", "-i", workdir / f"l{i}.txt", "-c:a", "libmp3lame", "-q:a", 2,
           workdir / f"s{i}.mp3")
        res.append(timing)
    return res


# ---------------------------------------------------------------- picture
def render_scene_picture(i, sc, target, workdir, reuse=False):
    """Render one scene's stock footage (no captions, muted) with short-video-maker, fit to `target` seconds."""
    raw = workdir / f"raw{i}.mp4"
    if not (reuse and raw.exists()):
        n_words = math.ceil(target * KOKORO_WORDS_PER_SEC * 1.25)  # overshoot, then trim
        filler = " ".join(FILLER[k % len(FILLER)] for k in range(n_words))
        body = {"scenes": [{"text": filler, "searchTerms": sc["terms"]}],
                "config": {"captionBackgroundColor": "hidden", "musicVolume": "muted", "voice": "am_adam",
                           "orientation": "portrait", "paddingBack": 0, "music": "chill"}}
        vid = http_json(f"{API}/api/short-video", body)["videoId"]
        for _ in range(180):
            st = http_json(f"{API}/api/short-video/{vid}/status")["status"]
            if st == "ready":
                break
            if st == "failed":
                sys.exit(f"short-video-maker failed on scene {i + 1}")
            time.sleep(5)
        else:
            sys.exit(f"Timed out rendering scene {i + 1}")
        urllib.request.urlretrieve(f"{API}/api/short-video/{vid}", raw)
    L = probe_duration(raw) - 0.1
    vf = "scale=1080:1920,fps=30,setsar=1"
    vf = (f"setpts={target / L:.5f}*(PTS-STARTPTS)," if target > L else "setpts=PTS-STARTPTS,") + vf
    out = workdir / f"v{i}.mp4"
    ff("-ss", "0.06", "-i", raw, "-an", "-vf", vf, "-t", f"{target:.3f}", "-c:v", "libx264", "-crf", 18,
       "-preset", "fast", "-pix_fmt", "yuv420p", out)
    if target > L:
        log(f"  scene {i + 1}: stock clip {L:.1f}s < {target:.1f}s, slowed x{target / L:.2f}")
    return out


# ---------------------------------------------------------------- subtitles
def ts(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def build_ass(sents, starts, path):
    events = []
    for i, ss in enumerate(sents):
        for s in ss:
            lines = textwrap.wrap(s["text"].strip(), width=34)
            chunks = [lines[k:k + 2] for k in range(0, len(lines), 2)]
            wts = [sum(len(l) for l in c) for c in chunks]
            t = starts[i] + s["start"]
            for c, w in zip(chunks, wts):
                d = s["dur"] * w / sum(wts)
                words = [(li, wd) for li, l in enumerate(c) for wd in l.split()]
                tot = sum(len(wd) for _, wd in words)
                txt, prev = "", 0
                for li, wd in words:
                    if li != prev:
                        txt = txt.rstrip() + "\\N"
                        prev = li
                    txt += "{\\kf%d}%s " % (max(1, round(d * 100 * len(wd) / tot)), wd)
                events.append((t, t + d, txt.rstrip()))
                t += d
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # purple (sung) / white (not yet sung), black outline, top-anchored so the first line never moves
        "Style: Default,Arial,56,&H00FF4CB4,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,1,8,60,60,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for a, b, txt in events:
            f.write("Dialogue: 0,%s,%s,Default,,0,0,0,,{\\an8\\pos(540,%d)}%s\n" % (ts(a), ts(b), SUB_Y, txt))
    return events


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--list-voices", action="store_true", help="show the voice library (voices.json) and exit")
    ap.add_argument("--genre", default=None, help="tranh-luan (default), info or tam-su; picks the speaking pace and music")
    ap.add_argument("--audience", default=None,
                    help="tre or trung-nien (accents optional: trẻ, trung_niên); picks the voice age and music")
    ap.add_argument("--dry-run", action="store_true", help="print the settings that would be used and stop")
    ap.add_argument("--mode", "--modes", dest="modes", default="voice",
                    help="voice (default), music, or both; a comma list such as music,voice also works")
    ap.add_argument("--voice", default=None,
                    help="female (default) or male: combined with --audience into female-young, male-mature...; or any key of voices.json / edge-tts voice name")
    ap.add_argument("--reuse-footage", action="store_true", help="re-fit existing stock clips in work/<slug> instead of downloading new ones")
    ap.add_argument("--skip-render", action="store_true", help="reuse existing picture + voice in work/<slug>")
    a = ap.parse_args()

    if a.list_voices:
        for k, v in voices.load_voices().items():
            print(f"{k:18} {v['engine']:6} {v.get('label', '')}")
        return
    if not a.spec:
        ap.error("the spec file is required")
    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    slug = spec.get("slug") or spec_path.stem
    # genre + audience (command line wins over the spec file); explicit rate / music in the spec win over the profile
    prof = profiles.resolve(
        genre=a.genre or spec.get("genre"), audience=a.audience or spec.get("audience"), voice=a.voice,
        rate=int(str(spec["rate"]).rstrip("%")) if "rate" in spec else None,
        music=spec.get("music") or (DEFAULT_MUSIC if not (a.audience or spec.get("audience")) else None))
    cfg = voices.resolve(prof["voice"])
    spec["voice_cfg"], spec["voice"] = cfg, cfg["key"]
    spec["rate"], spec["music"] = f"{prof['rate']:+d}%", prof["music"]
    log(f"profile: genre={prof['genre']} audience={prof['audience']} voice={cfg['key']} rate={spec['rate']} "
        f"music={spec['music']} (expected {prof['seconds'][0]}-{prof['seconds'][1]} s, about {prof['words'][0]}-{prof['words'][1]} words)")
    if a.dry_run:
        return
    modes = ["music", "voice"] if a.modes.strip().lower() == "both" else [m.strip() for m in a.modes.split(",") if m.strip()]
    workdir = ROOT / "work" / slug
    outdir = ROOT / "videos" / slug
    workdir.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)
    n = len(spec["scenes"])

    if not (a.skip_render):
        ensure_server()
    music = ensure_music(spec["music"], workdir, need="music" in modes)

    if not a.skip_render:
        log(f"1/4 voice-over ({cfg['key']}: {cfg.get('label', cfg.get('voice', ''))}) for {n} scenes")
        sents = asyncio.run(_tts_all(spec, workdir))
        json.dump(sents, open(workdir / "sentences.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sents = json.load(open(workdir / "sentences.json", encoding="utf-8"))

    targets = [probe_duration(workdir / f"s{i}.mp3") for i in range(n)]
    targets[-1] += TAIL
    starts = [sum(targets[:i]) for i in range(n)]
    total = sum(targets)
    log(f"narration {total - TAIL:.1f}s, video {total:.1f}s")
    lo, hi = prof["seconds"]
    if not lo - 3 <= total - TAIL <= hi + 3:
        log(f"note: this genre aims for {lo}-{hi} s; consider {'trimming' if total - TAIL > hi else 'adding to'} the script")

    if not a.skip_render:
        log("2/4 stock footage per scene (about 1 minute per scene)")
        segs = [render_scene_picture(i, sc, targets[i], workdir, a.reuse_footage) for i, sc in enumerate(spec["scenes"])]
        (workdir / "list.txt").write_text("".join(f"file '{s.name}'\n" for s in segs), encoding="utf-8")
        ff("-f", "concat", "-safe", "0", "-i", workdir / "list.txt", "-c", "copy", workdir / "visual.mp4")
        # voice track, each scene padded to its picture length
        parts = []
        for i in range(n):
            ff("-i", workdir / f"s{i}.mp3", "-af", f"apad=whole_dur={targets[i]:.3f}", "-ar", 44100, "-ac", 2,
               workdir / f"p{i}.wav")
            parts.append(f"file 'p{i}.wav'\n")
        (workdir / "alist.txt").write_text("".join(parts), encoding="utf-8")
        ff("-f", "concat", "-safe", "0", "-i", workdir / "alist.txt", "-c", "copy", workdir / "voice.wav")

    log("3/4 karaoke subtitles")
    rel_ass = f"work/{slug}/subs.ass"
    events = build_ass(sents, starts, ROOT / rel_ass)
    log(f"  {len(events)} subtitle events")

    log("4/4 mixing and burning subtitles")
    fade = f"afade=t=out:st={total - 2:.2f}:d=2"
    outputs = []
    for mode in modes:
        if mode == "music":      # loud music, no voice
            fc = f"[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,{fade}[a]"
            amap = ["-map", "0:v", "-map", "[a]"]
            inputs = ["-i", workdir / "visual.mp4", "-stream_loop", "-1", "-i", music]
        elif mode == "voice":    # voice up front, quiet music
            fc = (f"[1:a]loudnorm=I=-16:TP=-1.5[v];[2:a]loudnorm=I=-14:TP=-1.5,volume=0.18,{fade}[m];"
                  f"[v][m]amix=inputs=2:duration=first:normalize=0[a]")
            amap = ["-map", "0:v", "-map", "[a]"]
            inputs = ["-i", workdir / "visual.mp4", "-i", workdir / "voice.wav", "-stream_loop", "-1", "-i", music]
        else:
            sys.exit(f"unknown mode: {mode}")
        out = outdir / (f"{slug}-voice{voices.file_suffix(cfg)}.mp4" if mode == "voice" else f"{slug}-{mode}.mp4")
        ff(*inputs, "-filter_complex", f"[0:v]{compat.ass_filter(rel_ass)}[vv];" + fc,
           "-map", "[vv]", "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", 23, "-preset", "fast",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out)
        outputs.append(out)

    for out in outputs:
        info = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "csv=p=0", str(out)], cwd=ROOT).decode().strip().strip(",")
        mb = out.stat().st_size / 1048576
        note = "" if info == "1080,1920" else "  !! not 1080x1920"
        log(f"done: {out.relative_to(ROOT)}  {info}  {probe_duration(out):.1f}s  {mb:.1f} MB{note}")
        if mb > 29:  # keep a smaller copy for chat/phone delivery (30 MB limit)
            small = out.with_name(out.stem + "-share.mp4")
            ff("-i", out, "-c:v", "libx264", "-b:v", "3M", "-maxrate", "3.5M", "-bufsize", "6M", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", small)
            log(f"      share copy: {small.relative_to(ROOT)}  {small.stat().st_size / 1048576:.1f} MB")
    for k, ev in enumerate((events[1], events[len(events) // 2], events[-2])):
        t = (ev[0] + ev[1]) / 2
        ff("-ss", f"{t:.1f}", "-i", outputs[0], "-frames:v", 1, "-vf", "scale=360:-1", workdir / f"preview{k}.png")
    if total - TAIL > 60:
        log("note: narration is over 60 s, long for Shorts feed; consider trimming scenes")


if __name__ == "__main__":
    main()
