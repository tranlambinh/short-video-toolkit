"""Genre + audience profiles: one place that decides voice age, speaking pace and background music.

  /short-video tranh luận: chủ đề --trẻ        genre tranh-luan, audience tre
  /short-video info: chủ đề --trung_niên       genre info,       audience trung-nien
  /short-video tâm sự: chủ đề --trung_niên     genre tam-su,     audience trung-nien
  /short-video góc nhìn: chủ đề --trẻ          genre goc-nhin,   audience tre
  /short-video nhận định: chủ đề --trẻ         genre nhan-dinh,  audience tre

The values live in profiles.json (and voices.json for the voices themselves).
"""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load():
    return json.loads((ROOT / "profiles.json").read_text(encoding="utf-8"))


def norm(s):
    """'Trung_niên' -> 'trung-nien', 'tâm sự' -> 'tam-su' (no accents, hyphens)."""
    s = unicodedata.normalize("NFD", s.strip().lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "-".join(s.replace("_", " ").replace("-", " ").split())


def _find(table, name, what):
    n = norm(name)
    for key, v in table.items():
        if n == key or n in [norm(a) for a in v.get("aliases", [])]:
            return key
    raise SystemExit(f"unknown {what} '{name}'. Valid: {', '.join(table)}")


def resolve(genre=None, audience=None, voice=None, rate=None, music=None):
    """Return the settings for one video. Explicit rate / music / voice win over the profile."""
    p = load()
    g = _find(p["genres"], genre or p["defaults"]["genre"], "genre")
    none_aud = audience is None or norm(audience) in ("none", "khong", "mac-dinh", "default")
    a = None if none_aud else _find(p["audiences"], audience, "audience")
    voice = (voice or "female").strip()
    if a and voice.lower() in ("female", "male"):
        voice = f"{voice.lower()}-{p['audiences'][a]['voice_age']}"      # gender + age preset from voices.json
    out_rate = int(rate) if rate is not None else int(p["genres"][g]["rate"])
    out_music = music or (p["music"][g][a] if a else p["music"][g]["tre"])
    return {"genre": g, "audience": a or "none", "voice": voice, "rate": out_rate, "music": out_music,
            "words": p["genres"][g]["words"], "seconds": p["genres"][g]["seconds"],
            "express": float(p["genres"][g].get("express", 1.0))}
