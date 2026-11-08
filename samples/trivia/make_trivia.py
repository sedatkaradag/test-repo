"""Not part of the publishing pipeline: "Qur'an Quiz" trivia Reel, 3 questions, our look.

    python3 make_trivia.py <repo> <audio_dir> <out_dir> <rounds.json>

Intro (logo) -> each question: text + 3 options + 5 s bar -> answer -> the verse that gives the answer,
recited and lit word by word, with its meaning (the answer words in light green, in the Arabic and the meaning) and reference -> final score.
"""
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO, AUD, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(REPO / "scripts"))
import reels as RL  # noqa: E402
import render as R  # noqa: E402
from content import get  # noqa: E402

SW, SH, FPS = RL.SW, RL.SH, RL.FPS
OUT.mkdir(parents=True, exist_ok=True)
SR = 44100
GREEN = (118, 196, 146)
INTRO, THINK, REVEAL, SHOWV, HOLD, XF, FINAL = 3.0, 5.0, 0.9, 0.5, 1.6, 0.35, 4.0
ANSWER_GREEN = (140, 236, 152)   # the answer word, in the Arabic and in the meaning

# the questions come from a JSON file (4th argument): q, entry, verses, options, answer, highlight
# (answer words in the meaning), ar_answer (0-based word numbers in the Arabic)
ROUNDS = json.loads(Path(sys.argv[4]).read_text())
ALIGN = json.loads((AUD / "align.json").read_text())

Y_TOP = 250                  # label
Y_Q = 390                    # question block (to ~650)
OPT_X, OPT_W, OPT_H, OPT_GAP, Y_OPT = 140, 800, 140, 30, 720
Y_BAR = Y_OPT + 3 * (OPT_H + OPT_GAP) + 18
V_TOP = 880                  # verse block after the answer
Y_HANDLE = 1535


def font(path, size):
    return R._font(path, size)


def text_center(d, text, cx, y, f, color):
    d.text((cx - f.getlength(text) / 2, y), text, font=f, fill=color)


# ---------- logo: the page's own mark (assets/logo.png), revealed stroke by stroke ----------

LOGO_PX = 800                    # logo image size on the frame (the arch is about 385 px wide)
LOGO_CX, LOGO_CY = SW / 2, 700   # where the logo's centre sits


LOGO_DONE = 1.72                 # the pen is finished; the drawn strokes hand over to the original file


