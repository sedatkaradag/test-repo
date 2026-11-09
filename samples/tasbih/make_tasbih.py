"""Not part of the publishing pipeline: "99 Names of Allah" tasbih Reel.

    python3 make_tasbih.py <repo> <out_dir> [seconds_per_name]

A ring of 99 beads; one name every 1.5 s: its bead lights, the Arabic in the middle, the transliteration
and meaning under the ring, the count and a bar. Intro: Bismillah written into the ring (right to left). End: Alhamdulillah.
Names, transliterations and meanings come only from names_tirmidhi_3507.json (see its "source").
Sounds (made here, no music): a soft shimmer, a wooden bead click on every name, a bell at 33 and 66,
a rising bell arpeggio at the end.
"""
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
PER = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
sys.path.insert(0, str(REPO / "scripts"))
import reels as RL  # noqa: E402
import render as R  # noqa: E402
from content import get  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
HERE = REPO / "samples" / "tasbih"
NAMES = json.loads((HERE / "names_tirmidhi_3507.json").read_text())["names"]
assert len(NAMES) == 99 and [n["n"] for n in NAMES] == list(range(1, 100))

SW, SH, FPS, SR = RL.SW, RL.SH, RL.FPS, 44100
INTRO, OUTRO = 3.0, 4.5
T0 = INTRO
TE = T0 + 99 * PER
END = TE + OUTRO
CX, CY, RING = SW / 2, 800, 330          # bead ring
INNER = 282                               # inner disc
Y_TR, Y_MEAN = 1180, 1290                 # transliteration, meaning
Y_BAR = 1470
BAR_X0, BAR_X1 = 140, SW - 140
Y_HANDLE = 1535
GOLD, IVORY, MEAL, MUTED = RL.GOLD, RL.IVORY, RL.MEAL, RL.MUTED
LIT = (226, 190, 112)
F_AR = REPO / "assets" / "fonts" / "Amiri-Bold.ttf"


def font(path, size):
    return R._font(path, size)


def text_center(d, text, cx, y, f, color):
    d.text((cx - f.getlength(text) / 2, y), text, font=f, fill=color)


def ramp(t, a, d=0.3):
    return min(1.0, max(0.0, (t - a) / d))


# ---------- the ring ----------
# 99 beads with a small marker after the 33rd and the 66th, an open gap at the top for the imame.
UNIT = 360 / 104
SLOTS = []                                 # (angle, kind) kind: bead number 1..99 or "sep"
k = 0
for j in range(101):
    if j in (33, 67):
        SLOTS.append((-90 + (j + 2) * UNIT, "sep"))
    else:
        k += 1
        SLOTS.append((-90 + (j + 2) * UNIT, k))
BEADS = {kind: a for a, kind in SLOTS if kind != "sep"}
SEPS = [a for a, kind in SLOTS if kind == "sep"]
BEAD_R = 9.5


def pos(angle, r=RING):
    a = math.radians(angle)
    return CX + r * math.cos(a), CY + r * math.sin(a)


