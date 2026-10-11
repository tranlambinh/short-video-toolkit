#!/usr/bin/env python
"""Automatic subtitles for any video: Whisper medium -> editable transcript -> purple karaoke captions.

  python auto_subtitle.py video.mp4                       # transcribe (language auto-detected) and burn captions
  python auto_subtitle.py video.mp4 --lang vi             # force Vietnamese (use en for English)
  python auto_subtitle.py video.mp4 --transcribe-only     # stop after writing the transcript so it can be reviewed
  python auto_subtitle.py video.mp4 --transcript work/auto-sub/video/transcript.json
                                                          # burn captions from a transcript you edited or translated

Files (work/auto-sub/<name>/): transcript.json (editable), transcript.txt (readable), subs.ass, subs.srt.
Result: videos/auto-sub/<name>-sub.mp4. The original video is never changed.
To translate (for example English speech into Vietnamese captions): transcribe, translate the "text" of each
segment in transcript.json, then run again with --transcript. Word timing is re-spread across each segment.
"""
import argparse, json, os, subprocess, sys, time
import compat
from pathlib import Path

import karaoke

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models" / "faster-whisper-medium"


def log(msg):
    print(f"[subtitle] {msg}", flush=True)


def ffprobe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    j = json.loads(out)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return int(v["width"]), int(v["height"]), float(j["format"]["duration"])


def transcribe(video, lang, work):
    from faster_whisper import WhisperModel
    wav = work / "audio.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    log("loading Whisper medium (CPU, int8) ...")
    model = WhisperModel(str(MODEL_DIR) if MODEL_DIR.exists() else "medium", download_root=str(ROOT / "models" / "hf-cache"), device="cpu", compute_type="int8", cpu_threads=max(4, (os.cpu_count() or 8) // 2))
    t0 = time.time()
    gen, info = model.transcribe(str(wav), language=None if lang == "auto" else lang, beam_size=5, vad_filter=True,
                                 word_timestamps=True, condition_on_previous_text=False)
    log(f"language: {info.language} (confidence {info.language_probability:.2f}), audio {info.duration:.1f}s")
    segments = []
    for seg in gen:
        if seg.no_speech_prob > 0.7 and seg.avg_logprob < -1.0:
            continue                                  # almost certainly music or noise, not speech
        words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for w in (seg.words or []) if w.word.strip()]
        text = " ".join(w["w"] for w in words) if words else seg.text.strip()
        if not text:
            continue
        segments.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": text, "words": words})
        log(f"  {seg.start:6.1f}s  {text[:70]}")
    log(f"transcribed in {time.time() - t0:.0f}s")
    return info.language, segments


def write_outputs(language, segments, W, H, work, y_frac):
    (work / "transcript.json").write_text(json.dumps({"language": language, "segments": segments},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    (work / "transcript.txt").write_text("\n".join(f"[{s['start']:6.1f}s] {s['text']}" for s in segments), encoding="utf-8")
    (work / "subs.ass").write_text(karaoke.build_ass(segments, W, H, y_frac), encoding="utf-8")
    (work / "subs.srt").write_text(karaoke.build_srt(segments, W, H), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Automatic karaoke subtitles for a video.")
    ap.add_argument("video")
    ap.add_argument("--lang", default="auto", help="vi, en, or auto (default)")
    ap.add_argument("--transcribe-only", action="store_true")
    ap.add_argument("--transcript", help="use this (edited/translated) transcript.json instead of running Whisper")
    ap.add_argument("--out", help="output video (default videos/auto-sub/<name>-sub.mp4)")
    ap.add_argument("--pos-y", type=float, default=None,
                    help="top of the first caption line as a fraction of the height "
                         "(default 0.647 for vertical video = 676 px above the bottom of 1080x1920)")
    a = ap.parse_args()

    video = Path(a.video)
    if not video.exists():
        sys.exit(f"video not found: {video}")
    name = video.stem
    work = ROOT / "work" / "auto-sub" / name
    work.mkdir(parents=True, exist_ok=True)
    W, H, dur = ffprobe(video)

    if a.transcript:
        data = json.loads(Path(a.transcript).read_text(encoding="utf-8"))
        language, segments = data.get("language", "?"), data["segments"]
        log(f"using transcript {a.transcript} ({len(segments)} segments)")
    else:
        language, segments = transcribe(video, a.lang, work)
        if not segments:
            sys.exit("no speech found in this video")
    write_outputs(language, segments, W, H, work, a.pos_y)
    log(f"transcript: {work / 'transcript.json'}")
    if a.transcribe_only:
        log("stopped after transcript (--transcribe-only). Review or translate it, then run again with --transcript.")
        return

    out = Path(a.out) if a.out else ROOT / "videos" / "auto-sub" / f"{name}-sub.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    rel_ass = (work / "subs.ass").relative_to(ROOT).as_posix()
    log(f"burning captions into {W}x{H} video ...")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"{compat.ass_filter(rel_ass)}",
                    "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", str(out)], cwd=ROOT, check=True)
    log(f"done: {out}  {out.stat().st_size / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
