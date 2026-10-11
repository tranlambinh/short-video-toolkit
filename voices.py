"""Voice library for short_video.py: edge-tts voices (online) and Piper voices (offline), all driven the same way.

A voice is a key in voices.json. synth() takes the per-sentence delivery (rate %, pitch Hz, volume %) that
short_video.prosody() computes from the punctuation and applies it with the engine's own controls:
  edge   rate, pitch, volume are native edge-tts parameters
  piper  rate -> length_scale, pitch -> rubberband pitch shift (ratio = (f0 + Hz) / f0), volume -> gain
"""
import asyncio, json, subprocess, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_piper_cache = {}


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


async def synth(cfg, text, rate, pitch, vol, out):
    if cfg["engine"] == "edge":
        return await _edge(cfg, text, rate, pitch, vol, out)
    if cfg["engine"] == "piper":
        return await asyncio.to_thread(_piper_sync, cfg, text, rate, pitch, vol, out)
    raise ValueError(f"unknown engine {cfg['engine']}")
