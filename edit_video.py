#!/usr/bin/env python
"""Edit existing videos with ffmpeg: trim, join (with crossfade), speed, fades, slow zoom, logo.

Usage examples
  python edit_video.py in.mp4 -o out.mp4 --trim 5-40
  python edit_video.py a.mp4 b.mp4 c.mp4 -o joined.mp4 --transition 0.6
  python edit_video.py in.mp4 -o out.mp4 --logo logo.png --logo-pos tl --logo-size 14
  python edit_video.py in.mp4 -o out.mp4 --fade-in 0.5 --fade-out 0.8 --zoom 1.12 --speed 1.1

--trim START-END     once per input, in order ("-" keeps that input whole). Times: 12.5, 1:05, 0:01:05.5
--size WxH           output size, default = size of the first input (use 1080x1920 for TikTok/Reels/Shorts)
--fit cover|contain  how inputs of another shape fill the frame: cover crops, contain adds black bars
--transition SEC     crossfade between joined inputs (0 = hard cut)
--fade-in/--fade-out SEC   video and audio fade at the start / end of the final video
--zoom Z             slow push-in from 1.0x to Zx over the whole video (for example 1.12)
--speed X            playback speed of the final video (0.5 to 4)
--logo FILE          PNG (transparent background is best) overlay; --logo-pos tl|tr|bl|br|c,
                     --logo-size PERCENT of video width, --logo-opacity 0-1, --logo-margin PX,
                     --logo-from / --logo-to seconds to show it only for part of the video
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

FPS = 30


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def ff(*args):
    run(["ffmpeg", "-v", "error", "-y", *args])


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    j = json.loads(out)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return {"w": int(v["width"]), "h": int(v["height"]), "dur": float(j["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def parse_time(s):
    parts = [float(p) for p in s.strip().split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


def parse_trim(spec, dur):
    if spec in (None, "", "-"):
        return 0.0, dur
    a, _, b = spec.partition("-")
    start = parse_time(a) if a.strip() else 0.0
    end = parse_time(b) if b.strip() else dur
    if end <= start or start >= dur:
        sys.exit(f"bad --trim '{spec}' for a {dur:.1f}s video")
    return start, min(end, dur)


def normalize(src, dst, start, end, W, H, fit):
    """Trim, fit to WxH, constant fps, yuv420p, stereo 44.1 kHz audio (silent if the input has none)."""
    info = probe(src)
    dur = end - start
    if fit == "cover":
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black"
    vf += f",setsar=1,fps={FPS},format=yuv420p"
    cmd = ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src]
    if info["audio"]:
        cmd += ["-map", "0:v", "-map", "0:a", "-af", "aresample=44100,aformat=channel_layouts=stereo"]
    else:
        cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a"]
    cmd += ["-vf", vf, "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", 16, "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k", dst]
    ff(*cmd)


def join_hard(parts, dst, tmp):
    lst = tmp / "concat.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", dst)


def join_xfade(parts, dst, t, tmp):
    acc = parts[0]
    for k, nxt in enumerate(parts[1:], start=1):
        d = probe(acc)["dur"]
        out = tmp / f"xf{k}.mp4"
        tt = min(t, d - 0.1, probe(nxt)["dur"] - 0.1)
        ff("-i", acc, "-i", nxt, "-filter_complex",
           f"[0:v][1:v]xfade=transition=fade:duration={tt:.3f}:offset={d - tt:.3f}[v];"
           f"[0:a][1:a]acrossfade=d={tt:.3f}[a]",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", 16, "-preset", "fast", "-c:a", "aac", "-b:a", "192k", out)
        acc = out
    acc.replace(dst)


def run_job(a, inputs, output):
    for p in inputs + ([a.logo] if a.logo else []):
        if not Path(p).exists():
            sys.exit(f"file not found: {p}")
    if not 0.5 <= a.speed <= 4:
        sys.exit("--speed must be between 0.5 and 4")
    first = probe(inputs[0])
    if a.size:
        W, H = (int(x) for x in a.size.lower().split("x"))
    else:
        W, H = first["w"] - first["w"] % 2, first["h"] - first["h"] % 2

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="edit_video_") as td:
        tmp = Path(td)
        parts = []
        for i, src in enumerate(inputs):
            info = probe(src)
            trim = a.trim[i] if i < len(a.trim) else None
            s, e = parse_trim(trim, info["dur"])
            dst = tmp / f"n{i}.mp4"
            print(f"[edit] input {i + 1}/{len(inputs)}: {Path(src).name}  {s:.1f}s-{e:.1f}s", flush=True)
            normalize(src, dst, s, e, W, H, a.fit)
            parts.append(dst)
        if len(parts) == 1:
            base = parts[0]
        else:
            base = tmp / "joined.mp4"
            print(f"[edit] joining {len(parts)} clips" + (f" with {a.transition}s crossfade" if a.transition > 0 else ""), flush=True)
            if a.transition > 0:
                join_xfade(parts, base, a.transition, tmp)
            else:
                join_hard(parts, base, tmp)

        dur = probe(base)["dur"]
        final_dur = dur / a.speed
        vchain, achain = [], []
        if a.zoom > 1.0:   # supersample first so the slow zoom does not jitter
            frames = max(1, int(final_dur * FPS))
            vchain.append(f"scale={W * 2}:{H * 2},zoompan=z='min(1+({a.zoom}-1)*on/{frames},{a.zoom})'"
                          f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
        if a.speed != 1.0:
            vchain.append(f"setpts=PTS/{a.speed}")
            achain.append(f"atempo={a.speed}")
        if a.fade_in > 0:
            vchain.append(f"fade=t=in:st=0:d={a.fade_in}")
            achain.append(f"afade=t=in:st=0:d={a.fade_in}")
        if a.fade_out > 0:
            st = max(0.0, final_dur - a.fade_out)
            vchain.append(f"fade=t=out:st={st:.3f}:d={a.fade_out}")
            achain.append(f"afade=t=out:st={st:.3f}:d={a.fade_out}")

        inputs = ["-i", base]
        fc = "[0:v]" + (",".join(vchain) if vchain else "null") + "[v0]"
        last = "v0"
        if a.logo:
            m = a.logo_margin
            pos = {"tl": f"{m}:{m}", "tr": f"W-w-{m}:{m}", "bl": f"{m}:H-h-{m}",
                   "br": f"W-w-{m}:H-h-{m}", "c": "(W-w)/2:(H-h)/2"}[a.logo_pos]
            enable = ""
            if a.logo_from is not None or a.logo_to is not None:
                enable = f":enable='between(t,{a.logo_from or 0},{a.logo_to or final_dur})'"
            inputs += ["-i", a.logo]
            fc += (f";[1:v]scale={int(W * a.logo_size / 100)}:-1,format=rgba,"
                   f"colorchannelmixer=aa={a.logo_opacity}[lg];[v0][lg]overlay={pos}{enable}[v1]")
            last = "v1"
        fc += ";[0:a]" + (",".join(achain) if achain else "anull") + "[a]"
        print(f"[edit] rendering final {final_dur:.1f}s {W}x{H}", flush=True)
        ff(*inputs, "-filter_complex", fc, "-map", f"[{last}]", "-map", "[a]", "-c:v", "libx264", "-crf", a.crf,
           "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out)

    r = probe(out)
    print(f"[edit] done: {out}  {r['w']}x{r['h']}  {r['dur']:.1f}s  {out.stat().st_size / 1048576:.1f} MB")


def main():
    ap = argparse.ArgumentParser(description="Edit existing videos with ffmpeg.")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--output", required=True, help="output file (output folder with --batch)")
    ap.add_argument("--batch", action="store_true",
                    help="treat every input (file, folder or wildcard like videos/*.mp4) as its own video and write each to the output folder")
    ap.add_argument("--suffix", default="edit", help="word added to each file name in --batch mode, e.g. logo gives clip-logo.mp4 (default edit)")
    ap.add_argument("--trim", action="append", default=[])
    ap.add_argument("--size", default=None)
    ap.add_argument("--fit", choices=["cover", "contain"], default="cover")
    ap.add_argument("--transition", type=float, default=0.0)
    ap.add_argument("--fade-in", type=float, default=0.0)
    ap.add_argument("--fade-out", type=float, default=0.0)
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--logo")
    ap.add_argument("--logo-pos", choices=["tl", "tr", "bl", "br", "c"], default="tr")
    ap.add_argument("--logo-size", type=float, default=14.0, help="percent of video width")
    ap.add_argument("--logo-opacity", type=float, default=1.0)
    ap.add_argument("--logo-margin", type=int, default=40)
    ap.add_argument("--logo-from", type=float, default=None)
    ap.add_argument("--logo-to", type=float, default=None)
    ap.add_argument("--crf", type=int, default=20)
    a = ap.parse_args()

    if not a.batch:
        run_job(a, a.inputs, a.output)
        return
    # batch: expand folders and wildcards, then edit every video on its own with the same settings
    import glob
    exts = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi"}
    files = []
    for item in a.inputs:
        if Path(item).is_dir():
            files += sorted(str(f) for f in Path(item).iterdir() if f.suffix.lower() in exts)
        elif any(ch in item for ch in "*?["):
            files += sorted(glob.glob(item))
        else:
            files.append(item)
    files = [f for i, f in enumerate(files) if f not in files[:i]]
    if not files:
        sys.exit("no videos found for --batch")
    outdir = Path(a.output)
    outdir.mkdir(parents=True, exist_ok=True)
    ok, failed = [], []
    for n, f in enumerate(files, start=1):
        dst = outdir / f"{Path(f).stem}-{a.suffix.lstrip('-')}.mp4"
        print(f"[edit] ===== {n}/{len(files)}: {f}", flush=True)
        try:
            run_job(a, [f], str(dst))
            ok.append(dst)
        except (SystemExit, subprocess.CalledProcessError) as e:
            failed.append((f, str(e)))
            print(f"[edit] FAILED: {f}: {e}", flush=True)
    print(f"[edit] batch done: {len(ok)} ok, {len(failed)} failed -> {outdir}")
    for f, e in failed:
        print(f"[edit]   failed: {f} ({e})")


if __name__ == "__main__":
    main()