def ring_base():
    """Frame furniture that never changes: header, discs, the string, dim beads, separators, imame."""
    s = 2                                   # drawn at 2x and scaled down for smooth edges
    big = Image.new("RGBA", (SW * s, SH * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.ellipse([(CX - INNER) * s, (CY - INNER) * s, (CX + INNER) * s, (CY + INNER) * s], fill=(2, 10, 9, 110))
    d.ellipse([(CX - INNER - 8) * s, (CY - INNER - 8) * s, (CX + INNER + 8) * s, (CY + INNER + 8) * s],
              outline=GOLD + (60,), width=2 * s)
    d.ellipse([(CX - RING) * s, (CY - RING) * s, (CX + RING) * s, (CY + RING) * s], outline=GOLD + (45,), width=2 * s)
    for kind, a in BEADS.items():
        x, y = pos(a)
        d.ellipse([(x - BEAD_R) * s, (y - BEAD_R) * s, (x + BEAD_R) * s, (y + BEAD_R) * s],
                  fill=(60, 58, 40, 255), outline=GOLD + (70,), width=s)
    for a in SEPS:
        x, y = pos(a)
        d.ellipse([(x - 5) * s, (y - 5) * s, (x + 5) * s, (y + 5) * s], fill=GOLD + (150,))
    # imame: a longer bead at the top with a short tassel
    x, y = pos(-90)
    d.rounded_rectangle([(x - 8) * s, (y - 30) * s, (x + 8) * s, (y + 4) * s], radius=8 * s, fill=GOLD + (210,))
    d.ellipse([(x - 6) * s, (y - 44) * s, (x + 6) * s, (y - 32) * s], fill=GOLD + (210,))
    for dx in (-6, -2, 2, 6):
        d.line([(x * s, (y - 40) * s), ((x + dx) * s, (y - 64) * s)], fill=GOLD + (150,), width=s)
    img = big.resize((SW, SH), Image.LANCZOS)
    RL.draw_label(img, "ASMA UL HUSNA", RL.TOP_LABEL, GOLD)
    dd = ImageDraw.Draw(img)
    text_center(dd, "The 99 Names of Allah", SW / 2, RL.TOP_LABEL + 46, font(R.F_BODY, 44), MEAL + (255,))
    text_center(dd, R.HANDLE, SW / 2, Y_HANDLE + 30, font(R.F_LABEL, 27), MUTED + (255,))
    return RL._Layer(img)


def bead_sprite(r, glow):
    """A lit bead (and its soft glow) as a small RGBA patch."""
    s = 64
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    if glow:
        g = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([c - 20, c - 20, c + 20, c + 20], fill=LIT + (150,))
        img = g.filter(ImageFilter.GaussianBlur(7))
        return np.asarray(img, np.float32)
    big = Image.new("RGBA", (s * 4, s * 4), (0, 0, 0, 0))
    db = ImageDraw.Draw(big)
    db.ellipse([(c - r) * 4, (c - r) * 4, (c + r) * 4, (c + r) * 4], fill=LIT + (255,))
    db.ellipse([(c - r * 0.55 - 1.5) * 4, (c - r * 0.55 - 2.5) * 4, (c - r * 0.55 + 4) * 4, (c - r * 0.55 + 3) * 4],
               fill=(255, 240, 200, 180))
    return np.asarray(big.resize((s, s), Image.LANCZOS), np.float32)


LIT_SPR = bead_sprite(BEAD_R + 0.5, False)
GLOW_SPR = bead_sprite(0, True)


def put(frame, spr, x, y, k=1.0):
    s = spr.shape[0]
    x0, y0 = int(round(x - s / 2)), int(round(y - s / 2))
    sl = frame[y0:y0 + s, x0:x0 + s]
    a = spr[..., 3:4] / 255 * k
    sl *= (1 - a)
    sl += spr[..., :3] * a


# ---------- text layers ----------

def name_layer(nm):
    img = RL.layer()
    d = ImageDraw.Draw(img)
    words = nm["ar"].split(" ")
    lines = [nm["ar"]]
    size = 150
    fit = lambda ls, sz: max(font(F_AR, sz).getlength(l, direction="rtl", language="ar") for l in ls) <= 2 * INNER - 90
    while not fit(lines, size):
        size -= 4
    if size < 104 and len(words) > 2:                  # a long phrase reads better on two lines
        lines, size = [" ".join(words[:2]), " ".join(words[2:])], 120
        while not fit(lines, size):
            size -= 4
    f = font(F_AR, size)
    lh = size * 1.32
    for i, line in enumerate(lines):
        w = f.getlength(line, direction="rtl", language="ar")
        bb = d.textbbox((0, 0), line, font=f, direction="rtl", language="ar")
        y = CY - 30 - 8 * (len(lines) - 1) + (i - (len(lines) - 1) / 2) * lh - (bb[1] + bb[3]) / 2
        d.text(((SW - w) / 2, y), line, font=f, fill=LIT + (255,), direction="rtl", language="ar")
    text_center(d, str(nm["n"]), SW / 2, CY + 128, font(R.F_LABEL, 30), MUTED + (255,))
    size = 82
    while R._width_ltr(nm["translit"], size) > 900:
        size -= 4
    RL.draw_en(img, [nm["translit"]], size, Y_TR, IVORY)
    size = 46
    lines = RL.en_lines(nm["meaning"], size, 880)
    while len(lines) > 2:
        size -= 2
        lines = RL.en_lines(nm["meaning"], size, 880)
    RL.draw_en(img, lines, size, Y_MEAN, MEAL)
    return img


def intro_layer():
    img = RL.layer()
    RL.draw_en(img, ["Say each name with us"], 70, Y_TR, IVORY)
    RL.draw_en(img, ["99 names  ·  one tasbih"], 46, Y_MEAN, MEAL)
    return RL._Layer(img)


def outro_layer():
    img = RL.layer()
    d = ImageDraw.Draw(img)
    words = R._arabic_words(get("quran:1:2")["arabic_display"])[:2]   # "al-hamdu lillahi", from our Qur'an text
    ar = " ".join(words)
    f = font(R.F_QURAN, 112)
    w = f.getlength(ar, direction="rtl", language="ar")
    bb = d.textbbox((0, 0), ar, font=f, direction="rtl", language="ar")
    d.text(((SW - w) / 2, CY - 10 - (bb[1] + bb[3]) / 2), ar, font=f, fill=LIT + (255,), direction="rtl", language="ar")
    RL.draw_en(img, ["Alhamdulillah"], 82, Y_TR, IVORY)
    RL.draw_en(img, ["Save this and complete a tasbih every day"], 44, Y_MEAN, MEAL)
    RL.draw_en(img, ["Send it to someone you love"], 40, Y_MEAN + 62, MUTED)
    return RL._Layer(img)


def counter(frame, n, share, k=1.0):
    """'DHIKR' label, n / 99 and the bar."""
    key = (n, round(k, 2))
    if key not in counter.cache:
        img = RL.layer()
        d = ImageDraw.Draw(img)
        f = font(R.F_LABEL, 26)
        d.text((BAR_X0, Y_BAR - 42), "D H I K R", font=f, fill=GOLD + (255,))
        t = f"{n} / 99"
        d.text((BAR_X1 - f.getlength(t), Y_BAR - 42), t, font=f, fill=IVORY + (255,))
        counter.cache = {key: RL._Layer(img)}
    counter.cache[key].over(frame, k)
    frame[Y_BAR:Y_BAR + 6, BAR_X0:BAR_X1] = frame[Y_BAR:Y_BAR + 6, BAR_X0:BAR_X1] * 0.75 + np.array(MUTED, np.float32) * 0.25 * k
    x1 = BAR_X0 + int((BAR_X1 - BAR_X0) * share)
    frame[Y_BAR:Y_BAR + 6, BAR_X0:x1] = frame[Y_BAR:Y_BAR + 6, BAR_X0:x1] * (1 - k) + np.array(LIT, np.float32) * k


counter.cache = {}


# ---------- Bismillah (our Qur'an text, 1:1 without its verse number) ----------

def bismillah():
    """The Bismillah on two lines (bismi-llahi / ar-rahmani r-rahim) as RGBA patches with their places."""
    words = R._arabic_words(get("quran:1:1")["arabic_display"])
    words[-1] = words[-1].split("\xa0")[0]
    lines = [" ".join(words[:2]), " ".join(words[2:])]
    size = 92
    f = font(R.F_QURAN, size)
    while max(f.getlength(l, direction="rtl", language="ar") for l in lines) > 2 * INNER - 110:
        size -= 2
        f = font(R.F_QURAN, size)
    lh = size * 1.55
    out = []
    for i, line in enumerate(lines):
        img = RL.layer()
        d = ImageDraw.Draw(img)
        w = f.getlength(line, direction="rtl", language="ar")
        bb = d.textbbox((0, 0), line, font=f, direction="rtl", language="ar")
        y = CY - 20 + (i - 0.5) * lh - (bb[1] + bb[3]) / 2
        d.text(((SW - w) / 2, y), line, font=f, fill=LIT + (255,), direction="rtl", language="ar")
        a = np.asarray(img, np.float32)
        ys = np.nonzero(a[..., 3].max(1) > 0)[0]
        xs = np.nonzero(a[..., 3].max(0) > 0)[0]
        y0, y1, x0, x1 = ys[0] - 4, ys[-1] + 5, xs[0] - 4, xs[-1] + 5
        out.append((a[y0:y1, x0:x1], int(y0), int(x0)))
    return out


BISM = bismillah()
BISM_T = [(0.35, 1.05), (1.05, 1.85)]   # each line is revealed right to left in turn


def bismillah_at(frame, t, k):
    if k <= 0:
        return
    for (spr, y0, x0), (ta, tb) in zip(BISM, BISM_T):
        p = min(1.0, max(0.0, (t - ta) / (tb - ta)))
        if p <= 0:
            continue
        p = p * p * (3 - 2 * p)
        h, w = spr.shape[:2]
        edge = w * (1 - p)               # columns right of the edge show, with a soft 40 px edge
        m = np.clip((np.arange(w, dtype=np.float32) - edge + 40) / 40, 0, 1) if p < 1 else np.ones(w, np.float32)
        a = spr[..., 3:4] / 255 * m[None, :, None] * k
        sl = frame[y0:y0 + h, x0:x0 + w]
        sl *= (1 - a)
        sl += spr[..., :3] * a


# ---------- sound ----------

def sfx_click(seed):
    """A soft wooden bead click: a short knock plus a faint second tap."""
    n = int(0.12 * SR)
    tt = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    noise = np.convolve(rng.standard_normal(n), [1, -0.9], mode="same")
    knock = (0.7 * np.sin(2 * np.pi * 1850 * tt) + 0.5 * np.sin(2 * np.pi * 2900 * tt)) * np.exp(-tt / 0.006)
    body = 0.5 * np.sin(2 * np.pi * 420 * tt) * np.exp(-tt / 0.018)
    s = (knock + body + 0.35 * noise * np.exp(-tt / 0.004))
    d = int(0.022 * SR)
    s[d:] += 0.35 * s[:-d].copy()
    return s * 0.13


def sfx_bell(f0=880.0):
    n = int(2.4 * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for m, g, dec in [(1, 1.0, 0.9), (2.0, 0.35, 0.5), (2.76, 0.18, 0.35), (5.4, 0.06, 0.2)]:
        out += g * np.sin(2 * np.pi * f0 * m * tt) * np.exp(-tt / dec)
    out *= np.minimum(1, tt / 0.004)
    for dly, g in [(0.11, 0.25), (0.23, 0.12)]:
        d = int(dly * SR)
        out[d:] += g * out[:-d].copy()
    return out * 0.10


def sfx_shimmer():
    n = int(3.0 * SR)
    tt = np.arange(n) / SR
    rng = np.random.default_rng(7)
    air = np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode="same")
    air = np.diff(np.concatenate([[0], air]))
    air *= np.clip(tt / 1.4, 0, 1) ** 2 * np.exp(-np.clip(tt - 1.5, 0, None) / 0.25) * 0.5
    out = air
    for k, f in enumerate([1318.5, 1760.0, 2093.0, 2637.0, 3136.0]):
        st = 1.35 + k * 0.07
        m = tt >= st
        u = tt[m] - st
        out[m] += 0.10 * np.sin(2 * np.pi * f * u) * np.exp(-u / 0.55) * np.minimum(1, u / 0.004)
    for dly, g in [(0.09, 0.35), (0.17, 0.2), (0.29, 0.1)]:
        d = int(dly * SR)
        out[d:] += g * out[:-d].copy()
    return out * 0.58


def sfx_close():
    n = int(3.2 * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        st = k * 0.16
        m = tt >= st
        u = tt[m] - st
        out[m] += (np.sin(2 * np.pi * f * u) + 0.25 * np.sin(2 * np.pi * 2 * f * u)) * np.exp(-u / 1.1) * np.minimum(1, u / 0.01)
    for dly, g in [(0.11, 0.3), (0.23, 0.15)]:
        d = int(dly * SR)
        out[d:] += g * out[:-d].copy()
    return out * 0.10


def audio():
    total = np.zeros(int((END + 1) * SR))

    def add(t0, sig):
        i = int(t0 * SR)
        n = min(len(sig), len(total) - i)
        total[i:i + n] += sig[:n]

    add(0.0, sfx_shimmer())
    for i in range(99):
        add(T0 + i * PER, sfx_click(i))
        if i + 1 in (33, 66):
            add(T0 + i * PER + 0.05, 1.6 * sfx_bell(880.0))
    add(TE + 0.05, sfx_close())
    pcm = (total[:int(END * SR)] * 0.89 * 1.6 * 32767)   # about +4 dB over the parts' own levels
    st = np.stack([pcm, pcm], 1).clip(-32768, 32767).astype(np.int16)
    with wave.open(str(OUT / "tasbih_audio.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


# ---------- frames ----------

def frames():
    bg = RL.background()
    base = ring_base()
    intro, outro = intro_layer(), outro_layer()
    names = {}
    for fi in range(int(round(END * FPS))):
        t = fi / FPS
        frame = RL._ground(bg, t, END)
        base.over(frame, ramp(t, 0.0, 0.5))
        cur = int((t - T0) // PER) if t >= T0 else -1          # index of the name on screen
        cur = min(cur, 98)
        lit = cur + 1 if t < TE else 99
        for b in range(1, lit + 1):
            x, y = pos(BEADS[b])
            put(frame, LIT_SPR, x, y)
        if 0 <= cur and t < TE + 1.2:                            # the newest bead glows, then settles
            ts = T0 + cur * PER
            x, y = pos(BEADS[cur + 1])
            put(frame, GLOW_SPR, x, y, max(0.0, 1 - (t - ts) / 0.7))
        if t >= TE:                                              # the whole ring breathes once
            g = math.sin(min(1.0, (t - TE) / 1.6) * math.pi) * 0.55
            if g > 0.01:
                for b in range(1, 100, 2):
                    x, y = pos(BEADS[b])
                    put(frame, GLOW_SPR, x, y, g)
        if t < T0:
            a = 1 - ramp(t, T0 - 0.35, 0.35)
            bismillah_at(frame, t, a)
            intro.over(frame, ramp(t, 1.4, 0.4) * a)
            counter(frame, 0, 0.0, ramp(t, 0.3, 0.4))
        elif t < TE:
            ts = T0 + cur * PER
            if cur not in names:
                names.clear() if len(names) > 3 else None
                names[cur] = RL._Layer(name_layer(NAMES[cur]))
            kin = ramp(t, ts, 0.18)
            kout = 1 - ramp(t, ts + PER - 0.12, 0.12) if cur < 98 else 1 - ramp(t, TE - 0.05, 0.3)
            names[cur].over(frame, kin * kout)
            share = (cur + ramp(t, ts, 0.25)) / 99
            counter(frame, cur + 1, share)
        else:
            if t < TE + 0.3:
                names.get(98) and names[98].over(frame, 1 - ramp(t, TE - 0.05, 0.3))
            outro.over(frame, ramp(t, TE + 0.25, 0.5))
            counter(frame, 99, 1.0)
        yield t, frame.clip(0, 255).astype(np.uint8)


def main():
    audio()
    video = OUT / "tasbih.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}",
           "-r", str(FPS), "-i", "-", "-i", str(OUT / "tasbih_audio.wav"), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{END:.2f}", "-movflags", "+faststart", str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    marks = {round(x, 2) for x in (0.5, 1.2, 2.2, 2.9, END - 2.5, END - 0.1)}
    marks |= {round(T0 + i * PER + PER * 0.55, 2) for i in range(99)}     # one still per name
    (OUT / "frames").mkdir(exist_ok=True)
    for t, f in frames():
        proc.stdin.write(f.tobytes())
        for m in list(marks):
            if abs(t - m) < 0.5 / FPS:
                Image.fromarray(f).resize((540, 960)).save(OUT / "frames" / f"f_{m:06.2f}.jpg", quality=85)
                marks.discard(m)
    proc.stdin.close()
    proc.wait()
    print("ok", video, f"{END:.1f}s")


if __name__ == "__main__":
    main()
