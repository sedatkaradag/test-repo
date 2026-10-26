"""Reels template v2 (9:16): verse by verse in gold, hadith phrase by phrase in silver.

    python3 scripts/reels.py <entry_id> <out_dir> --caption-file <caption.txt>
        writes <out_dir>/reel_still.jpg (the finished last frame) and reel_preview.mp4,
        and prints any problem found in what was drawn.

Layout (top to bottom): label, hook, the text, (for verses) the meaning of the verse being
recited, reference, handle. The text is drawn dim and the part being recited (verse) or read
(hadith phrase) lights up; at the end everything is lit and the closing line appears.

Where the words come from:
  * Verse and hadith text: only the verified database (content.get), as on the feed cards.
    Punctuation is the same as on the card; the meaning shown under a verse is that verse's part
    of the card's English, cut at the verse boundary (no word changes).
  * Hook: the first line of the approved caption. Closing line: the caption's closing line.
    Nothing else is written by hand. The recitation line is not drawn (the caption has it).

Colours: verse text gold; hadith text silver and no gold at all on hadith Reels. The hook and
closing line are ivory on both.

Timing: a verse Reel lights each verse while it is recited. The recitation is only reachable
from GitHub, so the layout is planned here (and checked by the verifier on the still), stored
in the queue item, and GitHub draws the final video from that stored layout with each verse's
real duration (reel_audio.py). `layout_hash` proves GitHub drew exactly what was approved; if it
differs, GitHub falls back to stretching the preview video. Hadith Reels are silent and timed by
reading length.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import render as R
from content import ROOT, display_text, drop_dangling_closes, get, quote_context, smart_quotes, split_narrator

TEMPLATE = "v2"
SW, SH, FPS = 1080, 1920, 30
BOTTOM_LIMIT = 1585      # nothing below this: Instagram's caption and buttons cover it
TOP_LABEL = 250
HOOK_Y = 318
MAX_W_AR, MAX_W_EN = 900, 860

GOLD, IVORY, MUTED, BG, PATTERN = R.GOLD, R.IVORY, R.MUTED, R.BG, R.PATTERN
VERSE_ON, VERSE_DIM = (214, 178, 104), (104, 92, 64)        # gold
HADITH_ON, HADITH_DIM = (184, 198, 214), (88, 100, 110)     # silver
MEAL = (226, 218, 202)
BG_PATH = ROOT / "assets" / "reel_background.png"

TAIL = 2.0               # seconds the finished frame (with the closing line) stays at the end
HADITH_TAIL = 3.0


class TooLong(Exception):
    pass


# ---------- caption parts shown on the video ----------

def hook_and_cta(caption):
    """(hook, closing line) exactly as written in the approved caption."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", caption.strip()) if p.strip()]
    paras = [p for p in paras if not p.startswith("#") and not p.lower().startswith("recitation:")]
    hook = paras[0].splitlines()[0].strip() if paras else ""
    cta = paras[-1].strip() if len(paras) > 1 else ""
    return hook, cta


# ---------- drawing helpers ----------

