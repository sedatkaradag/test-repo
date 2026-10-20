"""Render a post image (1080x1350 JPEG) for a verified entry.

    python scripts/render.py <entry_id> <out.jpg>

The background is fixed (assets/background.png, generated once from code);
only the text changes. Text is taken from the database, never from arguments.
Exits with code 3 if the text does not fit, so the curator picks another entry.
"""
import math
import sys
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from content import ROOT, display_text, get, smart_quotes, split_narrator

W, H = 1080, 1350
BG = (13, 36, 32)
PATTERN = (44, 86, 74)
GOLD = (201, 166, 96)
IVORY = (244, 236, 222)
MUTED = (160, 170, 158)
HANDLE = "@thehalalalgorithm"

FONTS = ROOT / "assets" / "fonts"
F_BODY = FONTS / "EBGaramond[wght].ttf"
F_LABEL = FONTS / "Marcellus-Regular.ttf"
F_QURAN = FONTS / "AmiriQuran-Regular.ttf"
F_ARABIC = FONTS / "Amiri-Regular.ttf"
BG_PATH = ROOT / "assets" / "background.png"

TEXT_LEFT, TEXT_RIGHT = 140, W - 140
TEXT_TOP, TEXT_BOTTOM = 250, 1095


class TooLong(Exception):
    pass


# ---------- background (fixed theme) ----------

def _star(draw, cx, cy, r, color, width):
    """Eight-pointed star: two overlapping squares."""
    for rot in (0, math.pi / 4):
        pts = [(cx + r * math.cos(rot + k * math.pi / 2), cy + r * math.sin(rot + k * math.pi / 2))
               for k in range(4)]
        draw.polygon(pts, outline=color, width=width)