def logo_reveal(LOGO_PX=LOGO_PX):
    """Everything needed to draw the logo: the original image (rgb, alpha) for the finished mark, and
    three layers that are revealed along the pen's path while drawing: the thin lines and the thick
    strokes, drawn here as clean vector strokes measured from the original, and the crescent (from the
    original). Keeping thin and thick strokes in separate layers means a stroke never shows a piece of
    another stroke before that one is drawn."""
    from scipy.spatial import cKDTree
    src = Image.open(REPO / "assets" / "logo.png").convert("RGB").resize((LOGO_PX, LOGO_PX), Image.LANCZOS)
    im = np.asarray(src, dtype=np.float32)
    bg = im[4, 4]
    gold, thin_c, ivory_c = np.array([201, 166, 96.]), np.array([126, 114, 71.]), np.array([244, 236, 222.])
    best_a, best_c, best_r = None, None, None
    for f in (gold, thin_c, ivory_c):                # the original, unpremultiplied from its background
        d = f - bg
        a = np.clip(((im - bg) @ d) / (d @ d), 0, 1)
        r = np.abs(im - (bg + a[..., None] * d)).sum(2)
        if best_r is None:
            best_a, best_c, best_r = a, np.broadcast_to(f, im.shape).copy(), r
        else:
            m = r < best_r
            best_a[m], best_c[m], best_r[m] = a[m], f, r[m]
    k = LOGO_PX / 2160
    P = lambda x, y: (x * k, y * k)
    dt, dr, db, dl = P(1079.5, 794.5), P(1484.5, 1199.5), P(1079.5, 1604.5), P(674.5, 1199.5)
    tl, tr, br, bl = P(797, 917), P(1362, 917), P(1362, 1482), P(797, 1482)
    ax, ay, ar_ = 1079.5 * k, 939.5 * k, 520 * k
    arc = [(ax + ar_ * np.cos(a), ay + ar_ * np.sin(a)) for a in np.linspace(np.pi, 2 * np.pi, 160)]
    # closed shapes start and end in the middle of a straight side, never on a corner, so the pen's
    # first touch is a clean dot and no corner waits for the pen to come back to it
    mb = (1079.5 * k, 1759.5 * k)
    arch = [mb, (559.5 * k, 1759.5 * k)] + arc + [(1599.5 * k, 1759.5 * k), mb]
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    def poly(pts, n=400):
        pts = np.array(pts, np.float32)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)])
        u = np.linspace(0, s[-1], n)
        return np.stack([np.interp(u, s, pts[:, 0]), np.interp(u, s, pts[:, 1])], 1)

    def stroke_layer(polys, width):
        """Antialiased strokes (4x supersampled), as an alpha map."""
        ss = 4
        m = Image.new("L", (LOGO_PX * ss, LOGO_PX * ss), 0)
        d = ImageDraw.Draw(m)
        for pts in polys:
            sp = [(x * ss, y * ss) for x, y in pts]
            d.line(sp, fill=255, width=int(round(width * k * ss)), joint="curve")
            r = width * k * ss / 2
            for x, y in sp[:1] + sp[-1:]:
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return np.asarray(m.resize((LOGO_PX, LOGO_PX), Image.LANCZOS), dtype=np.float32) / 255

    # (vertices, start s, duration s, stroke width in the 2160 px original)
    thick = [(arch, 0.08, 0.72, 28), ([mid(tl, tr), tr, br, bl, tl, mid(tl, tr)], 0.55, 0.45, 23),
             ([mid(dt, dr), dr, db, dl, dt, mid(dt, dr)], 0.72, 0.45, 23)]
    thin_l = [([a, b], 1.12, 0.34, 6.5)
              for a, b in [(dt, br), (dt, bl), (dr, tl), (dr, bl), (dl, tr), (dl, br), (db, tr), (db, tl)]]

    def layer_times(group, alpha):
        """For each pixel of the layer, the time the pen gets there (earliest stroke that covers it)."""
        t_on = np.full(alpha.shape, 99.0, np.float32)
        ys, xs = np.nonzero(alpha > 0.01)
        q = np.stack([xs, ys], 1)
        best = np.full(len(q), np.inf)
        near_d, near_t = np.full(len(q), np.inf), np.zeros(len(q))
        for verts, s, d, w in group:
            pth = poly(verts, 900 if len(verts) > 10 else 400)
            # several nearest pen points, so on a closed shape (square, diamond) the corner where the
            # pen starts counts as drawn at the start, not when the pen comes back to it at the end
            dist, idx = cKDTree(pth).query(q, k=6)
            tts = s + d * idx / (len(pth) - 1)
            reach = dist <= w * k / 2 + 1.5
            tt = np.where(reach, tts, np.inf).min(1)
            best = np.minimum(best, tt)
            m = dist[:, 0] < near_d
            near_d[m], near_t[m] = dist[m, 0], tts[m, 0]
        t_on[ys, xs] = np.where(np.isfinite(best), best, near_t)
        return t_on

    # every stroke is its own layer, revealed only by its own pen: thin lines first (underneath), then
    # the arch, the square and the diamond
    layers = []
    for group, col in ((thin_l, thin_c), (thick, gold)):
        rgb = np.broadcast_to(col, im.shape).copy()
        for st in group:
            al = stroke_layer([st[0]], st[3])
            layers.append((rgb, al, layer_times([st], al)))
    # the crescent, from the original, sweeps in around its centre at the end
    cx, cy = 1079.5 * k, 1199.5 * k
    cres = (np.abs(im - ivory_c).sum(2) < 120) & (best_a > 0.02)
    cres = np.asarray(Image.fromarray((cres * 255).astype(np.uint8)).filter(__import__("PIL.ImageFilter").ImageFilter.MaxFilter(3))) > 0
    a_cres = np.where(cres, best_a, 0).astype(np.float32)
    yy, xx = np.mgrid[0:LOGO_PX, 0:LOGO_PX]
    ang = (np.arctan2(yy - cy, xx - cx) + np.pi / 2) % (2 * np.pi)
    layers.append((best_c.copy(), a_cres, (1.38 + 0.30 * ang / (2 * np.pi)).astype(np.float32)))
    return best_c, best_a, layers


