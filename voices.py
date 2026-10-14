"""Voice library for short_video.py: edge-tts voices (online), Piper and VieNeu-TTS voices (offline), all driven the same way.

A voice is a key in voices.json. synth() takes the per-sentence delivery (rate %, pitch Hz, volume %) that
short_video.prosody() computes from the punctuation and applies it with the engine's own controls:
  edge    rate, pitch, volume are native edge-tts parameters
  piper   rate -> length_scale, pitch -> rubberband pitch shift (ratio = (f0 + Hz) / f0), volume -> gain
  vieneu  rate -> atempo, pitch -> rubberband pitch shift, volume -> gain; a preset voice or a cloned ref_audio.
          It has no word boundaries, so Whisper finds each word's spoken time for the karaoke captions.

  python voices.py --vieneu-list      # every VieNeu preset voice name (use in voices.json or --voice "vieneu:Name")
"""
import asyncio, difflib, json, re, subprocess, threading, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALIGN_DIR = ROOT / "models" / "faster-whisper-base"   # small and fast; the script text is known, so base times words well
_piper_cache = {}
_vieneu = {}
_whisper = {}
_lock = threading.Lock()                # VieNeu and Whisper models are loaded once and used by one thread at a time


def load_voices():
    return json.loads((ROOT / "voices.json").read_text(encoding="utf-8"))["voices"]


def resolve(key):
    """Config for a voice key; anything unknown is treated as a raw edge-tts voice name (e.g. en-US-AvaNeural)."""
    voices = load_voices()
    k = key.strip().lower()
    if k in voices:
        cfg = dict(voices[k])
        cfg["key"] = k
        return cfg
    if k.startswith("vieneu:"):                     # any VieNeu preset by name, e.g. "vieneu:Ngọc Linh"
        name = key.strip()[7:].strip()
        import unicodedata                          # key goes into file names: "Thục Đoan" -> vieneu-thucdoan
        ascii_ = unicodedata.normalize("NFD", name.replace("Đ", "D").replace("đ", "d")).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]", "", ascii_.lower())
        return {"key": "vieneu-" + slug, "engine": "vieneu", "voice": name, "f0": 180, "label": "VieNeu: " + name}
    return {"key": key.strip(), "engine": "edge", "voice": key.strip(), "label": key.strip()}


def apply_preset(cfg, rate, pitch, vol):
    """Add the voice's own offsets (young / mature presets) to the sentence delivery."""
    return rate + int(cfg.get("rate", 0)), pitch + int(cfg.get("pitch", 0)), vol + int(cfg.get("volume", 0))


def file_suffix(cfg):
    k = cfg["key"]
    return "" if k == "female" else "-male" if k == "male" else "-" + k.replace(" ", "-")


async def _edge(cfg, text, rate, pitch, vol, out):
    import edge_tts
    comm = edge_tts.Communicate(text, cfg["voice"], rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz", volume=f"{vol:+d}%",
                                boundary="WordBoundary")
    n, words = 0, []
    with open(out, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
                n += len(ch["data"])
            elif ch["type"] == "WordBoundary":      # exact spoken time of every word, used for karaoke timing
                words.append({"w": ch["text"], "s": ch["offset"] / 1e7, "e": (ch["offset"] + ch["duration"]) / 1e7})
    Path(out).with_suffix(".words.json").write_text(json.dumps(words), encoding="utf-8")
    if not n:
        raise RuntimeError("no audio")


def _piper_voice(cfg):
    from piper import PiperVoice
    path = str(ROOT / cfg["model"])
    if path not in _piper_cache:
        _piper_cache[path] = PiperVoice.load(path)
    return _piper_cache[path]


def _piper_sync(cfg, text, rate, pitch, vol, out):
    from piper import SynthesisConfig
    voice = _piper_voice(cfg)
    length_scale = float(cfg.get("length_scale", 1.0)) / max(0.5, 1 + rate / 100)
    raw = Path(out).with_suffix(".piper.wav")
    with wave.open(str(raw), "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=SynthesisConfig(speaker_id=cfg.get("speaker"), length_scale=length_scale))
    f0 = float(cfg.get("f0", 200))
    ratio = max(0.6, min(1.6, (f0 + pitch) / f0))
    af = []
    if abs(ratio - 1) > 0.004:
        af.append(f"rubberband=pitch={ratio:.4f}")
    af.append(f"volume={max(0.1, 1 + vol / 100):.3f}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", ",".join(af), "-c:a", "libmp3lame",
                    "-q:a", "2", str(out)], check=True)
    raw.unlink()


def _vieneu_model(mode="v3turbo"):
    if mode not in _vieneu:
        from vieneu import Vieneu
        _vieneu[mode] = Vieneu(mode=mode)           # first use downloads the model from Hugging Face (about 1 minute)
    return _vieneu[mode]


def _vieneu_sync(cfg, text, rate, pitch, vol, out):
    with _lock:
        tts = _vieneu_model(cfg.get("mode", "v3turbo"))
        if cfg.get("ref_audio"):
            ref = ROOT / cfg["ref_audio"]
            if not ref.exists():
                raise FileNotFoundError(f"voice sample for cloning not found: {ref}")
            audio = tts.infer(text, ref_audio=str(ref))
        else:
            audio = tts.infer(text, voice=cfg["voice"])
        raw = Path(out).with_suffix(".vieneu.wav")
        tts.save(audio, str(raw))
    f0 = float(cfg.get("f0", 180))
    ratio = max(0.6, min(1.6, (f0 + pitch) / f0))
    tempo = max(0.5, min(2.0, 1 + rate / 100))
    af = []
    if abs(ratio - 1) > 0.004:
        af.append(f"rubberband=pitch={ratio:.4f}")
    if abs(tempo - 1) > 0.004:
        af.append(f"atempo={tempo:.4f}")
    af.append(f"volume={max(0.1, 1 + vol / 100):.3f}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", ",".join(af), "-c:a", "libmp3lame",
                    "-q:a", "2", str(out)], check=True)
    raw.unlink()
    if cfg.get("align", True):
        words = _align_words(out, text, cfg.get("lang", "vi"))
        if words:
            Path(out).with_suffix(".words.json").write_text(json.dumps(words), encoding="utf-8")


