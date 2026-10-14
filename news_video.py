#!/usr/bin/env python
"""Turn news article links into vertical shorts: article screenshot + related images, voice-over, karaoke captions,
and a footer with the headline and the source.

  python news_video.py fetch <url> [<url> ...]      read each article (text, date, source) and take a screenshot
        -> work/news/<slug>/article.json, article.txt, screenshot.png
  (Claude reads article.txt and writes work/news/<slug>/script.json, see below; you approve the batch)
  python news_video.py build <slug> [<slug> ...]    or: build --all
        -> videos/news/<slug>/<slug>.mp4
  python news_video.py status                        what is fetched / scripted / built

Layout, 1080x1920
  y    0-230   header: the article headline (up to 3 lines)
  y  230-1440  content: article screenshot scrolling slowly, and related stock clips (marked "Hình minh họa")
  y 1475-1620  karaoke captions (position unchanged)
  y 1650-1920  footer: "Nguồn: <outlet> · <date>"

script.json
  {"title": "footer headline (the article's headline, shortened only if it is too long)",
   "source": "VnExpress", "audience": "tre" | "trung-nien" (optional), "genre": "news" (optional),
   "scenes": [{"vi": "narration", "visual": "article" | "stock" | "chart", "terms": ["english stock term", "..."],
               "image": "charts/chart1.png", "label": "Biểu đồ: Goldman Sachs"}]}
Scenes marked "article" show the screenshot scrolling down; "stock" scenes need 3 English search terms; "chart" scenes show
a picture that `fetch` saved from inside the article (charts/chartN.png, listed in charts.json) fitted in the frame with a slow
zoom, tagged "Biểu đồ" (or "label"). If the article has charts they are always used: one "chart" scene per chart.
"""
import argparse, asyncio, json, re, subprocess, sys, textwrap, time
import compat
from pathlib import Path
from urllib.parse import urlparse

import karaoke
import profiles
import short_video as sv
import voices

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "work" / "news"
OUT = ROOT / "videos" / "news"
W, H = 1080, 1920
HEAD_H = 230              # header with the headline
CONTENT_Y = HEAD_H        # content area starts under the header
CONTENT_H = 1210          # content area height (ends at y 1440)
CAP_Y = 1475              # top of the first caption line
FOOT_Y = 1650             # footer starts here
SCROLL_PX_PER_SEC = 110   # how fast the article screenshot scrolls
VIEW_W, SCALE = 480, 2.25  # phone-width page, rendered at 1080 px
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/17.0 Mobile/15E148 Safari/604.1")


def log(msg):
    print(f"[news-video] {msg}", flush=True)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", profiles.norm(text)).strip("-")[:44] or "bai-bao"


# ---------------------------------------------------------------- fetch
HIDE_FIXED = """() => {
  document.querySelectorAll('*').forEach(e => {
    const s = getComputedStyle(e);
    if (s.position === 'fixed' || s.position === 'sticky') e.style.display = 'none';
  });
  document.documentElement.style.overflow = 'visible';
}"""
EXPAND = ["Story Continues", "Continue reading", "Continue Reading", "Read the full story", "Show more", "Xem thêm", "Đọc tiếp", "Xem toàn bộ bài"]
CONSENT = ["Đồng ý", "Chấp nhận", "Chấp nhận tất cả", "Tôi đồng ý", "Accept all", "Accept", "I agree", "Allow all", "Đóng", "Close"]


def trim_blank_top(path):
    """Cut the empty ad slot some sites leave above the page (rows that are all white or all black).
    Returns how many pixels were removed (0 when the page starts with content)."""
    import numpy as np
    from PIL import Image
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    flat = (a.min(axis=2) > 245) | (a.max(axis=2) < 12)          # white or black pixels
    content_frac = 1 - flat.mean(axis=1)                             # share of non-blank pixels per row
    busy = content_frac > 0.08                                       # rows that really hold content
    first = next((y for y in range(len(busy) - 4) if busy[y:y + 4].all()), 0)   # 4 in a row: ignores 1px anti-aliased edges
    cut = max(0, first - 16)                                         # keep a little margin above the first content
    if cut < 200:
        return 0
    im.crop((0, cut, im.width, im.height)).save(path)
    return cut