LOGO_RGB, LOGO_A, LOGO_LAYERS = logo_reveal()
FIN_PX, FIN_CY = 478, 500                           # the closing screen's smaller logo
FIN_LOGO = logo_reveal(FIN_PX)


def draw_logo_at(frame, t, alpha=1.0, cx=LOGO_CX, cy=LOGO_CY, data=None, px=LOGO_PX):
    """Composite the logo as drawn by time t (s from the drawing's start)."""
    rgb, la, layers = data or (LOGO_RGB, LOGO_A, LOGO_LAYERS)
    x0, y0 = int(cx - px / 2), int(cy - px / 2)
    sl = frame[y0:y0 + px, x0:x0 + px]
    hand = min(1.0, max(0.0, (t - LOGO_DONE) / 0.2))  # drawn strokes -> the original file
    if hand < 1:
        for lrgb, lal, lt in layers:
            on = np.clip((t - lt) / 0.06, 0, 1) * lal * alpha * (1 - hand)
            sl *= (1 - on[..., None])
            sl += lrgb * on[..., None]
    if hand > 0:
        on = la * alpha * hand
        sl *= (1 - on[..., None])
        sl += rgb * on[..., None]


def draw_logo(img, cx, cy, s, a=255):
    """The finished logo onto an RGBA layer (final screen); s = arch width in px."""
    px = int(LOGO_PX * s / 385)
    rgba = np.concatenate([LOGO_RGB, (LOGO_A * a)[..., None]], 2).clip(0, 255).astype(np.uint8)
    logo = Image.fromarray(rgba, "RGBA").resize((px, px), Image.LANCZOS)
    img.alpha_composite(logo, (int(cx - px / 2), int(cy - px / 2)))


# ---------- layers ----------

def intro_layer():
    """Intro text (the logo itself is drawn frame by frame)."""
    img = RL.layer()
    d = ImageDraw.Draw(img)
    RL.draw_label(img, "QUR'AN QUIZ", 1010, RL.GOLD)
    text_center(d, "3 questions", SW / 2, 1070, font(R.F_BODY, 92), RL.IVORY + (255,))
    text_center(d, "How many can you get?", SW / 2, 1200, font(R.F_BODY, 56), RL.MEAL + (255,))
    text_center(d, R.HANDLE, SW / 2, Y_HANDLE, font(R.F_LABEL, 28), RL.MUTED + (255,))
    return img


def header(img, k):
    d = ImageDraw.Draw(img)
    RL.draw_label(img, "QUR'AN QUIZ", Y_TOP, RL.GOLD)
    f = font(R.F_LABEL, 30)
    t = f"{k + 1} / {len(ROUNDS)}"
    tw = f.getlength(t) + 56
    d.rounded_rectangle([(SW - tw) / 2, 296, (SW + tw) / 2, 344], radius=24, outline=RL.GOLD + (255,), width=2)
    text_center(d, t, SW / 2, 304, f, RL.GOLD + (255,))
    text_center(d, R.HANDLE, SW / 2, Y_HANDLE, font(R.F_LABEL, 28), RL.MUTED + (255,))


def question_lines(rk):
    for size in (74, 70, 66, 62):
        lines = RL.en_lines(rk["q"], size, 900)
        if len(lines) <= 3:
            return lines, size