def _norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def _align_words(audio, text, lang):
    """One {w, s, e} per whitespace token of `text`, timed by Whisper (same format edge-tts boundaries give).

    Whisper's words are matched to the script's words; script words Whisper heard differently get times
    spread by length between their matched neighbours. Returns [] if Whisper is unavailable or heard nothing."""
    try:
        with _lock:
            if "m" not in _whisper:
                import os
                from faster_whisper import WhisperModel
                _whisper["m"] = WhisperModel(str(ALIGN_DIR) if ALIGN_DIR.exists() else "base",
                                             download_root=str(ROOT / "models" / "hf-cache"), device="cpu",
                                             compute_type="int8", cpu_threads=max(4, (os.cpu_count() or 8) // 2))
            segs, _ = _whisper["m"].transcribe(str(audio), language=lang, beam_size=1, word_timestamps=True,
                                               condition_on_previous_text=False, initial_prompt=text)
            heard = [w for s in segs for w in (s.words or []) if _norm(w.word)]
    except Exception:
        return []
    toks = text.split()
    if not heard or not toks:
        return []
    times = [None] * len(toks)
    sm = difflib.SequenceMatcher(None, [_norm(t) for t in toks], [_norm(w.word) for w in heard], autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            times[a + k] = (heard[b + k].start, heard[b + k].end)
    if not any(times):
        return []
    end_all = heard[-1].end
    k = 0
    while k < len(toks):                            # fill each run of unmatched tokens between the matched ones
        if times[k]:
            k += 1
            continue
        j = k
        while j < len(toks) and not times[j]:
            j += 1
        s0 = times[k - 1][1] if k else max(0.0, heard[0].start - 0.05 * (j - k))
        e0 = times[j][0] if j < len(toks) else end_all
        e0 = max(e0, s0 + 0.08 * (j - k))
        total = sum(len(t) for t in toks[k:j]) or 1
        t = s0
        for m in range(k, j):
            d = (e0 - s0) * len(toks[m]) / total
            times[m] = (t, t + d)
            t += d
        k = j
    return [{"w": tok, "s": round(s, 3), "e": round(e, 3)} for tok, (s, e) in zip(toks, times)]


async def synth(cfg, text, rate, pitch, vol, out):
    if cfg["engine"] == "edge":
        return await _edge(cfg, text, rate, pitch, vol, out)
    if cfg["engine"] == "piper":
        return await asyncio.to_thread(_piper_sync, cfg, text, rate, pitch, vol, out)
    if cfg["engine"] == "vieneu":
        return await asyncio.to_thread(_vieneu_sync, cfg, text, rate, pitch, vol, out)
    raise ValueError(f"unknown engine {cfg['engine']}")


if __name__ == "__main__":
    import sys
    import compat  # noqa: F401  (UTF-8 console on Windows)
    if "--vieneu-list" in sys.argv:
        for label, name in _vieneu_model().list_preset_voices():
            print(f"{name:16s} {label}")
    else:
        print(__doc__)