def squeeze_blank(src, dst, min_run=300, keep=40):
    """Remove empty bands in the middle of a page screenshot (ad slots that never loaded), leaving `keep` px of white.
    Returns the path to read from: dst when something was removed, otherwise src."""
    import numpy as np
    from PIL import Image
    im = Image.open(src).convert("RGB")
    a = np.asarray(im)
    blank = (a.min(axis=2) > 245).all(axis=1)
    runs, start = [], None
    for y, b in enumerate(blank):
        if b and start is None:
            start = y
        elif not b and start is not None:
            if y - start >= min_run and start > 0:
                runs.append((start, y))
            start = None
    tail = start + keep if (start is not None and start > 0 and len(blank) - start >= min_run) else None   # blank all the way to the bottom
    if not runs and tail is None:
        return src
    parts, pos = [], 0
    for y0, y1 in runs:
        parts.append(im.crop((0, pos, im.width, y0 + keep)))
        pos = y1 - keep
    parts.append(im.crop((0, pos, im.width, tail if tail is not None and tail > pos else im.height)))
    out = Image.new("RGB", (im.width, sum(p.height for p in parts)), "white")
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height
    out.save(dst)
    return dst


# Images and chart embeds that sit inside the article body: found between the first and the last paragraph of the extracted text
# (so the lead photo, ads, "related stories" and the next stories of an endless-scroll page are left out).
GRAB_JS = r"""(articleText) => {
  const clean = s => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const body = clean(articleText);
  const ps = [...document.querySelectorAll('p')].filter(p => {
    const t = clean(p.innerText || '');
    return t.length > 60 && body.includes(t.slice(0, 50));
  });
  if (!ps.length) return [];
  // endless-scroll pages append more stories (sometimes quoting the same sentences): keep only the first run of paragraphs,
  // i.e. stop at the first jump of more than 3500 px between two matching paragraphs
  const pos = ps.map(p => ({t: p.getBoundingClientRect().top + scrollY, b: p.getBoundingClientRect().bottom + scrollY}))
                .sort((x, y) => x.t - y.t);
  let top = pos[0].t, bottom = pos[0].b;
  for (const q of pos.slice(1)) {
    if (q.t - bottom > 3500) break;
    bottom = Math.max(bottom, q.b);
  }
  const skip = 'aside, nav, footer, [class*="related"], [class*="recirc"], [class*="newsletter"], [class*="promo"], [class*="sponsor"]';
  const embed = /datawrapper|flourish|infogram|tableau|ourworldindata|everviz|visualisations|datawrapper\.dwcdn/i;
  const found = [];
  document.querySelectorAll('img, iframe').forEach(e => {
    const r = e.getBoundingClientRect();
    const y = r.top + scrollY;
    if (r.width < 260 || r.height < 120 || y < top - 5 || y > bottom + 120 || e.closest(skip)) return;
    const ratio = r.width / r.height;
    if (ratio > 4.5 || ratio < 0.25) return;
    const src = e.tagName === 'IMG' ? (e.currentSrc || e.src || '') : (e.src || '');
    if (e.tagName === 'IFRAME' && !embed.test(src)) return;
    if (/avatar|logo|sprite|pixel|icon|emoji/i.test(src)) return;
    const fig = e.closest('figure');
    found.push({y: Math.round(y), src, tag: e.tagName, alt: e.alt || '',
                caption: fig && fig.querySelector('figcaption') ? fig.querySelector('figcaption').innerText.trim() : ''});
    e.setAttribute('data-nv-fig', String(found.length - 1));
  });
  return found;
}"""


def fetch_image(page, src):
    """Download an image with the page's own session; returns an RGB PIL image or None."""
    import io
    from PIL import Image
    if not src.startswith("http"):
        return None
    try:
        resp = page.context.request.get(src, timeout=20000)
        if not resp.ok:
            return None
        im = Image.open(io.BytesIO(resp.body()))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        return im.convert("RGB")
    except Exception:
        return None