def static_layer(rk, k):
    img = RL.layer()
    header(img, k)
    lines, size = question_lines(rk)
    RL.draw_en(img, lines, size, Y_Q + (260 - len(lines) * RL.en_lh(size)) / 2, RL.IVORY)
    return img


def option_box(d, j, text, state):
    x, y = OPT_X, Y_OPT + j * (OPT_H + OPT_GAP)
    if state == "normal":
        d.rounded_rectangle([x, y, x + OPT_W, y + OPT_H], radius=26, fill=(255, 255, 255, 16), outline=RL.GOLD + (110,), width=2)
        num, col = RL.GOLD, RL.IVORY
    else:
        d.rounded_rectangle([x, y, x + OPT_W, y + OPT_H], radius=26, fill=GREEN + (55,), outline=GREEN + (255,), width=4)
        num, col = GREEN, (236, 246, 238)
        cx, cy = x + OPT_W - 52, y + OPT_H / 2
        d.line([(cx - 16, cy), (cx - 5, cy + 12), (cx + 17, cy - 13)], fill=GREEN + (255,), width=5, joint="curve")
    cx, cy = x + 62, y + OPT_H / 2
    d.ellipse([cx - 32, cy - 32, cx + 32, cy + 32], outline=num + (255,), width=2)
    f = font(R.F_LABEL, 34)
    text_center(d, "ABC"[j], cx, cy - 22, f, num + (255,))
    d.text((x + 128, cy - 33), text, font=font(R.F_BODY, 58), fill=col + (255,))


def options_layer(rk):
    img = RL.layer()
    d = ImageDraw.Draw(img)
    for j, t in enumerate(rk["options"]):
        option_box(d, j, t, "normal")
    d.rounded_rectangle([OPT_X, Y_BAR, OPT_X + OPT_W, Y_BAR + 8], radius=4, fill=(255, 255, 255, 34))
    return img


def wrong_cover(rk):
    img = RL.layer()
    d = ImageDraw.Draw(img)
    for j in range(3):
        if j != rk["answer"]:
            y = Y_OPT + j * (OPT_H + OPT_GAP)
            d.rounded_rectangle([OPT_X - 2, y - 2, OPT_X + OPT_W + 2, y + OPT_H + 2], radius=28, fill=tuple(RL.BG) + (185,))
    return img


def right_layer(rk, y_override=None):
    img = RL.layer()
    d = ImageDraw.Draw(img)
    j = rk["answer"]
    y = Y_OPT + j * (OPT_H + OPT_GAP)
    d.rounded_rectangle([OPT_X - 2, y - 2, OPT_X + OPT_W + 2, y + OPT_H + 2], radius=28, fill=tuple(RL.BG) + (255,))
    option_box(d, j, rk["options"][j], "right")
    return img


def answer_chip(rk):
    """The right answer, small, under the question while the verse is shown."""
    img = RL.layer()
    d = ImageDraw.Draw(img)
    t = rk["options"][rk["answer"]]
    f = font(R.F_BODY, 54)
    tw = f.getlength(t) + 124
    y = 700
    d.rounded_rectangle([(SW - tw) / 2, y, (SW + tw) / 2, y + 96], radius=48, fill=GREEN + (55,), outline=GREEN + (255,), width=3)
    cx = (SW - tw) / 2 + 44
    d.line([(cx - 13, y + 48), (cx - 4, y + 58), (cx + 14, y + 37)], fill=GREEN + (255,), width=5, joint="curve")
    d.text(((SW - tw) / 2 + 82, y + 18), t, font=f, fill=(236, 246, 238, 255))
    return img


