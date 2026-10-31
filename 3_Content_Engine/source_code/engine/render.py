"""Render asset specs to final files (MP4 / PNG / PDF). Pure Pillow + ffmpeg.

Everything drawn is programmatic: Inter (SIL OFL) fonts, flat colours, no stock media,
no faces, no music, no synthetic voice -> nothing that needs a licence or an AI label.
"""
import functools
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ASSET_DIR = Path(__file__).parent / "assets"
FPS = 30
XFADE = 6  # frames of cross-fade between scenes


class RenderError(Exception):
    pass


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Theme:
    def __init__(self, brand):
        c = brand["colors"]
        self.bg, self.bg2, self.accent = _rgb(c["bg"]), _rgb(c["bg2"]), _rgb(c["accent"])
        self.cyan, self.text, self.muted = _rgb(c["cyan"]), _rgb(c["text"]), _rgb(c["muted"])
        self.fonts = {k: str(ASSET_DIR / v) for k, v in brand["fonts"].items()}
        self.name = brand["brand_name"]
        self.footer = brand["footer"]

    @functools.lru_cache(maxsize=256)
    def font(self, weight, size):
        return ImageFont.truetype(self.fonts[weight], size)


@functools.lru_cache(maxsize=8)
def _background(w, h, bg, bg2, accent):
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(bg[i] + (bg2[i] - bg[i]) * t) for i in range(3)))
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = int(w * 0.55)
    gd.ellipse([w - r // 2, -r // 2, w + r // 2, r // 2], fill=tuple(int(c * 0.45) for c in accent))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=int(w * 0.12)))
    return _add(img, glow)


def _add(a, b):
    return ImageChops.add(a, b)


def _wrap_words(draw, words, font, max_w):
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and draw.textlength(trial, font=font) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def _fit(draw, theme, text, weight, max_w, max_h, start, minimum, spacing=1.18):
    words = text.split()
    for size in range(start, minimum - 1, -4):
        f = theme.font(weight, size)
        lines = _wrap_words(draw, words, f, max_w)
        if len(lines) * size * spacing <= max_h:
            return f, size, lines
    f = theme.font(weight, minimum)
    return f, minimum, _wrap_words(draw, words, f, max_w)


def _draw_lines(draw, theme, lines, font, size, x, y, color, active=-1, offset=0, spacing=1.18,
                muted=None, align="left", max_w=0):
    """Draw wrapped word lines; word index `active` highlighted (karaoke style)."""
    idx = 0
    for ln in lines:
        line_text = " ".join(ln)
        lw = draw.textlength(line_text, font=font)
        cx = x + ((max_w - lw) / 2 if align == "center" else 0)
        for wi, w in enumerate(ln):
            col = color
            if active >= 0:
                col = theme.cyan if idx == active else (color if idx < active else (muted or theme.muted))
            draw.text((cx, y), w, font=font, fill=col)
            cx += draw.textlength(w + " ", font=font)
            idx += 1
        y += size * spacing
    return y


def _wordmark(draw, theme, w, y, scale=1.0):
    # Use a plain typographic name treatment. Do not invent or imply an
    # official IncuBrix logo when authorized brand artwork is unavailable.
    size = int(40 * scale)
    draw.text((90, y), theme.name, font=theme.font("bold", size), fill=theme.text)
    width = draw.textlength(theme.name, font=theme.font("bold", size))
    draw.rounded_rectangle(
        [90, y + int(52 * scale), 90 + width, y + int(58 * scale)],
        radius=max(1, int(3 * scale)),
        fill=theme.cyan,
    )


def _frame(theme, w, h, scene, cur_word=-1, safe_top=None, safe_bottom=None, deck=None):
    """One still of a scene (video scene or slide)."""
    img = _background(w, h, theme.bg, theme.bg2, theme.accent).copy()
    d = ImageDraw.Draw(img)
    tall = h > w * 1.5
    top = safe_top if safe_top is not None else (260 if tall else 90)
    bottom = safe_bottom if safe_bottom is not None else (h - (380 if tall else 150))
    _wordmark(d, theme, w, top - 130 if tall else 70)
    mx = 90
    max_w = w - 2 * mx
    kind = scene["kind"]
    text, sub = scene.get("text", ""), scene.get("sub", "")
    avail = bottom - top - 140

    if kind in ("hook", "cover"):
        f, size, lines = _fit(d, theme, text, "bold", max_w, avail * 0.75, 132 if tall else 120, 60)
        block = len(lines) * size * 1.18
        y = top + (avail - block) / 2 - (30 if sub else 0)
        d.rounded_rectangle([mx, y - 46, mx + 120, y - 34], radius=6, fill=theme.accent)
        y = _draw_lines(d, theme, lines, f, size, mx, y, theme.text, active=cur_word)
        if sub:
            fs, ss, sl = _fit(d, theme, sub, "regular", max_w, 200, 44, 30)
            _draw_lines(d, theme, sl, fs, ss, mx, y + 26, theme.muted)
        if kind == "cover" and deck:
            d.text((mx, bottom - 20), "Swipe  →", font=theme.font("semibold", 42), fill=theme.cyan)
    elif kind == "point":
        n = scene.get("n", "")
        badge = 96
        d.ellipse([mx, top + 20, mx + badge, top + 20 + badge], fill=theme.accent)
        nf = theme.font("bold", 54)
        nt = str(n)
        d.text((mx + badge / 2 - d.textlength(nt, font=nf) / 2, top + 20 + 16), nt, font=nf, fill=theme.text)
        y0 = top + 20 + badge + 60
        f, size, lines = _fit(d, theme, text, "bold", max_w, (bottom - y0) * 0.6, 92 if tall else 84, 48)
        y = _draw_lines(d, theme, lines, f, size, mx, y0, theme.text, active=cur_word)
        if sub:
            fs, ss, sl = _fit(d, theme, sub, "regular", max_w, bottom - y - 30, 46, 30)
            _draw_lines(d, theme, sl, fs, ss, mx, y + 34, theme.muted)
        if deck:
            d.text((w - mx - 200, bottom - 10), f"{n:02d} / {deck - 2:02d}" if isinstance(n, int) else "",
                   font=theme.font("semibold", 34), fill=theme.muted)
    elif kind == "cta":
        f, size, lines = _fit(d, theme, text, "bold", max_w, avail * 0.55, 100 if tall else 92, 52)
        block = len(lines) * size * 1.18
        y = top + (avail - block) / 2 - 60
        y = _draw_lines(d, theme, lines, f, size, mx, y, theme.text, active=cur_word)
        if sub:
            fs, ss, sl = _fit(d, theme, sub, "regular", max_w, 160, 44, 30)
            y = _draw_lines(d, theme, sl, fs, ss, mx, y + 20, theme.muted)
        btn = theme.footer
        bf = theme.font("bold", 46)
        bw = d.textlength(btn, font=bf) + 80
        d.rounded_rectangle([mx, y + 50, mx + bw, y + 50 + 96], radius=48, fill=theme.accent)
        d.text((mx + 40, y + 50 + 22), btn, font=bf, fill=theme.text)
    elif kind == "card":   # single-image graphic
        f, size, lines = _fit(d, theme, text, "bold", max_w, avail * 0.62, 128 if h >= w else 100, 52)
        block = len(lines) * size * 1.18
        y = top + (avail - block) / 2 - (50 if sub else 0)
        d.rounded_rectangle([mx, y - 46, mx + 120, y - 34], radius=6, fill=theme.accent)
        y = _draw_lines(d, theme, lines, f, size, mx, y, theme.text)
        if sub:
            fs, ss, sl = _fit(d, theme, sub, "regular", max_w, 360, 46, 28)
            _draw_lines(d, theme, sl, fs, ss, mx, y + 30, theme.muted)
    else:
        raise RenderError(f"unknown scene kind {kind!r}")

    if kind != "cta":
        d.text((mx, h - (110 if tall else 80)), theme.footer, font=theme.font("semibold", 34), fill=theme.muted)
    return img


def scene_seconds(scene):
    n = len((scene.get("text", "") + " " + scene.get("sub", "")).split())
    return float(scene.get("seconds") or max(2.4, 1.6 + 0.42 * n))


def video_duration(spec):
    return sum(scene_seconds(s) for s in spec["scenes"])


def render_video(spec, out_path, theme):
    w, h = spec["size"]
    w, h = int(w), int(h)
    tall = h > w * 1.5
    scenes = spec["scenes"]
    total = video_duration(spec)
    if total > 60.0:
        raise RenderError(f"video is {total:.1f}s, limit 60s")
    voiceover = spec.get("voiceover_path")
    if voiceover:
        voiceover = Path(voiceover)
        rights = voiceover.with_suffix(voiceover.suffix + ".rights.json")
        if not voiceover.is_file() or not rights.is_file():
            raise RenderError("voiceover requires an audio file and adjacent .rights.json")
        cmd_audio = ["-i", str(voiceover), "-af", "apad"]
    else:
        cmd_audio = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(FPS), "-i", "-", *cmd_audio, "-shortest",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart",
           "-metadata", f"title={spec.get('asset_id', '')}", str(out_path)]
    tmp = str(out_path) + ".part.mp4"
    cmd[-1] = tmp
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise RenderError("ffmpeg not found on PATH") from exc
    bar_y0 = (h - 300) if tall else (h - 60)
    prev_img = None
    elapsed = 0.0
    try:
        for si, sc in enumerate(scenes):
            dur = scene_seconds(sc)
            nframes = max(1, round(dur * FPS))
            nwords = max(1, len(sc.get("text", "").split()))
            cache = {}
            for fi in range(nframes):
                # karaoke highlight: advance across the first ~80% of the scene
                prog = fi / max(1, nframes - 1)
                cur = min(nwords - 1, int(prog / 0.8 * nwords)) if sc["kind"] != "cta" else -1
                if cur not in cache:
                    cache[cur] = _frame(theme, w, h, sc, cur_word=cur)
                base = cache[cur]
                if si > 0 and fi < XFADE and prev_img is not None:
                    base = Image.blend(prev_img, base, (fi + 1) / (XFADE + 1))
                gfx = base.copy()
                gd = ImageDraw.Draw(gfx)
                done = (elapsed + fi / FPS) / total
                gd.rectangle([90, bar_y0, 90 + int((w - 180) * done), bar_y0 + 8], fill=theme.cyan)
                gd.rectangle([90 + int((w - 180) * done), bar_y0, w - 90, bar_y0 + 8], fill=(40, 50, 80))
                proc.stdin.write(gfx.tobytes())
            prev_img = cache[list(cache)[-1]]
            elapsed += dur
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise RenderError(f"ffmpeg failed: {err[-300:]}")
        os.replace(tmp, out_path)
    except BrokenPipeError as exc:
        raise RenderError(f"ffmpeg pipe closed: {proc.stderr.read().decode(errors='replace')[-300:]}") from exc
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    return total


def render_carousel(spec, out_dir, theme, make_pdf=True):
    """slides: [cover, point..., cta]; writes slide_01.png... and carousel.pdf"""
    w, h = spec["size"]
    slides = spec["slides"]
    if not (5 <= len(slides) <= 10):
        raise RenderError(f"carousel has {len(slides)} slides; need 5-10")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    imgs = []
    for i, sc in enumerate(slides, 1):
        im = _frame(theme, int(w), int(h), sc, deck=len(slides), safe_top=170, safe_bottom=int(h) - 190)
        p = out_dir / f"slide_{i:02d}.png"
        im.save(p, optimize=True)
        imgs.append(im)
    if make_pdf:
        imgs[0].save(out_dir / "carousel.pdf", save_all=True, append_images=imgs[1:], resolution=150.0)
    return len(slides)


def render_graphic(spec, out_path, theme):
    w, h = spec["size"]
    im = _frame(theme, int(w), int(h), dict(spec["card"], kind="card"), safe_top=170, safe_bottom=int(h) - 190)
    im.save(out_path, optimize=True)
    return 1