def grab_charts(page, text, d, limit=8):
    """Save the images / chart embeds inside the article body as charts/chart1.png ... (reading order) plus charts.json.
    Claude looks at them while writing the script and uses the real charts as 'chart' scenes."""
    import hashlib, io
    from PIL import Image
    cdir = d / "charts"
    for old in list(cdir.glob("*")) if cdir.exists() else []:
        old.unlink()
    height = page.evaluate("document.documentElement.scrollHeight")
    y = 0
    while y < min(height, 16000):                         # scroll through the page so lazy images load
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(250)
        y += 800
        height = page.evaluate("document.documentElement.scrollHeight")
    page.wait_for_timeout(500)
    cands = page.evaluate(GRAB_JS, text) or []
    figs, seen = [], set()
    for k, c in enumerate(cands):
        key = hashlib.md5(c["src"].encode()).hexdigest() if c["src"] else str(k)
        if key in seen or len(figs) >= limit:
            continue
        seen.add(key)
        cdir.mkdir(exist_ok=True)
        out = cdir / f"chart{len(figs) + 1}.png"
        im = fetch_image(page, c["src"]) if c["tag"] == "IMG" else None
        if im is None:                                     # embeds (Datawrapper...) and images that cannot be downloaded
            try:
                page.locator(f'[data-nv-fig="{k}"]').first.screenshot(path=str(out), timeout=8000)
                im = Image.open(out).convert("RGB")
            except Exception:
                continue
        if im.width < 260 or im.height < 120:
            continue
        im.save(out)
        figs.append({"file": f"charts/{out.name}", "caption": c["caption"], "alt": c["alt"], "src": c["src"][:300],
                     "width": im.width, "height": im.height})
    (d / "charts.json").write_text(json.dumps(figs, ensure_ascii=False, indent=1), encoding="utf-8")
    return figs


def fetch_one(page, url, name=None):
    import trafilatura
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    for label in CONSENT:                                  # dismiss cookie / consent popups when there is one
        try:
            btn = page.get_by_role("button", name=label, exact=True).first
            if btn.is_visible(timeout=300):
                btn.click(timeout=800)
                page.wait_for_timeout(300)
        except Exception:
            pass
    page.evaluate(HIDE_FIXED)
    page.wait_for_timeout(400)
    for label in EXPAND:                                   # articles folded behind a "Story Continues" style button
        try:
            btn = page.get_by_role("button", name=label, exact=True).first
            if btn.is_visible(timeout=300):
                btn.click(timeout=1500)
                page.wait_for_timeout(1200)
                log(f"  opened the folded part of the article ({label})")
        except Exception:
            pass
    html = page.content()
    got = trafilatura.extract(html, url=url, output_format="json", with_metadata=True, include_comments=False,
                              favor_precision=True)
    info = json.loads(got) if got else {}
    title = (info.get("title") or page.title() or "").strip()
    host = urlparse(url).netloc.lower().removeprefix("www.")
    source = (info.get("sitename") or host).strip()
    slug = name or slugify(title)
    d = BASE / slug
    d.mkdir(parents=True, exist_ok=True)
    full = page.evaluate("document.documentElement.scrollHeight")
    page.screenshot(path=str(d / "screenshot.png"), full_page=True, timeout=90000,
                    clip={"x": 0, "y": 0, "width": VIEW_W, "height": float(min(full, 1700))})
    cut = trim_blank_top(str(d / "screenshot.png"))
    if cut:
        log(f"  removed {cut}px of empty ad space above the article in the screenshot")
    text = (info.get("text") or "").strip()
    try:
        figs = grab_charts(page, text, d)
    except Exception as e:
        figs = []
        log(f"  could not look for charts: {type(e).__name__}: {str(e)[:100]}")
    if figs:
        log(f"  {len(figs)} image(s) inside the article body saved to charts/ (charts, tables or photos; look at each one):")
        for f in figs:
            log(f"    {f['file']}  {f['width']}x{f['height']}  {f['caption'] or f['alt'] or '(no caption)'}"[:150])
    art = {"url": url, "title": title, "source": source, "host": host, "date": info.get("date"),
           "author": info.get("author"), "description": info.get("description"), "text": text,
           "words": len(text.split())}
    (d / "article.json").write_text(json.dumps(art, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "article.txt").write_text(
        f"{title}\nNguồn: {source} ({host})  Ngày: {art['date'] or 'không rõ'}  Tác giả: {art['author'] or 'không rõ'}\n"
        f"{url}\n\n{text}\n", encoding="utf-8")
    note = ""
    if len(text) < 600:
        note = "  !! nội dung ngắn: có thể bị chặn, cần đăng nhập hoặc là trang không phải bài báo"
    log(f"{slug}: {title[:70]} | {source} | {art['date'] or 'no date'} | {art['words']} words{note}")
    return slug


def cmd_fetch(a):
    from playwright.sync_api import sync_playwright
    done = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)       # the real Chrome gives the most reliable pages
        except Exception:
            browser = p.chromium.launch(headless=True)                          # bundled Chromium: python -m playwright install chromium
        ctx = browser.new_context(viewport={"width": VIEW_W, "height": 1000}, device_scale_factor=SCALE, user_agent=UA,
                                  is_mobile=True, has_touch=True, locale="vi-VN")
        for k, url in enumerate(a.urls):
            page = ctx.new_page()
            try:
                done.append(fetch_one(page, url, a.name if len(a.urls) == 1 else None))
            except Exception as e:
                log(f"FAILED {url}: {type(e).__name__}: {str(e)[:150]}")
            finally:
                page.close()
        browser.close()
    if done:
        log("next: read work/news/<slug>/article.txt and screenshot.png, then write work/news/<slug>/script.json")


