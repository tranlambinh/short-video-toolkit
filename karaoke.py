"""Purple karaoke subtitles (ASS) shared by the subtitle tools.

Transcript format used everywhere (JSON, editable by hand):
  {"language": "vi", "segments": [{"start": 0.1, "end": 3.4, "text": "...", "words": [{"w": "Xin", "s": 0.1, "e": 0.3}]}]}
If a segment's "text" no longer matches its words (because it was edited or translated), word timing is
spread over the segment evenly by letter count, so you can fix typos or translate without re-running Whisper.

Look: white text that turns purple word by word, black outline, centred, Arial 56 px on a 1080 px wide
frame. The first line starts at a fixed height (default 676 px above the bottom of a 1080x1920 video) so
captions never jump up and down between one-line and two-line texts.
"""
import re

PURPLE = "&H00FF4CB4"   # ASS colours are &HAABBGGRR, so this is RGB #B44CFF, the vivid purple of sung words
WHITE = "&H00FFFFFF"
Y_FRAC_PORTRAIT = (1920 - 676) / 1920     # top of the first line, as a fraction of the height
Y_FRAC_LANDSCAPE = 0.78


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def srt_ts(t):
    t = max(0.0, t)
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def _clean(w):
    return re.sub(r"[{}\\]", "", w).strip()


def normalize_segments(segments):
    """Make sure every segment has words consistent with its text (re-spread timing if the text was edited)."""
    out = []
    for seg in segments:
        text = " ".join(seg.get("text", "").split())
        if not text:
            continue
        words = seg.get("words") or []
        joined = " ".join(_clean(w["w"]) for w in words)
        if words and " ".join(joined.split()) == text:
            ws = [{"w": _clean(w["w"]), "s": float(w["s"]), "e": float(w["e"])} for w in words if _clean(w["w"])]
        else:
            toks = text.split()
            total = sum(len(t) for t in toks) or 1
            s0, e0 = float(seg["start"]), float(seg["end"])
            t, ws = s0, []
            for tok in toks:
                d = (e0 - s0) * len(tok) / total
                ws.append({"w": _clean(tok), "s": t, "e": t + d})
                t += d
        out.append({"start": float(seg["start"]), "end": float(seg["end"]), "text": text, "words": ws})
    return out


def style_for(W, H, y_frac=None, font="Arial"):
    base = min(W, H)
    size = round(base * 0.0519)                      # 56 px at 1080
    if y_frac is None:
        y_frac = Y_FRAC_PORTRAIT if H >= W else Y_FRAC_LANDSCAPE
    chars = min(42, int(0.88 * W / (size * 0.5)))    # about 34 per line on a 1080 px wide video
    return {"size": size, "y": round(H * y_frac), "chars": chars, "font": font, "outline": max(2, round(size * 0.09))}


def build_events(segments, chars):
    """Chunk every segment into two-line captions with per-word karaoke timing.
    Returns a list of (start, end, lines) where lines is a list of lists of (word, start, end)."""
    events = []
    for seg in normalize_segments(segments):
        lines, cur, n = [], [], 0
        for w in seg["words"]:
            add = len(w["w"]) + (1 if cur else 0)
            if cur and n + add > chars:
                lines.append(cur)
                cur, n = [], 0
                add = len(w["w"])
            cur.append(w)
            n += add
        if cur:
            lines.append(cur)
        for k in range(0, len(lines), 2):
            chunk = lines[k:k + 2]
            flat = [w for ln in chunk for w in ln]
            events.append((flat[0]["s"], flat[-1]["e"], chunk))
    # never overlap the next caption
    for i in range(len(events) - 1):
        if events[i][1] > events[i + 1][0]:
            events[i] = (events[i][0], events[i + 1][0] - 0.02, events[i][2])
    return events


def title_text(text, chars=20):
    """Wrap a title into at most two balanced lines, joined with the ASS line break."""
    import textwrap
    words = text.strip().split()
    if len(" ".join(words)) <= chars:
        return " ".join(words)
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, a, b)
    return best[1] + "\\N" + best[2]


def build_ass(segments, W, H, y_frac=None, font="Arial", y_px=None, title=None):
    """title = {"text": str, "start": s, "end": s, "y": px} adds a purple-boxed title at the top of the caption area."""
    st = style_for(W, H, y_frac, font)
    if y_px is not None:
        st["y"] = int(y_px)
    tsize = round(min(W, H) * 0.06)
    title_style = (f"Style: Title,{st['font']},{tsize},&H00FFFFFF,&H00FFFFFF,&H00D9286D,&H00000000,-1,0,0,0,100,100,0,0,3,"
                   f"{round(tsize * 0.28)},0,8,60,60,0,1\n") if title else ""
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{st['font']},{st['size']},{PURPLE},{WHITE},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,"
        f"{st['outline']},1,8,60,60,0,1\n{title_style}\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    rows = []
    for s, e, chunk in build_events(segments, st["chars"]):
        flat = [w for ln in chunk for w in ln]
        parts, idx = [], 0
        for li, ln in enumerate(chunk):
            if li:
                parts[-1] = parts[-1].rstrip() + "\\N"
            for w in ln:
                nxt = flat[idx + 1]["s"] if idx + 1 < len(flat) else w["e"]
                idx += 1
                cs = max(1, round((max(nxt, w["e"]) - w["s"]) * 100))
                parts.append("{\\kf%d}%s " % (cs, w["w"]))
        rows.append("Dialogue: 0,%s,%s,Default,,0,0,0,,{\\an8\\pos(%d,%d)}%s\n"
                    % (ts(s), ts(e), W // 2, st["y"], "".join(parts).rstrip()))
    if title:
        rows.insert(0, "Dialogue: 1,%s,%s,Title,,0,0,0,,{\\an8\\pos(%d,%d)\\fad(250,350)}%s\n"
                    % (ts(title["start"]), ts(title["end"]), W // 2, int(title["y"]), title_text(title["text"])))
    return header + "".join(rows)


def build_srt(segments, W, H):
    st = style_for(W, H)
    out = []
    for i, (s, e, chunk) in enumerate(build_events(segments, st["chars"]), start=1):
        txt = "\n".join(" ".join(w["w"] for w in ln) for ln in chunk)
        out.append(f"{i}\n{srt_ts(s)} --> {srt_ts(e)}\n{txt}\n")
    return "\n".join(out)