def verse_layers(rk):
    words = []
    for a in rk["verses"]:
        words += R._arabic_words(get(f"quran:{int(a[:3])}:{int(a[3:])}")["arabic_display"])
    size = 92
    while True:
        lines = R._wrap(words, 900, lambda s: font(R.F_QURAN, size).getlength(s, direction="rtl", language="ar"))
        if (len(lines) <= 2) or size <= 64:
            break
        size -= 2
    f = font(R.F_QURAN, size)
    lh = RL.ar_lh(size)
    y = V_TOP
    dim = RL.layer()
    RL.draw_ar(dim, lines, size, y, RL.VERSE_DIM)
    gmask = np.zeros((SH, SW, 4), np.uint8)
    per_word, wi = [], 0
    for n, line in enumerate(lines):
        # each line drawn on its own, so a mark hanging below the line above is never cut into a word here
        lit, green = RL.layer(), RL.layer()
        RL.draw_ar(lit, [line], size, y + n * lh, RL.VERSE_ON)
        RL.draw_ar(green, [line], size, y + n * lh, ANSWER_GREEN)
        lit_a, green_a = np.asarray(lit).copy(), np.asarray(green).copy()
        lw = line.split(" ")
        total = f.getlength(line, direction="rtl", language="ar")
        right = (SW + total) / 2
        y0, y1 = int(y + n * lh - lh * 0.6), int(y + (n + 1) * lh + lh * 0.3)
        sp = f.getlength(" ", direction="rtl", language="ar")
        for i in range(len(lw)):
            r_edge = right - (f.getlength(" ".join(lw[:i]), direction="rtl", language="ar") + sp / 2 if i else -8)
            l_edge = right - f.getlength(" ".join(lw[:i + 1]), direction="rtl", language="ar") - (sp / 2 if i < len(lw) - 1 else 8)
            m = np.zeros_like(lit_a)
            xa, xb = max(0, int(l_edge)), min(SW, int(r_edge) + 1)
            m[max(0, y0):min(SH, y1), xa:xb] = lit_a[max(0, y0):min(SH, y1), xa:xb]
            per_word.append(RL._Layer(Image.fromarray(m, "RGBA")))
            if wi in rk["ar_answer"]:                 # the answer word, without an attached verse number
                word = lw[i].split(" ")[0]
                gl = r_edge - f.getlength(word, direction="rtl", language="ar") - 6
                ga = max(0, int(gl))
                gmask[max(0, y0):min(SH, y1), ga:xb] = green_a[max(0, y0):min(SH, y1), ga:xb]
            wi += 1
    assert len(per_word) == len(words)
    rk["green"] = RL._Layer(Image.fromarray(gmask, "RGBA"))
    return RL._Layer(dim), per_word, y + len(lines) * lh


def meaning_layers(rk, y):
    """Meaning (the answer words in gold) and the reference under the verse."""
    import re
    txt = RL.verse_meanings(rk["entry"])[1]
    size = 50
    lines = RL.en_lines(txt, size, 900)
    base, gold = RL.layer(), RL.layer()
    want = [w.lower() for w in rk["highlight"]]
    flat = [re.sub(r"[^\w]", "", w).lower() for w in txt.split(" ")]
    hit = set()
    for i in range(len(flat) - len(want) + 1):
        if flat[i:i + len(want)] == want:
            hit |= set(range(i, i + len(want)))
    assert hit, (txt, want)
    db, dg = ImageDraw.Draw(base), ImageDraw.Draw(gold)
    yy, wi = y + 26, 0
    for line in lines:
        ws = line.split(" ")
        x0 = (SW - R._width_ltr(line, size)) / 2
        for j, w in enumerate(ws):
            x = x0 + (R._width_ltr(" ".join(ws[:j]) + " ", size) if j else 0)
            d, col = (dg, ANSWER_GREEN) if wi in hit else (db, RL.MEAL)
            for t_, f in R._runs(w, size):
                d.text((x, yy), t_, font=f, fill=col + (255,))
                x += f.getlength(t_)
            wi += 1
        yy += RL.en_lh(size)
    ref = get(rk["entry"])["reference"]
    text_center(db, ref, SW / 2, yy + 26, font(R.F_LABEL, 36), RL.GOLD + (255,))
    return RL._Layer(base), RL._Layer(gold)