# ---------------------------------------------------------------- build
def ass_text(s):
    return s.replace("{", "(").replace("}", ")")


def balanced(text, width):
    """Split into one line, or two lines of similar length (no stray one-word second line)."""
    words = text.split()
    if len(text) <= width or len(words) < 2:
        return [text]
    best = min(range(1, len(words)), key=lambda k: max(len(" ".join(words[:k])), len(" ".join(words[k:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def footer_events(title, source, date, total, stock_spans, lang="vi"):
    """Headline centred in the header band (56 px, two lines; 46 px for three), source centred in the footer."""
    t = ass_text(title)
    size, lh = 56, 68
    if len(textwrap.wrap(t, width=28)) <= 2:
        lines = balanced(t, 28)                      # one line, or two lines of similar length
    else:
        lines, size, lh = textwrap.wrap(t, width=34, max_lines=3, placeholder="…"), 46, 56
    lines = lines or [""]
    y = (HEAD_H - 6 - lh * len(lines)) // 2
    src = ("Source: " if lang == "en" else "Nguồn: ") + source; src = src + (f" · {date}" if date else "")
    ys = FOOT_Y + 6 + (H - FOOT_Y - 6 - 46) // 2
    ev = ["Dialogue: 0,%s,%s,FooterTitle,,0,0,0,,{\\an8\\pos(540,%d)\\fs%d}%s\n" % (
        karaoke.ts(0), karaoke.ts(total), y, size, "\\N".join(lines)),
        "Dialogue: 0,%s,%s,FooterSrc,,0,0,0,,{\\an8\\pos(540,%d)}%s\n" % (
        karaoke.ts(0), karaoke.ts(total), ys, ass_text(src))]
    for span in stock_spans:                          # (start, end) = stock illustration, (start, end, label) = chart
        a_, b_ = span[0], span[1]
        label = ass_text(span[2]) if len(span) > 2 else ("Illustration" if lang == "en" else "Hình minh họa")
        ev.append("Dialogue: 0,%s,%s,Tag,,0,0,0,,{\\an7\\pos(36,%d)}%s\n" % (
            karaoke.ts(a_), karaoke.ts(b_), CONTENT_Y + 24, label))
    return ev


def build_ass(sents, starts, art, sc, total, stock_spans, path):
    segs = []
    for i, ss in enumerate(sents):
        sub = sc["scenes"][i].get("sub")           # subtitle text in another language, matched sentence by sentence
        subs = sv.split_sentences(sub) if sub else None
        if subs is not None and len(subs) != len(ss):
            sys.exit(f"scene {i + 1}: 'sub' has {len(subs)} sentences but 'vi' has {len(ss)}; they must match one to one")
        for j, s_ in enumerate(ss):
            t0 = starts[i] + s_["start"]
            words = [] if subs else [{"w": w["w"], "s": t0 + w["s"], "e": t0 + w["e"]} for w in s_.get("words", [])]
            segs.append({"start": t0, "end": t0 + s_["dur"], "text": subs[j] if subs else s_["text"], "words": words})
    ass = karaoke.build_ass(segs, W, H, y_px=CAP_Y)
    styles = (
        "Style: FooterTitle,Arial,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1\n"
        "Style: FooterSrc,Arial,42,&H00FFB8C9,&H00FFB8C9,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1\n"
        "Style: Tag,Arial,28,&H00FFFFFF,&H00FFFFFF,&H80000000,&H00000000,-1,0,0,0,100,100,0,0,3,9,0,7,40,40,40,1\n")
    i = ass.index("Style: Default,")
    j = ass.index("\n", i) + 1
    ass = ass[:j] + styles + ass[j:]
    date = (art.get("date") or "")[:10]
    if re.match(r"\d{4}-\d{2}-\d{2}", date):
        date = f"{date[8:10]}/{date[5:7]}/{date[:4]}"
    ass += "".join(footer_events(sc.get("title") or art["title"], sc.get("source") or art["source"], date, total, stock_spans, sc.get("lang", "vi")))
    path.write_text(ass, encoding="utf-8")


def article_clip(shot, T, y0, out, share=None):
    """Content-area clip from the screenshot: scrolls down slowly. Returns the scroll distance used."""
    from PIL import Image
    w, h = Image.open(shot).size
    sh = round(h * W / w)                                  # height once scaled to 1080 wide
    room = max(0, sh - CONTENT_H - y0)
    D = min(room, SCROLL_PX_PER_SEC * T)
    if share is not None:                                  # several article scenes: each gets its part of the page
        D = min(D, room * share)
    vf = (f"scale={W}:-2,pad={W}:'max({CONTENT_H},ih)':0:0:white,"
          f"crop={W}:{CONTENT_H}:0:'{y0:.0f}+{D:.0f}*min(1,t/{T:.2f})',fps=30,format=yuv420p")
    sv.ff("-loop", 1, "-framerate", 30, "-t", f"{T:.3f}", "-i", shot, "-vf", vf, "-c:v", "libx264", "-crf", 18,
          "-preset", "fast", "-color_range", "tv", out)
    return D


def chart_clip(img_path, T, out):
    """Content-area clip for a chart (or any picture from the article): fitted inside the frame on white, slow zoom-in."""
    from PIL import Image
    im = Image.open(img_path).convert("RGB")
    k = 2                                                  # compose at 2x so the zoom does not jitter
    box_w, box_h = (W - 40) * k, (CONTENT_H - 90) * k
    f = min(box_w / im.width, box_h / im.height)
    im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    canvas = Image.new("RGB", (W * k, CONTENT_H * k), "white")
    canvas.paste(im, ((W * k - im.width) // 2, (CONTENT_H * k - im.height) // 2 + 20 * k))
    cpath = Path(out).with_suffix(".png")
    canvas.save(cpath)
    frames = max(2, round(T * 30))
    vf = (f"zoompan=z='1+0.05*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{CONTENT_H}:fps=30,"
          f"format=yuv420p")
    sv.ff("-i", cpath, "-vf", vf, "-t", f"{T:.3f}", "-c:v", "libx264", "-crf", 18, "-preset", "fast", "-color_range", "tv", out)


def audio_gaps(path):
    """Holes in the audio timeline (seconds) longer than 0.3 s: a gap means narration is missing."""
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "packet=pts_time", "-select_streams", "a",
                                   "-of", "csv=p=0", str(path)], text=True)
    p = [float(x.strip(",")) for x in out.split() if x.strip(",")]
    return [(round(x, 2), round(y, 2)) for x, y in zip(p, p[1:]) if y - x > 0.3]


def compose(d, ass_path, music, total, out):
    """Mix voice and music first (audio only), then lay the picture and subtitles over the content and attach that audio.
    Doing both in one ffmpeg graph used to drop about 3 s of audio at the first scene changes."""
    mix = d / "mix.wav"
    fade = f"afade=t=out:st={total - 2:.2f}:d=2"
    afc = (f"[0:a]loudnorm=I=-16:TP=-1.5,aresample=44100[vo];"
           f"[1:a]loudnorm=I=-14:TP=-1.5,aresample=44100,volume=0.18,{fade}[m];"
           f"[vo][m]amix=inputs=2:duration=first:normalize=0,apad=whole_dur={total:.3f}[aud]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "voice.wav"), "-stream_loop", "-1", "-i", str(music),
                    "-filter_complex", afc, "-map", "[aud]", "-t", f"{total:.3f}", "-ar", "44100", "-ac", "2", str(mix)],
                   cwd=ROOT, check=True)
    rel = ass_path.relative_to(ROOT).as_posix()
    fc = (f"color=c=0x15102a:s={W}x{H}:r=30:d={total:.3f}[bg];[bg][0:v]overlay=0:{CONTENT_Y}[a];"
          f"[a]drawbox=x=0:y=0:w={W}:h={HEAD_H}:color=0x241546:t=fill,"
          f"drawbox=x=0:y={HEAD_H - 6}:w={W}:h=6:color=0xB44CFF:t=fill,"
          f"drawbox=x=0:y={FOOT_Y}:w={W}:h={H - FOOT_Y}:color=0x241546:t=fill,"
          f"drawbox=x=0:y={FOOT_Y}:w={W}:h=6:color=0xB44CFF:t=fill,"
          f"{compat.ass_filter(rel)},format=yuv420p[v]")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "content.mp4"), "-i", str(mix), "-filter_complex", fc,
                    "-map", "[v]", "-map", "1:a", "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], cwd=ROOT, check=True)
    gaps = audio_gaps(out)
    if gaps:
        log(f"WARNING: the audio has holes at {gaps}; part of the narration is missing")


def build_one(slug, a):
    d = BASE / slug
    art = json.loads((d / "article.json").read_text(encoding="utf-8"))
    sc = json.loads((d / "script.json").read_text(encoding="utf-8"))
    scenes = sc["scenes"]
    prof = profiles.resolve(genre=a.genre or sc.get("genre") or "news", audience=a.audience or sc.get("audience") or "tre",
                            voice=a.voice, rate=int(str(sc["rate"]).rstrip("%")) if "rate" in sc else None,
                            music=sc.get("music"))
    if prof["audience"] == "none" and "music" not in sc:
        prof["music"] = profiles.load()["music"][prof["genre"]]["tre"]
    cfg = voices.resolve(prof["voice"])
    spec = {"scenes": scenes, "voice_cfg": cfg, "voice": cfg["key"], "rate": f"{prof['rate']:+d}%", "music": prof["music"],
            "express": prof["express"]}
    log(f"{slug}: voice {cfg['key']}, rate {spec['rate']}, music {spec['music']}")
    if a.dry_run:
        return
    if any(s.get("visual", "stock") == "stock" for s in scenes):
        sv.ensure_server()
    music = sv.ensure_music(spec["music"], d)

    sents = asyncio.run(sv._tts_all(spec, d))
    n = len(scenes)
    targets = [sv.probe_duration(d / f"s{i}.mp3") for i in range(n)]
    targets[-1] += sv.TAIL
    starts = [sum(targets[:i]) for i in range(n)]
    total = sum(targets)
    log(f"narration {total - sv.TAIL:.1f}s (no length limit for news)")

    segs, stock_spans, y0 = [], [], 0.0
    art_idx = [k for k, x in enumerate(scenes) if x.get("visual", "stock") == "article"]
    shot = str(d / "screenshot.png")
    if sc.get("shot_height") or sc.get("shot_top") or sc.get("cut_bands"):   # keep a slice of the page (drops ads, popups, blank parts)
        from PIL import Image
        im = Image.open(shot).convert("RGB")
        if sc.get("cut_bands"):                    # [[y0, y1], ...] in screenshot pixels: remove these bands and close the gap
            pieces, pos = [], 0
            for y0, y1 in sorted(sc["cut_bands"]):
                pieces.append(im.crop((0, pos, im.width, y0)))
                pos = y1
            pieces.append(im.crop((0, pos, im.width, im.height)))
            joined = Image.new("RGB", (im.width, sum(p.height for p in pieces)), "white")
            yy = 0
            for p_ in pieces:
                joined.paste(p_, (0, yy))
                yy += p_.height
            im = joined
        top = int(sc.get("shot_top", 0))
        bottom = min(int(sc.get("shot_height", im.height)), im.height)
        im.crop((0, top, im.width, bottom)).save(d / "screenshot_crop.png")
        shot = str(d / "screenshot_crop.png")
    sq = squeeze_blank(shot, d / "screenshot_squeezed.png")
    if str(sq) != shot:
        log(f"  removed empty bands from the screenshot (ad slots that did not load)")
        shot = str(sq)
    for i, s in enumerate(scenes):
        out = d / f"c{i}.mp4"
        if s.get("visual", "stock") == "article":
            y0 += article_clip(shot, targets[i], y0, out, share=targets[i] / sum(targets[k] for k in art_idx if k >= i))
        elif s.get("visual") == "chart":                   # a real chart or picture taken from the article (charts/chartN.png)
            img = d / s.get("image", "")
            if not s.get("image") or not img.is_file():
                have = ", ".join(sorted(p_.name for p_ in (d / "charts").glob("*"))) or "none (fetch found no pictures in the article)"
                sys.exit(f"scene {i + 1}: chart image {s.get('image')!r} not found in {d}; available in charts/: {have}")
            chart_clip(img, targets[i], out)
            label = s.get("label") or ("Chart" if sc.get("lang") == "en" else "Biểu đồ")
            stock_spans.append((starts[i], starts[i] + targets[i], label))
        else:
            v = sv.render_scene_picture(i, s, targets[i], d, a.reuse_footage)
            # stock clips can arrive tagged full-range; convert to limited range and tag it, because the clips are joined with
            # -c copy and a stray full-range tag would be inherited by the clips after it (white chart/page turning grey)
            sv.ff("-i", v, "-vf", f"crop={W}:{CONTENT_H}:0:{(1920 - CONTENT_H) // 2},scale=out_range=tv,fps=30,format=yuv420p",
                  "-c:v", "libx264", "-crf", 18, "-preset", "fast", "-color_range", "tv", out)
            stock_spans.append((starts[i], starts[i] + targets[i]))
        segs.append(out)
    (d / "clist.txt").write_text("".join(f"file '{p.name}'\n" for p in segs), encoding="utf-8")
    sv.ff("-f", "concat", "-safe", "0", "-i", d / "clist.txt", "-c", "copy", d / "content.mp4")

    parts = []
    for i in range(n):
        sv.ff("-i", d / f"s{i}.mp3", "-af", f"apad=whole_dur={targets[i]:.3f}", "-ar", 44100, "-ac", 2, d / f"p{i}.wav")
        parts.append(f"file 'p{i}.wav'\n")
    (d / "alist.txt").write_text("".join(parts), encoding="utf-8")
    sv.ff("-f", "concat", "-safe", "0", "-i", d / "alist.txt", "-c", "copy", d / "voice.wav")

    ass_path = d / "subs.ass"
    build_ass(sents, starts, art, sc, total, stock_spans, ass_path)
    rel = ass_path.relative_to(ROOT).as_posix()
    outdir = OUT / slug
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{slug}.mp4"
    compose(d, ass_path, music, total, out)
    # one frame in the middle of every scene, for the visual check
    frames = []
    for i in range(n):
        f = d / f"chk{i}.png"
        sv.ff("-ss", f"{starts[i] + targets[i] * 0.55:.2f}", "-i", out, "-frames:v", 1, "-vf", "scale=270:-1", f)
        frames.append(f)
    inp = sum([["-i", str(f)] for f in frames], [])
    sv.ff(*inp, "-filter_complex", "".join(f"[{k}:v]" for k in range(n)) + f"hstack=inputs={n}", "-frames:v", 1,
          d / "montage.png")
    for f in frames:
        f.unlink()
    log(f"done: {out.relative_to(ROOT)}  {sv.probe_duration(out):.1f}s  {out.stat().st_size / 1048576:.1f} MB")
    return out


def cmd_build(a):
    slugs = a.slugs
    if a.all:
        slugs = sorted(p.parent.name for p in BASE.glob("*/script.json") if not (OUT / p.parent.name / f"{p.parent.name}.mp4").exists())
    if not slugs:
        sys.exit("nothing to build (no script.json yet, or everything is built already)")
    ok, bad = [], []
    for slug in slugs:
        try:
            build_one(slug, a)
            ok.append(slug)
        except (SystemExit, Exception) as e:
            bad.append((slug, f"{type(e).__name__}: {e}"))
            log(f"FAILED {slug}: {e}")
    log(f"batch done: {len(ok)} built, {len(bad)} failed")
    for s, e in bad:
        log(f"  failed: {s} ({e[:120]})")


def cmd_remux(a):
    for slug in a.slugs:
        d = BASE / slug
        sc = json.loads((d / "script.json").read_text(encoding="utf-8"))
        prof = profiles.resolve(genre=a.genre or sc.get("genre") or "news", audience=a.audience or sc.get("audience") or "tre",
                                voice=a.voice, music=sc.get("music"))
        music = sv.ensure_music(prof["music"], d)
        total = sv.probe_duration(d / "content.mp4")
        out = OUT / slug / f"{slug}.mp4"
        compose(d, d / "subs.ass", music, total, out)
        log(f"remuxed {out.relative_to(ROOT)}  {sv.probe_duration(out):.1f}s  {out.stat().st_size / 1048576:.1f} MB")


def cmd_status(a):
    if not BASE.exists():
        print("no articles yet")
        return
    for d in sorted(p for p in BASE.iterdir() if (p / "article.json").exists()):
        art = json.loads((d / "article.json").read_text(encoding="utf-8"))
        st = ["fetched"]
        if (d / "script.json").exists():
            st.append("script")
        if (OUT / d.name / f"{d.name}.mp4").exists():
            st.append("built")
        print(f"{d.name:46} {'+'.join(st):22} {art['source']} | {art['title'][:60]}")


def main():
    ap = argparse.ArgumentParser(description="News article links -> vertical shorts.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("urls", nargs="+")
    f.add_argument("--name")
    f.set_defaults(fn=cmd_fetch)
    b = sub.add_parser("build")
    b.add_argument("slugs", nargs="*")
    b.add_argument("--all", action="store_true", help="every fetched article that has a script and no video yet")
    b.add_argument("--voice", default=None, help="female (default) or male, or a key of voices.json")
    b.add_argument("--audience", default=None, help="tre or trung-nien (changes voice age and music)")
    b.add_argument("--genre", default=None)
    b.add_argument("--reuse-footage", action="store_true")
    b.add_argument("--dry-run", action="store_true")
    b.set_defaults(fn=cmd_build)
    r = sub.add_parser("remux", help="redo only the final mix and compose for built videos (no new voice or footage)")
    r.add_argument("slugs", nargs="+")
    r.add_argument("--voice", default=None)
    r.add_argument("--audience", default=None, help="selects the music, as in build")
    r.add_argument("--genre", default=None)
    r.set_defaults(fn=cmd_remux)
    s = sub.add_parser("status")
    s.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