def make_background():
    img = Image.new("RGB", (W, H), BG)

    # Geometric pattern on its own layer, faded towards the centre so text stays clean.
    pat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(pat)
    step = 96
    for gy in range(-step, H + step, step):
        for gx in range(-step, W + step, step):
            ox = step // 2 if (gy // step) % 2 else 0
            _star(d, gx + ox, gy, 30, PATTERN + (255,), 2)
            d.ellipse([gx + ox - 4, gy - 4, gx + ox + 4, gy + 4], outline=PATTERN + (255,), width=1)
    # Radial mask: pattern invisible in the middle, visible towards the edges.
    small = Image.new("L", (W // 4, H // 4), 0)
    px = small.load()
    for y in range(H // 4):
        for x in range(W // 4):
            dist = math.hypot((x * 4 - W / 2) / (W * 0.62), (y * 4 - H / 2) / (H * 0.62))
            px[x, y] = int(max(0.0, min(1.0, (dist - 0.30) / 0.55)) * 255)
    mask = small.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4))
    alpha = ImageChops.multiply(pat.getchannel("A"), mask).point(lambda v: int(v * 0.6))
    pat.putalpha(alpha)
    img.paste(pat, (0, 0), pat)

    # Soft vignette.
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle([0, 0, W, H], fill=110)
    vd.rounded_rectangle([90, 90, W - 90, H - 90], radius=200, fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(90))
    img = Image.composite(Image.new("RGB", (W, H), (4, 14, 12)), img, vig)

    # Double gold frame with star corners.
    d = ImageDraw.Draw(img)
    d.rectangle([56, 56, W - 56, H - 56], outline=GOLD, width=2)
    d.rectangle([68, 68, W - 68, H - 68], outline=(120, 104, 70), width=1)
    for (x, y) in [(56, 56), (W - 56, 56), (56, H - 56), (W - 56, H - 56)]:
        d.rectangle([x - 16, y - 16, x + 16, y + 16], fill=BG)
        _star(d, x, y, 13, GOLD, 2)
    img.save(BG_PATH)
    return img


def background():
    if not BG_PATH.exists():
        return make_background()
    return Image.open(BG_PATH).convert("RGB")


# ---------- text layout ----------

@lru_cache(maxsize=None)
def _cmap(path):
    return set(TTFont(str(path)).getBestCmap().keys())


@lru_cache(maxsize=None)
def _font(path, size):
    return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)


def _runs(text, size):
    """Split text into (substring, font) runs, falling back to Amiri for glyphs
    the body font lacks (e.g. the ﷺ ligature)."""
    body = _cmap(F_BODY)
    runs = []
    for ch in text:
        path = F_BODY if ord(ch) in body or ch == " " else F_ARABIC
        if runs and runs[-1][1] == path:
            runs[-1][0] += ch
        else:
            runs.append([ch, path])
    return [(t, _font(p, size if p == F_BODY else int(size * 0.95))) for t, p in runs]


def _width_ltr(text, size):
    return sum(f.getlength(t) for t, f in _runs(text, size))


def _wrap(words, max_w, measure):
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if measure(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _layout_english(text, size, max_w):
    lines = _wrap(text.split(" "), max_w, lambda s: _width_ltr(s, size))
    return lines, int(size * 1.42)


def _layout_arabic(text, size, max_w, path):
    f = _font(path, size)
    lines = _wrap(text.split(" "), max_w,
                  lambda s: f.getlength(s, direction="rtl", language="ar"))
    return lines, int(size * 1.95)


def _draw_english(draw, lines, size, lh, y, color):
    for line in lines:
        x = (W - _width_ltr(line, size)) / 2
        for t, f in _runs(line, size):
            draw.text((x, y), t, font=f, fill=color)
            x += f.getlength(t)
        y += lh
    return y


def _draw_arabic(draw, lines, size, lh, y, color, path):
    """Draw RTL lines; return the lowest pixel actually inked (marks included)."""
    f = _font(path, size)
    bottom = y
    for line in lines:
        w = f.getlength(line, direction="rtl", language="ar")
        pos = ((W - w) / 2, y)
        draw.text(pos, line, font=f, fill=color, direction="rtl", language="ar")
        bottom = max(bottom, draw.textbbox(pos, line, font=f, direction="rtl", language="ar")[3])
        y += lh
    return bottom


def _label(draw, text, y, size=30, color=GOLD, spacing=6):
    f = _font(F_LABEL, size)
    widths = [f.getlength(c) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = (W - total) / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=f, fill=color)
        x += w + spacing
    return total


def _divider(draw, y):
    cx = W / 2
    draw.line([(cx - 90, y), (cx - 16, y)], fill=GOLD, width=1)
    draw.line([(cx + 16, y), (cx + 90, y)], fill=GOLD, width=1)
    draw.polygon([(cx, y - 7), (cx + 7, y), (cx, y + 7), (cx - 7, y)], outline=GOLD, fill=None)


def render(entry_id, out_path):
    e = get(entry_id)
    img = background()
    d = ImageDraw.Draw(img)
    max_w = TEXT_RIGHT - TEXT_LEFT
    avail = TEXT_BOTTOM - TEXT_TOP
    english = display_text(e["english"])
    is_quran = e["type"] == "quran"

    # Header label with short rules either side.
    label = "THE NOBLE QUR'AN" if is_quran else "HADITH"
    tw = _label(d, label, 140)
    for side in (-1, 1):
        x0 = W / 2 + side * (tw / 2 + 24)
        d.line([(x0, 158), (x0 + side * 60, 158)], fill=GOLD, width=1)

    # Fit text: shrink until everything fits in the text box.
    plan = None
    if is_quran:
        for ar_size in range(66, 47, -2):
            en_size = int(ar_size * 0.68)
            a_lines, a_lh = _layout_arabic(e["arabic"], ar_size, max_w, F_QURAN)
            e_lines, e_lh = _layout_english(english, en_size, max_w)
            total = len(a_lines) * a_lh + 84 + len(e_lines) * e_lh
            if total <= avail:
                plan = (a_lines, ar_size, a_lh, e_lines, en_size, e_lh, total)
                break
    else:
        narrator, body = split_narrator(e["english"])
        english = display_text(body)
        narrator = smart_quotes(narrator) if narrator else None
        for en_size in range(54, 33, -2):
            e_lines, e_lh = _layout_english(english, en_size, max_w)
            n_size = max(26, int(en_size * 0.62))
            n_lines, n_lh = _layout_english(narrator, n_size, max_w) if narrator else ([], 0)
            n_block = len(n_lines) * n_lh + (34 if n_lines else 0)
            total = n_block + len(e_lines) * e_lh
            if total <= avail:
                plan = (None, 0, 0, e_lines, en_size, e_lh, total)
                break
    if plan is None:
        raise TooLong(entry_id)

    a_lines, ar_size, a_lh, e_lines, en_size, e_lh, total = plan
    y = TEXT_TOP + (avail - total) / 2
    if a_lines:
        y = _draw_arabic(d, a_lines, ar_size, a_lh, y, IVORY, F_QURAN)
        _divider(d, y + 40)
        y += 84
    elif not is_quran and narrator:
        y = _draw_english(d, n_lines, n_size, n_lh, y, MUTED)
        y += 34
    _draw_english(d, e_lines, en_size, e_lh, y, IVORY if not a_lines else (222, 214, 198))

    # Reference and handle.
    ref = e["reference"]
    f = _font(F_LABEL, 30)
    d.text(((W - f.getlength(ref)) / 2, 1150), ref, font=f, fill=GOLD)
    f2 = _font(F_LABEL, 24)
    d.text(((W - f2.getlength(HANDLE)) / 2, 1232), HANDLE, font=f2, fill=MUTED)

    img.save(out_path, "JPEG", quality=92, optimize=True)
    return out_path


def make_story(post_path, out_path, label="TODAY'S REMINDER"):
    """9:16 Story frame: the post centred on the same ground with a label above it."""
    post = Image.open(post_path).convert("RGB")
    sw, sh = 1080, 1920
    story = Image.new("RGB", (sw, sh), BG)
    scale = 0.86
    pw, ph = int(W * scale), int(H * scale)
    story.paste(post.resize((pw, ph), Image.LANCZOS), ((sw - pw) // 2, (sh - ph) // 2))
    d = ImageDraw.Draw(story)
    f = _font(F_LABEL, 34)
    spacing = 8
    widths = [f.getlength(c) for c in label]
    x = (sw - (sum(widths) + spacing * (len(label) - 1))) / 2
    for c, w in zip(label, widths):
        d.text((x, 230), c, font=f, fill=GOLD)
        x += w + spacing
    story.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path


if __name__ == "__main__":
    try:
        render(sys.argv[1], sys.argv[2])
        print(f"ok {sys.argv[2]}")
    except TooLong:
        print("too_long: pick a shorter entry")
        sys.exit(3)