def final_layer():
    img = RL.layer()
    d = ImageDraw.Draw(img)
    f = font(R.F_LABEL, 46)
    t = "YOUR SCORE:  ? / 3"
    tw = f.getlength(t) + 84
    y = 760
    d.rounded_rectangle([(SW - tw) / 2, y, (SW + tw) / 2, y + 82], radius=41, fill=RL.GOLD + (255,))
    text_center(d, t, SW / 2, y + 14, f, (20, 34, 28, 255))
    text_center(d, "Comment your score below", SW / 2, y + 130, font(R.F_BODY, 50), RL.IVORY + (255,))
    text_center(d, "Send this to a friend and compare scores", SW / 2, y + 205, font(R.F_BODY, 42), RL.MEAL + (255,))
    RL.draw_label(img, "ANSWERS", y + 320, RL.GOLD)
    for i, rk in enumerate(ROUNDS):
        yy = y + 390 + i * 96
        t = f"{i + 1}.  {rk['options'][rk['answer']]}"
        text_center(d, t, SW / 2, yy, font(R.F_BODY, 46), (236, 246, 238, 255))
    text_center(d, R.HANDLE, SW / 2, Y_HANDLE, font(R.F_LABEL, 28), RL.MUTED + (255,))
    return img


# ---------- audio and timeline ----------

def pcm_of(ayah):
    tmp = OUT / "seg.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(AUD / "audio" / f"{ayah}.mp3"),
                    "-ac", "2", "-ar", str(SR), str(tmp)], check=True)
    with wave.open(str(tmp)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32)


def word_starts(ayah, n):
    st = [None] * n
    for a, b, s, e in ALIGN[ayah]:
        for k in range(a, b):
            st[k] = (s + (e - s) * (k - a) / (b - a)) / 1000
    for k in range(n):
        if st[k] is None:
            st[k] = (st[k - 1] + 0.3) if k else 0.0
    return st