def background():
    """Fixed 9:16 ground (generated once and stored, so every machine draws the same pixels)."""
    if BG_PATH.exists():
        return Image.open(BG_PATH).convert("RGB")
    img = Image.new("RGB", (SW, SH), BG)
    pat = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(pat)
    step = 120
    for gy in range(-step, SH + step, step):
        for gx in range(-step, SW + step, step):
            ox = step // 2 if (gy // step) % 2 else 0
            R._star(d, gx + ox, gy, 38, PATTERN + (255,), 2)
    small = Image.new("L", (SW // 4, SH // 4), 0)
    px = small.load()
    for y in range(SH // 4):
        for x in range(SW // 4):
            dist = math.hypot((x * 4 - SW / 2) / (SW * 0.7), (y * 4 - SH / 2) / (SH * 0.62))
            px[x, y] = int(max(0.0, min(1.0, (dist - 0.28) / 0.6)) * 255)
    mask = small.resize((SW, SH), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    pat.putalpha(ImageChops.multiply(pat.getchannel("A"), mask).point(lambda v: int(v * 0.5)))
    img.paste(pat, (0, 0), pat)
    vig = Image.new("L", (SW, SH), 120)
    ImageDraw.Draw(vig).rounded_rectangle([70, 140, SW - 70, SH - 140], radius=240, fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(110))
    img = Image.composite(Image.new("RGB", (SW, SH), (4, 14, 12)), img, vig)
    img.save(BG_PATH)
    return img


def layer():
    return Image.new("RGBA", (SW, SH), (0, 0, 0, 0))


def en_lines(text, size, max_w):
    return R._wrap(text.split(" "), max_w, lambda s: R._width_ltr(s, size))


def en_lh(size):
    return int(size * 1.38)


def draw_en(img, lines, size, y, color):
    d = ImageDraw.Draw(img)
    for line in lines:
        x = (SW - R._width_ltr(line, size)) / 2
        for t, f in R._runs(line, size):
            d.text((x, y), t, font=f, fill=color + (255,))
            x += f.getlength(t)
        y += en_lh(size)


def ar_lines(text, size):
    f = R._font(R.F_QURAN, size)
    return R._wrap(R._arabic_words(text), MAX_W_AR, lambda s: f.getlength(s, direction="rtl", language="ar"))


def ar_lh(size):
    return int(size * R.ARABIC_LINE)


def draw_ar(img, lines, size, y, color, boxes=None):
    d = ImageDraw.Draw(img)
    f = R._font(R.F_QURAN, size)
    for line in lines:
        w = f.getlength(line, direction="rtl", language="ar")
        pos = ((SW - w) / 2, y)
        d.text(pos, line, font=f, fill=color + (255,), direction="rtl", language="ar")
        if boxes is not None:
            boxes.append(d.textbbox(pos, line, font=f, direction="rtl", language="ar"))
        y += ar_lh(size)


def draw_label(img, text, y, color):
    d = ImageDraw.Draw(img)
    f = R._font(R.F_LABEL, 30)
    widths = [f.getlength(c) for c in text]
    tw = sum(widths) + 6 * (len(text) - 1)
    x = (SW - tw) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=f, fill=color + (255,))
        x += w + 6
    for side in (-1, 1):
        x0 = SW / 2 + side * (tw / 2 + 24)
        d.line([(x0, y + 18), (x0 + side * 70, y + 18)], fill=color + (255,), width=2)


def draw_center(img, text, y, size, color):
    d = ImageDraw.Draw(img)
    f = R._font(R.F_LABEL, size)
    d.text(((SW - f.getlength(text)) / 2, y), text, font=f, fill=color + (255,))


def hook_layout(hook):
    for size in range(82, 58, -4):
        lines = en_lines(hook, size, 900)
        if len(lines) <= 3:
            return lines, size
    raise TooLong("hook is too long for the video (keep the caption's first line to about 50 characters)")


# ---------- text split (layout only, no word changes) ----------

def _alnum(s):
    return re.sub(r"[^A-Za-z0-9]", "", s)


def verse_meanings(entry_id):
    """The card's English for a verse or range, cut at each verse boundary.

    Same text and punctuation as the feed card (display_text + dangling-quote rule); a cut is made
    after the last letter of a verse and the punctuation that follows it."""
    e = get(entry_id)
    _, dangling = quote_context(e)
    card = drop_dangling_closes(display_text(e["english"]), dangling)
    m = re.fullmatch(r"quran:(\d+):(\d+)(?:-(\d+))?", entry_id)
    s, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
    counts = [len(_alnum(get(f"quran:{s}:{v}")["english"])) for v in range(a, b + 1)]
    out, pos, seen = [], 0, 0
    for n in counts[:-1]:
        target = seen + n
        i = pos
        while i < len(card) and seen < target:
            if card[i].isascii() and card[i].isalnum():
                seen += 1
            i += 1
        while i < len(card) and not card[i].isspace() and not (card[i].isascii() and card[i].isalnum()):
            i += 1   # keep the punctuation that closes the verse (; . ” ] ) with it
        out.append(card[pos:i].strip())
        pos = i
    out.append(card[pos:].strip())
    return out, card


def hadith_parts(entry_id):
    """(lead, phrases, body): the hadith as the card shows it, the narration line apart and the
    words of the Prophet cut into 1-4 phrases at punctuation."""
    e = get(entry_id)
    narrator, body = split_narrator(e["english"])
    lead = smart_quotes(narrator) + ":" if narrator else None
    if not narrator:
        # "It was narrated from Abu Hurairah that the Messenger of Allah said: “...”"
        mm = re.match(r"^(.{10,170}?\b(?:said|saying)):\s*(?=[\"“A-Z])(.+)$", e["english"], re.S)
        if mm:
            lead, body = smart_quotes(mm.group(1)) + ":", mm.group(2)
    body = display_text(body)
    return lead, split_phrases(body), body


def split_phrases(text, target=95, most=4):
    sentences = [s for s in re.split(r"(?<=[.!?;:])\s+", text) if s]
    pieces = []
    for s in sentences:
        pieces += _halve(s, target)
    chunks = []
    for p in pieces:
        if chunks and len(chunks[-1]) + 1 + len(p) <= target * 0.8:
            chunks[-1] += " " + p
        else:
            chunks.append(p)
    if len(chunks) == 1 and len(text) > 60:
        chunks = _halve(text, len(text) - 1)
    while len(chunks) > most:
        k = min(range(len(chunks) - 1), key=lambda j: len(chunks[j]) + len(chunks[j + 1]))
        chunks[k:k + 2] = [chunks[k] + " " + chunks[k + 1]]
    return chunks


def _halve(s, target):
    """Cut a long phrase at the comma (or semicolon) nearest its middle."""
    if len(s) <= target:
        return [s]
    cuts = [m.end() for m in re.finditer(r"[,;:]\s", s)]
    cuts = [c for c in cuts if 25 <= c <= len(s) - 20]
    if not cuts:
        return [s]
    c = min(cuts, key=lambda x: abs(x - len(s) / 2))
    return _halve(s[:c].rstrip(), target) + _halve(s[c:].lstrip(), target)


# ---------- layout plans (plain data, stored in the queue item) ----------

def plan(entry_id, caption):
    hook, cta = hook_and_cta(caption)
    if not hook:
        raise TooLong("caption has no first line to use as the hook")
    if len(hook) > 60:
        raise TooLong(f"the caption's first line is the hook on the video: at most 60 characters (now {len(hook)})")
    if not cta or len(cta) > 90 or "\n" in cta:
        raise TooLong("the caption's closing line is shown at the end of the Reel: one line, at most 90 characters")
    e = get(entry_id)
    ref_no = e["reference"].split(" ")[-1]
    if ref_no in cta or "#" in cta or cta == hook:
        raise TooLong("the caption needs its own closing line after the reference (it is shown at the end of the Reel)")
    return plan_verse(entry_id, hook, cta) if e["type"] == "quran" else plan_hadith(entry_id, hook, cta)


def plan_story(entry_id):
    """Recitation Story of a verse feed post: the same verse-by-verse frame, without a hook or a
    closing line (the post itself carries the caption)."""
    return plan_verse(entry_id, None, None, story=True)


def plan_verse(entry_id, hook, cta, story=False):
    e = get(entry_id)
    m = re.fullmatch(r"quran:(\d+):(\d+)(?:-(\d+))?", entry_id)
    s, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
    arabic = [get(f"quran:{s}:{v}")["arabic_display"] for v in range(a, b + 1)]
    meanings, _ = verse_meanings(entry_id)
    if hook:
        h_lines, h_size = hook_layout(hook)
        hook_bottom = HOOK_Y + len(h_lines) * en_lh(h_size)
    else:
        h_lines, h_size, hook_bottom = [], 0, HOOK_Y + 20
    for meal_size in (46, 42, 38):
        cta_lines = en_lines(cta, meal_size + 2, MAX_W_EN) if cta else []
        for size in range(80, 44, -2):
            blocks = [ar_lines(t, size) for t in arabic]
            if any(len(bl) > 3 for bl in blocks):
                continue
            n = sum(len(bl) for bl in blocks)
            meal = [en_lines(t, meal_size, MAX_W_EN) for t in meanings]
            meal_h = max([len(x) * en_lh(meal_size) for x in meal] + [len(cta_lines) * en_lh(meal_size + 2)])
            if story and len(meal) > 1:
                # A Story ends on the whole meaning (it has no closing line to show).
                meal_h = max(meal_h, len(en_lines(" ".join(meanings), meal_size, MAX_W_EN)) * en_lh(meal_size))
            block = n * ar_lh(size) + 30 + meal_h + 30 + 110
            room = BOTTOM_LIMIT - (hook_bottom + 50)
            if block <= room:
                y = hook_bottom + 50 + (room - block) / 2 * 0.8
                verses, yy = [], y
                for k, bl in enumerate(blocks):
                    verses.append({"ayah": f"{s:03d}{a + k:03d}", "lines": bl, "y": yy,
                                   "meal": meal[k]})
                    yy += len(bl) * ar_lh(size)
                meal_y = yy + 30
                ref_y = meal_y + meal_h + 30
                if story:   # closing frame: every verse lit with its whole meaning
                    cta, cta_lines = " ".join(meanings), en_lines(" ".join(meanings), meal_size, MAX_W_EN)
                return {"template": TEMPLATE, "kind": "quran", "entry_id": entry_id, "story": story,
                        "label": "THE NOBLE QUR'AN", "hook": hook or "", "hook_lines": h_lines, "hook_size": h_size,
                        "arabic_size": size, "verses": verses, "meal_size": meal_size, "meal_y": meal_y,
                        "cta": cta, "cta_lines": cta_lines, "cta_size": meal_size if story else meal_size + 2,
                        "cta_color": "meal" if story else "ivory",
                        "ref": e["reference"], "ref_y": ref_y, "handle_y": ref_y + 52}
    raise TooLong("verses too long for one frame; choose a shorter passage")


def plan_hadith(entry_id, hook, cta):
    e = get(entry_id)
    lead, phrases, _ = hadith_parts(entry_id)
    h_lines, h_size = hook_layout(hook)
    hook_bottom = HOOK_Y + len(h_lines) * en_lh(h_size)
    lead_size = 34
    lead_lines = en_lines(lead, lead_size, 820) if lead else []
    cta_lines = en_lines(cta, 48, MAX_W_EN)
    for size in range(68, 42, -2):
        ph = [en_lines(p, size, 900) for p in phrases]
        lead_h = len(lead_lines) * en_lh(lead_size) + (36 if lead_lines else 0)
        text_h = sum(len(x) * en_lh(size) for x in ph) + 20 * (len(ph) - 1)
        block = lead_h + text_h + 40 + len(cta_lines) * en_lh(48) + 40 + 90
        room = BOTTOM_LIMIT - (hook_bottom + 60)
        if block <= room:
            y = hook_bottom + 60 + (room - block) / 2
            lead_y = y
            y += lead_h
            parts = []
            for lines in ph:
                parts.append({"lines": lines, "y": y})
                y += len(lines) * en_lh(size) + 20
            cta_y = y - 20 + 40
            ref_y = cta_y + len(cta_lines) * en_lh(48) + 40
            grade = str(e.get("status", "")).capitalize()
            return {"template": TEMPLATE, "kind": "hadith", "entry_id": entry_id,
                    "label": "HADITH", "hook": hook, "hook_lines": h_lines, "hook_size": h_size,
                    "lead_lines": lead_lines, "lead_size": lead_size, "lead_y": lead_y,
                    "text_size": size, "phrases": parts,
                    "cta": cta, "cta_lines": cta_lines, "cta_size": 48, "cta_y": cta_y,
                    "ref": f"{e['reference']} · Grade: {grade}", "ref_y": ref_y, "handle_y": ref_y + 52}
    raise TooLong("hadith too long for one Reel frame; choose a shorter one")


# ---------- layers ----------

def layers(L, boxes=None):
    """(static, dim, [lit part k], [meaning k], closing) as RGBA images drawn from the plan."""
    static, dim, cta = layer(), layer(), layer()
    lit, meals = [], []
    if L["kind"] == "quran":
        draw_label(static, L["label"], TOP_LABEL, GOLD)
        if L["hook_lines"]:
            draw_en(static, L["hook_lines"], L["hook_size"], HOOK_Y, IVORY)
        for v in L["verses"]:
            draw_ar(dim, v["lines"], L["arabic_size"], v["y"], VERSE_DIM, boxes)
            b = layer()
            draw_ar(b, v["lines"], L["arabic_size"], v["y"], VERSE_ON)
            lit.append(b)
            m = layer()
            draw_en(m, v["meal"], L["meal_size"], L["meal_y"], MEAL)
            meals.append(m)
        draw_en(cta, L["cta_lines"], L["cta_size"], L["meal_y"], MEAL if L.get("cta_color") == "meal" else IVORY)
        draw_center(static, L["ref"], L["ref_y"], 36, GOLD)
    else:
        draw_label(static, L["label"], TOP_LABEL, HADITH_ON)
        draw_en(static, L["hook_lines"], L["hook_size"], HOOK_Y, IVORY)
        if L["lead_lines"]:
            draw_en(static, L["lead_lines"], L["lead_size"], L["lead_y"], MUTED)
        for p in L["phrases"]:
            draw_en(dim, p["lines"], L["text_size"], p["y"], HADITH_DIM)
            b = layer()
            draw_en(b, p["lines"], L["text_size"], p["y"], HADITH_ON)
            lit.append(b)
        draw_en(cta, L["cta_lines"], L["cta_size"], L["cta_y"], IVORY)
        draw_center(static, L["ref"], L["ref_y"], 36, HADITH_ON)
    draw_center(static, R.HANDLE, L["handle_y"], 24, MUTED)
    return static, dim, lit, meals, cta


def layout_hash(L):
    """Fingerprint of every pixel the plan draws (and of the ground). Same plan + same fonts and
    Pillow = same hash, so GitHub can prove it drew exactly what the verifier saw."""
    h = hashlib.sha256()
    h.update(background().tobytes())
    static, dim, lit, meals, cta = layers(L)
    for im in [static, dim, *lit, *meals, cta]:
        h.update(im.tobytes())
    return h.hexdigest()[:24]


# ---------- checks (what was drawn, against the source) ----------

def issues(L):
    from integrity import _english_missing, _missing_glyphs
    out = []
    e = get(L["entry_id"])

    def check_en(lines, size, max_w, what):
        for n, line in enumerate(lines, 1):
            if _english_missing(line, size):
                out.append(f"{what} line {n} has a character the font cannot draw")
            if R._width_ltr(line, size) > max_w + 1:
                out.append(f"{what} line {n} is wider than the frame allows")

    check_en(L["hook_lines"], L["hook_size"], 900, "hook")
    check_en(L["cta_lines"], L["cta_size"], MAX_W_EN, "closing line")
    if " ".join(L["hook_lines"]) != L["hook"] or " ".join(L["cta_lines"]) != L["cta"]:
        out.append("hook or closing line drawn differently from the caption")
    if L.get("story") and _alnum(L["cta"]) != _alnum(e["english"]):
        out.append("the Story's closing meaning differs from the source text")
    if L["kind"] == "quran":
        drawn = [w for v in L["verses"] for line in v["lines"] for w in line.split(" ") if w]
        if " ".join(drawn) != " ".join(R._arabic_words(e["arabic_display"])):
            out.append("drawn Arabic differs from the source text")
        f = R._font(R.F_QURAN, L["arabic_size"])
        k = 0
        for v in L["verses"]:
            for line in v["lines"]:
                k += 1
                first = line[:1]
                if first and (unicodedata.category(first).startswith("M") or first == "⁠"):
                    out.append(f"Arabic line {k} starts with a loose mark (a word was split)")
                if _missing_glyphs(line, R.F_QURAN, rtl=True):
                    out.append(f"Arabic line {k} has a character the font cannot draw")
                if f.getlength(line, direction="rtl", language="ar") > MAX_W_AR + 1:
                    out.append(f"Arabic line {k} is wider than the frame allows")
                if line.split(" ")[0].startswith("﴿"):
                    out.append(f"Arabic line {k} starts with a verse number")
            check_en(v["meal"], L["meal_size"], MAX_W_EN, f"meaning of {v['ayah']}")
        if re.search(r"[۞۩]", " ".join(drawn)):
            out.append("a rub el hizb or sajdah sign was drawn")
        if "ۜ" in e["arabic"]:
            out.append("contains the small high seen (saktah / seen reading); choose another entry")
        boxes = []
        layers(L, boxes)
        for n in range(1, len(boxes)):
            gap = boxes[n][1] - boxes[n - 1][3]
            if gap < 0.2 * L["arabic_size"]:
                out.append(f"Arabic line {n + 1} comes too close to line {n} ({gap:.0f}px)")
        meanings = " ".join(" ".join(v["meal"]) for v in L["verses"])
        if _alnum(meanings) != _alnum(e["english"]):
            out.append("meanings on the Reel differ from the source text")
        bottom = L["handle_y"] + 30
    else:
        lead, phrases, body = hadith_parts(L["entry_id"])
        drawn = " ".join(" ".join(p["lines"]) for p in L["phrases"])
        if drawn != body:
            out.append("drawn hadith text differs from the card text")
        if _alnum(" ".join(L["lead_lines"]) + drawn) != _alnum(e["english"]):
            out.append("letters on the Reel differ from the source text")
        check_en(L["lead_lines"], L["lead_size"], 820, "narration")
        for p in L["phrases"]:
            check_en(p["lines"], L["text_size"], 900, "hadith")
        bottom = L["handle_y"] + 30
    if bottom > BOTTOM_LIMIT + 40:
        out.append("text reaches into the area Instagram covers")
    return out


# ---------- timing ----------

def _letters(s):
    return sum(1 for ch in s if unicodedata.category(ch).startswith("L"))


def preview_bounds(L):
    """Start time of each lit part, plus the end of the last one.
    Verses: estimated from length (GitHub replaces this with the real recitation timing).
    Hadith phrases: reading time."""
    if L["kind"] == "quran":
        durs = [min(14.0, max(2.5, 0.15 * _letters(" ".join(v["lines"])) + 0.8)) for v in L["verses"]]
    else:
        durs = []
        for k, p in enumerate(L["phrases"]):
            words = len(" ".join(p["lines"]).split())
            d = words * 0.32 + (2.2 if k == 0 else 1.2)
            durs.append(min(8.0, max(2.6, d)))
    out = [0.0]
    for d in durs:
        out.append(round(out[-1] + d, 2))
    return out


# ---------- frames and video ----------

def _ramp(t, a, b, fade=0.25):
    if t < a - fade or t > b + fade:
        return 0.0
    return float(min(1.0, (t - (a - fade)) / fade, ((b + fade) - t) / fade))


class _Layer:
    """An RGBA layer kept only over the rows it covers (blending is the slow part)."""

    def __init__(self, img):
        import numpy as np
        a = np.asarray(img, dtype=np.float32)
        rows = np.nonzero(a[..., 3].max(axis=1) > 0)[0]
        self.y0, self.y1 = (int(rows[0]), int(rows[-1]) + 1) if len(rows) else (0, 0)
        self.rgb = a[self.y0:self.y1, :, :3]
        self.alpha = a[self.y0:self.y1, :, 3:4] / 255.0

    def over(self, frame, k):
        if k <= 0 or self.y1 <= self.y0:
            return
        a = self.alpha * k
        sl = frame[self.y0:self.y1]
        sl *= (1 - a)
        sl += self.rgb * a


def _ffmpeg():
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def frames(L, bounds, end):
    """Yield (t, frame) as uint8 arrays."""
    import numpy as np
    bg = background()
    static, dim, lit, meals, cta = layers(L)
    st, dm, ct = _Layer(static), _Layer(dim), _Layer(cta)
    lt, ml = [_Layer(x) for x in lit], [_Layer(x) for x in meals]
    last = bounds[-1]
    n = int(round(end * FPS))
    for i in range(n):
        t = i / FPS
        s = 1.0 + 0.05 * min(1.0, t / end)
        bw, bh = int(SW * s), int(SH * s)
        b = bg.resize((bw, bh), Image.BILINEAR).crop(((bw - SW) // 2, (bh - SH) // 2,
                                                       (bw - SW) // 2 + SW, (bh - SH) // 2 + SH))
        frame = np.asarray(b, dtype=np.float32).copy()
        dm.over(frame, 1.0)
        st.over(frame, 1.0)
        done = t >= last
        for k in range(len(lt)):
            a = 1.0 if done else (1.0 if (k == 0 and t < bounds[1]) else _ramp(t, bounds[k], bounds[k + 1]))
            lt[k].over(frame, a)
            if ml and not done:
                ml[k].over(frame, a)
        if done:
            ct.over(frame, min(1.0, (t - last) / 0.35))
        yield t, frame.clip(0, 255).astype(np.uint8)


def still(L, out):
    """The finished frame (all text lit, closing line shown): the verifier opens this, and it is
    the Reel's card and cover."""
    import numpy as np
    bg = background()
    s = 1.05
    bw, bh = int(SW * s), int(SH * s)
    b = bg.resize((bw, bh), Image.BILINEAR).crop(((bw - SW) // 2, (bh - SH) // 2,
                                                   (bw - SW) // 2 + SW, (bh - SH) // 2 + SH))
    frame = np.asarray(b, dtype=np.float32).copy()
    static, dim, lit, meals, cta = layers(L)
    for im in [dim, static, *lit, cta]:
        _Layer(im).over(frame, 1.0)
    Image.fromarray(frame.clip(0, 255).astype(np.uint8)).save(out, "JPEG", quality=90)
    return out


def render_video(L, out, bounds=None, audio=None):
    """Write the MP4. `bounds`: start of each lit part plus the end of the last (seconds);
    `audio`: recitation file for verse Reels (otherwise silent)."""
    bounds = bounds or preview_bounds(L)
    end = bounds[-1] + (TAIL if L["kind"] == "quran" else HADITH_TAIL)
    if audio:
        ain = ["-i", str(audio)]
        af = ["-filter:a", "apad"]
    else:
        ain = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        af = []
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}",
           "-r", str(FPS), "-i", "-", *ain, "-map", "0:v", "-map", "1:a", *af,
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-t", f"{end:.2f}", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for _, f in frames(L, bounds, end):
        proc.stdin.write(f.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return round(end, 2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entry")
    p.add_argument("out_dir")
    p.add_argument("--caption-file", help="caption (Reels); not used with --story")
    p.add_argument("--story", action="store_true", help="the recitation Story of a verse post")
    p.add_argument("--no-video", action="store_true", help="only the still (fast)")
    a = p.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        L = plan_story(a.entry) if a.story else plan(a.entry, Path(a.caption_file).read_text(encoding="utf-8"))
    except TooLong as e:
        print(f"too_long: {e}")
        sys.exit(3)
    bad = issues(L)
    still(L, out / "reel_still.jpg")
    print(f"still {out / 'reel_still.jpg'}")
    if not a.no_video:
        sec = render_video(L, out / "reel_preview.mp4")
        print(f"video {out / 'reel_preview.mp4'} ({sec}s, timing: "
              f"{'estimated, GitHub uses the recitation' if L['kind'] == 'quran' else 'reading time'})")
    print(json.dumps({"ok": not bad, "issues": bad}, ensure_ascii=False))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
