#!/usr/bin/env python
"""Cut vertical shorts out of a long landscape video, one per key message.

  1. python clip_video.py prepare <file | YouTube link | Google Drive link> [--lang vi|en|auto] [--name NAME]
        downloads if needed, transcribes with Whisper medium, writes work/clips/<name>/
          transcript.json        words with timing (cached; use --force to redo)
          transcript_for_llm.txt numbered segments "[12] 03:41-03:52 text", what Claude reads to find key messages
          frames.png             8 frames across the video, to judge the layout
  2. Claude proposes key messages and writes work/clips/<name>/plan.json (see below); you pick which to make.
  3. python clip_video.py render <name> [--clips 1,3,5] [--title-seconds 4] [--layout blur|crop]
        videos/clips/<name>/clip-01-<title>.mp4 + index.md

plan.json
  {"clips": [{"id": 1, "title": "Short title shown at the top", "start_seg": 12, "end_seg": 19,
              "layout": "crop" | "blur", "hook": "...", "why": "...", "caption": "text to post",
              "translations": {"12": "Vietnamese text for segment 12", "13": "..."}}]}
start_seg / end_seg are segment numbers from transcript_for_llm.txt; cut times snap to the first and last word.
translations (optional) replace the caption text of those segments (for English video with Vietnamese captions).

Layouts (landscape source -> 1080x1920)
  blur  the whole frame in the middle over a blurred copy of itself; title above, captions below. Safe for slides,
        screen shares, several people.
  crop  9:16 window that follows the speaker's face (OpenCV), then scaled up. Looks native for a talking head, softer
        picture when the source is 1080p.
Titles: white text in a purple box, shown for the first --title-seconds (0 = whole clip). Captions: purple karaoke.
"""
import argparse, copy, json, re, shutil, subprocess, sys
import compat
from pathlib import Path

import numpy as np

import auto_subtitle as asub
import karaoke
import profiles

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "work" / "clips"
OUT = ROOT / "videos" / "clips"
OW, OH = 1080, 1920


def log(msg):
    print(f"[clip-video] {msg}", flush=True)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", profiles.norm(text)).strip("-")[:48] or "video"


def mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def is_url(s):
    return s.startswith(("http://", "https://"))


# ---------------------------------------------------------------- source
def fetch(source, d):
    """Local file as is; YouTube or Google Drive link downloaded into work/clips/<name>/source.mp4."""
    if not is_url(source):
        p = Path(source)
        if not p.exists():
            sys.exit(f"file not found: {source}")
        return p
    d.mkdir(parents=True, exist_ok=True)
    dest = d / "source.mp4"
    if dest.exists():
        log(f"using the video already downloaded: {dest}")
        return dest
    if "drive.google.com" in source or "docs.google.com" in source:
        import gdown
        log("downloading from Google Drive (the file must be shared as 'Anyone with the link') ...")
        got = gdown.download(url=source, output=str(dest), quiet=False, fuzzy=True)
        if not got or not dest.exists():
            sys.exit("Google Drive download failed. Share the file as 'Anyone with the link' or upload it here instead.")
        return dest
    log("downloading with yt-dlp ...")
    subprocess.run([sys.executable, "-m", "yt_dlp", "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
                    "--merge-output-format", "mp4", "-o", str(d / "source.%(ext)s"), source], check=True)
    found = sorted(d.glob("source.*"))
    if not found:
        sys.exit("download failed")
    return found[0]


def default_name(source):
    if not is_url(source):
        return slugify(Path(source).stem)
    try:
        t = subprocess.check_output([sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download", "--no-warnings",
                                     "--print", "%(title)s", source], text=True, encoding="utf-8").strip().splitlines()[0]
        return slugify(t)
    except Exception:
        return "video"