def build():
    t, parts = INTRO, []
    for k, rk in enumerate(ROUNDS):
        rk["static"] = RL._Layer(static_layer(rk, k))
        rk["opts"] = RL._Layer(options_layer(rk))
        rk["wrong"], rk["right"] = RL._Layer(wrong_cover(rk)), RL._Layer(right_layer(rk))
        rk["chip"] = RL._Layer(answer_chip(rk))
        rk["dim"], rk["lit"], vy = verse_layers(rk)
        rk["mbase"], rk["mgold"] = meaning_layers(rk, vy)
        rk["t0"] = t
        rk["think0"] = t + 0.3
        rk["reveal"] = rk["think0"] + THINK
        rk["verse0"] = rk["reveal"] + REVEAL          # options give way to the verse
        rk["rec0"] = rk["verse0"] + SHOWV
        starts, off, pcms = [], 0.0, []
        for a in rk["verses"]:
            pcm = pcm_of(a)
            n = len(R._arabic_words(get(f"quran:{int(a[:3])}:{int(a[3:])}")["arabic_display"]))
            starts += [off + s for s in word_starts(a, n)]
            off += len(pcm) / SR
            pcms.append(pcm)
        pcm = np.concatenate(pcms)
        rk["word_t"] = [rk["rec0"] + s for s in starts]
        rk["rec_end"] = rk["rec0"] + len(pcm) / SR
        rk["t1"] = rk["rec_end"] + HOLD
        parts.append((rk["rec0"], pcm))
        t = rk["t1"]
    end = t + FINAL
    total = np.zeros((int(end * SR) + SR, 2), np.float32)
    for t0, pcm in parts:
        i = int(t0 * SR)
        total[i:i + len(pcm)] += pcm
    peak = np.abs(total).max() or 1
    total *= min(1.0, 0.89 * 32767 / peak)
    rec_peak = 0.89 * 32767

    def add(t0, sig):
        i = int(t0 * SR)
        n = min(len(sig), len(total) - i)
        total[i:i + n] += sig[:n, None] * rec_peak

    add(0.0, sfx_shimmer())
    for rk in ROUNDS:
        for n in range(int(THINK * 2)):
            add(rk["think0"] + n * 0.5, sfx_tick(n % 2))
        add(rk["reveal"], sfx_chime())
    add(ROUNDS[-1]["t1"] - XF, sfx_close())
    with wave.open(str(OUT / "trivia_audio.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(total[:int(end * SR)].clip(-32768, 32767).astype(np.int16).tobytes())
    return end


def _env(n, attack, decay):
    tt = np.arange(n) / SR
    return np.minimum(1, tt / attack) * np.exp(-tt / decay)


def sfx_shimmer():
    """Soft rising air, then a short sparkle of high bell tones as the logo completes."""
    n = int(3.2 * SR)
    tt = np.arange(n) / SR
    rng = np.random.default_rng(7)
    air = np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode="same")
    air = np.diff(np.concatenate([[0], air]))           # brighter noise
    air *= np.clip(tt / 1.4, 0, 1) ** 2 * np.exp(-np.clip(tt - 1.5, 0, None) / 0.25) * 0.5
    out = air
    for k, f in enumerate([1318.5, 1760.0, 2093.0, 2637.0, 3136.0]):
        st = 1.35 + k * 0.07
        m = tt >= st
        u = tt[m] - st
        out[m] += 0.10 * np.sin(2 * np.pi * f * u) * np.exp(-u / 0.55) * np.minimum(1, u / 0.004)
        out[m] += 0.03 * np.sin(2 * np.pi * 2 * f * u) * np.exp(-u / 0.3)
    for dly, g in [(0.09, 0.35), (0.17, 0.2), (0.29, 0.1)]:   # a little room
        d = int(dly * SR)
        out[d:] += g * out[:-d].copy()
    return out * 0.58


def sfx_tick(tock):
    n = int(0.06 * SR)
    tt = np.arange(n) / SR
    f = 1500 if tock else 2100
    rng = np.random.default_rng(3 + tock)
    s = (np.sin(2 * np.pi * f * tt) * 0.6 + rng.standard_normal(n) * 0.4) * np.exp(-tt / 0.008)
    return s * 0.06


def sfx_close():
    """Closing: a soft rising four-note bell arpeggio with a long tail."""
    n = int(2.6 * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        st = k * 0.13
        m = tt >= st
        u = tt[m] - st
        out[m] += (np.sin(2 * np.pi * f * u) + 0.25 * np.sin(2 * np.pi * 2 * f * u) + 0.08 * np.sin(2 * np.pi * 3 * f * u))             * np.exp(-u / 0.9) * np.minimum(1, u / 0.01)
    for dly, g in [(0.11, 0.3), (0.23, 0.15)]:
        d = int(dly * SR)
        out[d:] += g * out[:-d].copy()
    return out * 0.09


def sfx_chime():
    """A two-note 'correct' chime."""
    n = int(1.0 * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for st, f in [(0.0, 1046.5), (0.09, 1568.0)]:
        m = tt >= st
        u = tt[m] - st
        out[m] += (np.sin(2 * np.pi * f * u) + 0.3 * np.sin(2 * np.pi * 2 * f * u)) * np.exp(-u / 0.35) * np.minimum(1, u / 0.003)
    return out * 0.14


def ramp(t, a, d=0.3):
    return min(1.0, max(0.0, (t - a) / d))


def draw_round(frame, rk, t, a=1.0):
    rk["static"].over(frame, a)
    v = ramp(t, rk["verse0"], 0.4)                    # 0 = options, 1 = verse
    if v < 1:
        k = a * (1 - v)
        rk["opts"].over(frame, k)
        share = min(1.0, max(0.0, (t - rk["think0"]) / THINK))
        r = ramp(t, rk["reveal"], 0.25)
        if share > 0 and r < 1:
            x1 = OPT_X + int(OPT_W * share)
            kk = k * (1 - r)
            frame[Y_BAR:Y_BAR + 8, OPT_X:x1] = frame[Y_BAR:Y_BAR + 8, OPT_X:x1] * (1 - kk) + np.array(RL.GOLD, np.float32) * kk
        if r > 0:
            rk["wrong"].over(frame, r * k)
            rk["right"].over(frame, r * k)
    if v > 0:
        k = a * v
        rk["chip"].over(frame, k)
        rk["dim"].over(frame, k)
        for s, lw in zip(rk["word_t"], rk["lit"]):
            on = 1.0 if t >= rk["rec_end"] else min(1.0, max(0.0, (t - s) / 0.12))
            if on > 0:
                lw.over(frame, on * k)
        rk["green"].over(frame, k)                    # the answer word stays light green throughout
        rk["mbase"].over(frame, k)
        rk["mgold"].over(frame, k)


INTRO_L = RL._Layer(intro_layer())
FINAL_L = RL._Layer(final_layer())


def frames(end):
    bg = RL.background()
    last = ROUNDS[-1]
    for i in range(int(round(end * FPS))):
        t = i / FPS
        frame = RL._ground(bg, t, end)
        if t < INTRO:
            y = ramp(t, INTRO - XF, XF)
            draw_logo_at(frame, t, 1 - y)
            INTRO_L.over(frame, ramp(t, 1.55, 0.4) * (1 - y))
            if y > 0:
                draw_round(frame, ROUNDS[0], ROUNDS[0]["t0"], y)
        elif t >= last["t1"] - XF:
            x = ramp(t, last["t1"] - XF, XF)
            if x < 1:
                draw_round(frame, last, t, 1 - x)
            draw_logo_at(frame, t - (last["t1"] - XF) - 0.15, 1.0, SW / 2, FIN_CY, FIN_LOGO, FIN_PX)
            FINAL_L.over(frame, x)
        else:
            k = max(j for j, rk in enumerate(ROUNDS) if t >= rk["t0"])
            rk, nxt = ROUNDS[k], (ROUNDS[k + 1] if k + 1 < len(ROUNDS) else None)
            if nxt and t > nxt["t0"] - XF:
                x = (t - (nxt["t0"] - XF)) / XF
                draw_round(frame, rk, t, 1 - x)
                draw_round(frame, nxt, nxt["t0"], x)
            else:
                draw_round(frame, rk, t)
        yield t, frame.clip(0, 255).astype(np.uint8)


def main():
    end = build()
    video = OUT / "trivia.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}",
           "-r", str(FPS), "-i", "-", "-i", str(OUT / "trivia_audio.wav"), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{end:.2f}", "-movflags", "+faststart", str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    marks = {0.4: "intro1", 0.8: "intro2", 1.2: "intro3", 2.2: "intro4"}
    for rk in ROUNDS:
        marks[round(rk["think0"] + 2.5, 2)] = "think"
        marks[round(rk["reveal"] + 0.5, 2)] = "reveal"
        marks[round((rk["rec0"] + rk["rec_end"]) / 2, 2)] = "verse"
        marks[round(rk["t1"] - 0.6, 2)] = "hold"
    marks[round(ROUNDS[-1]["t1"] + 0.6, 2)] = "fin1"
    marks[round(ROUNDS[-1]["t1"] + 1.2, 2)] = "fin2"
    marks[round(end - 0.1, 2)] = "end"
    for t, f in frames(end):
        proc.stdin.write(f.tobytes())
        for m, name in list(marks.items()):
            if abs(t - m) < 0.5 / FPS:
                Image.fromarray(f).resize((432, 768)).save(OUT / f"t_{m:05.2f}_{name}.jpg", quality=85)
                marks.pop(m)
    proc.stdin.close()
    proc.wait()
    print("ok", video, f"{end:.1f}s")


if __name__ == "__main__":
    main()