# ---------------------------------------------------------------- prepare
def cmd_prepare(a):
    name = a.name or default_name(a.source)
    d = BASE / name
    d.mkdir(parents=True, exist_ok=True)
    src = fetch(a.source, d)
    W, H, dur = asub.ffprobe(src)
    tr = d / "transcript.json"
    if tr.exists() and not a.force:
        data = json.loads(tr.read_text(encoding="utf-8"))
        log(f"using the cached transcript ({len(data['segments'])} segments); --force to transcribe again")
    else:
        if W < H:
            log("note: this video is already vertical, so no reframing is needed")
        language, segments = asub.transcribe(src, a.lang, d)
        data = {"language": language, "duration": dur, "width": W, "height": H, "source": str(src), "segments": segments}
        tr.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"[{i}] {mmss(s['start'])}-{mmss(s['end'])} {s['text']}" for i, s in enumerate(data["segments"])]
    (d / "transcript_for_llm.txt").write_text(
        f"# {name}  language={data['language']}  duration={mmss(data['duration'])}  {data['width']}x{data['height']}\n"
        + "\n".join(lines) + "\n", encoding="utf-8")
    # contact sheet to judge layout (talking head -> crop, slides or several people -> blur)
    files = []
    for k in range(8):
        f = d / f"fr{k}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{data['duration'] * (k + 0.5) / 8:.2f}", "-i", str(src),
                        "-frames:v", "1", "-vf", "scale=480:-2", str(f)], check=True)
        files.append(f)
    inp = sum([["-i", str(f)] for f in files], [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex",
                    "[0:v][1:v][2:v][3:v]hstack=inputs=4[a];[4:v][5:v][6:v][7:v]hstack=inputs=4[b];[a][b]vstack",
                    "-frames:v", "1", str(d / "frames.png")], check=True)
    for f in files:
        f.unlink()
    log(f"ready: {d}")
    log(f"  video {W}x{H}, {mmss(data['duration'])}, language {data['language']}, {len(data['segments'])} segments")
    log(f"  next: read {d / 'transcript_for_llm.txt'} and write {d / 'plan.json'}")


# ---------------------------------------------------------------- reframing
def face_track(src, t0, t1, W, H, cw):
    """Horizontal crop positions (left edge) every second, following the largest face, smoothed."""
    import cv2
    cap = cv2.VideoCapture(str(src))
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    ts, xs = [], []
    t = t0
    while t <= t1:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if ok:
            sc = 640 / fr.shape[1]
            g = cv2.cvtColor(cv2.resize(fr, None, fx=sc, fy=sc), cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(g, 1.1, 5, minSize=(36, 36))
            if len(faces):
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                ts.append(t - t0)
                xs.append((x + w / 2) / sc)
        t += 0.5
    cap.release()
    dur = t1 - t0
    keys_t = np.arange(0, dur + 1.0, 1.0)
    if len(xs) < 3:
        centers = np.full(len(keys_t), W / 2)
        found = 0
    else:
        grid = np.arange(0, dur + 0.01, 0.5)
        series = np.interp(grid, ts, xs)
        k = 5
        series = np.convolve(np.pad(series, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
        centers = np.interp(keys_t, grid, series)
        found = len(xs)
    lefts = np.clip(centers - cw / 2, 0, W - cw)
    return list(zip(keys_t.tolist(), lefts.tolist())), found


def pan_expr(keys):
    expr = f"{keys[-1][1]:.1f}"
    for (ta, xa), (tb, xb) in reversed(list(zip(keys, keys[1:]))):
        expr = f"if(lt(t,{tb:.2f}),{xa:.1f}+({xb - xa:.1f})*(t-{ta:.2f})/{tb - ta:.2f},{expr})"
    return expr


# ---------------------------------------------------------------- render
def clip_times(segs, clip, dur):
    if "start" in clip and "end" in clip:
        return float(clip["start"]), min(float(clip["end"]), dur)
    first, last = segs[clip["start_seg"]], segs[clip["end_seg"]]
    s0 = first["words"][0]["s"] if first.get("words") else first["start"]
    e1 = last["words"][-1]["e"] if last.get("words") else last["end"]
    return max(0.0, s0 - 0.25), min(dur, e1 + 0.45)


def make_clip(a, data, clip, out_dir, work):
    segs = data["segments"]
    W, H, dur = data["width"], data["height"], data["duration"]
    src = Path(data["source"])
    t0, t1 = clip_times(segs, clip, dur)
    length = t1 - t0
    layout = a.layout or clip.get("layout") or "blur"
    if H >= W:
        layout = "native"
    # captions: segments inside the cut, shifted to the clip's own clock; translated text replaces the original
    tr = clip.get("translations", {})
    sub = []
    if "start_seg" in clip:
        idxs = range(clip["start_seg"], clip["end_seg"] + 1)
    else:                                              # explicit start/end seconds: every segment that falls inside
        idxs = [i for i, s in enumerate(segs) if s["start"] >= t0 - 0.5 and s["end"] <= t1 + 0.5]
    for i in idxs:
        seg = copy.deepcopy(segs[i])
        if str(i) in tr:
            seg["text"], seg["words"] = tr[str(i)], []
        sh = lambda v: max(0.0, v - t0)
        seg["start"], seg["end"] = sh(seg["start"]), min(length, sh(seg["end"]))
        for w in seg.get("words", []):
            w["s"], w["e"] = sh(w["s"]), min(length, sh(w["e"]))
        sub.append(seg)
    if layout == "blur":
        cap_y, title_y = 1314, 400
    else:
        cap_y, title_y = round(OH * karaoke.Y_FRAC_PORTRAIT), 230
    title = None
    if clip.get("title"):
        te = length if a.title_seconds <= 0 else min(length, a.title_seconds)
        title = {"text": clip["title"], "start": 0.0, "end": te, "y": title_y}
    ass = karaoke.build_ass(sub, OW, OH, y_px=cap_y, title=title)
    ass_path = work / f"clip-{clip['id']:02d}.ass"
    ass_path.write_text(ass, encoding="utf-8")
    rel = ass_path.relative_to(ROOT).as_posix()
    asfilter = f"{compat.ass_filter(rel)}"

    if layout == "native":
        vf = (f"[0:v]scale={OW}:{OH}:force_original_aspect_ratio=increase,crop={OW}:{OH},setsar=1,{asfilter},format=yuv420p[v]")
        note = "already vertical"
    elif layout == "crop":
        ch = H - H % 2
        cw = int(ch * 9 / 16) // 2 * 2
        keys, found = face_track(src, t0, t1, W, H, cw)
        note = f"crop, face found in {found} samples" + ("" if found else " (none, centered)")
        vf = (f"[0:v]crop={cw}:{ch}:x='{pan_expr(keys)}':y=0,scale={OW}:{OH}:flags=lanczos,setsar=1,{asfilter},format=yuv420p[v]")
    else:
        note = "blur"
        vf = (f"[0:v]split[a][b];[a]scale={OW}:{OH}:force_original_aspect_ratio=increase,crop={OW}:{OH},boxblur=40:6,"
              f"eq=brightness=-0.08[bg];[b]scale={OW}:-2:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,"
              f"{asfilter},format=yuv420p[v]")
    af = f"[0:a]afade=t=in:st=0:d=0.1,afade=t=out:st={max(0, length - 0.3):.2f}:d=0.3,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    name = f"clip-{clip['id']:02d}-{slugify(clip.get('title', 'clip'))}.mp4"
    out = out_dir / name
    if a.dry_run:
        log(f"clip {clip['id']}: {mmss(t0)}-{mmss(t1)} ({length:.0f}s) [{note}] {clip.get('title', '')}")
        return None
    log(f"clip {clip['id']}: {mmss(t0)}-{mmss(t1)} ({length:.0f}s) [{note}] {clip.get('title', '')}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{length:.3f}", "-i", str(src),
                    "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "20",
                    "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
                   cwd=ROOT, check=True)
    log(f"  -> {out.relative_to(ROOT)}  {out.stat().st_size / 1048576:.1f} MB")
    return {"id": clip["id"], "file": out.name, "start": t0, "end": t1, "length": length, "title": clip.get("title", ""),
            "caption": clip.get("caption", ""), "hook": clip.get("hook", ""), "layout": layout}


def cmd_render(a):
    work = BASE / a.name
    data = json.loads((work / "transcript.json").read_text(encoding="utf-8"))
    plan_path = Path(a.plan) if a.plan else work / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    want = None if a.clips in (None, "all") else {int(x) for x in a.clips.split(",")}
    out_dir = OUT / a.name
    out_dir.mkdir(parents=True, exist_ok=True)
    done = []
    for clip in plan["clips"]:
        if want is not None and clip["id"] not in want:
            continue
        r = make_clip(a, data, clip, out_dir, work)
        if r:
            done.append(r)
    if done:
        rows = ["# Short video cắt từ: " + a.name, ""]
        for r in done:
            rows += [f"## Clip {r['id']}: {r['title']}", f"- File: `{r['file']}` ({r['length']:.0f} s, {mmss(r['start'])}-{mmss(r['end'])} trong video gốc, khung {r['layout']})"]
            if r["hook"]:
                rows.append(f"- Câu mở đầu: {r['hook']}")
            if r["caption"]:
                rows += ["- Gợi ý chú thích đăng:", "", f"> {r['caption']}"]
            rows.append("")
        (out_dir / "index.md").write_text("\n".join(rows), encoding="utf-8")
        log(f"done: {len(done)} clips in {out_dir.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description="Cut vertical shorts out of a long landscape video.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("source")
    p.add_argument("--lang", default="auto")
    p.add_argument("--name")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_prepare)
    r = sub.add_parser("render")
    r.add_argument("name")
    r.add_argument("--plan")
    r.add_argument("--clips", help="ids to make, for example 1,3,5 (default all)")
    r.add_argument("--layout", choices=["blur", "crop"], help="force one layout for every clip")
    r.add_argument("--title-seconds", type=float, default=4.0, help="how long the title stays (0 = whole clip)")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(fn=cmd_render)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
