"""Sample (hand-made): the v3 verse Reel, lit WORD BY WORD with the recitation.

Each Arabic word is dim until it is recited, the word being recited is the brightest (with a soft
glow), and words already recited stay gold. The meaning lights with it: each Arabic word has the
English words it stands for (`MAP`, layout only: the text is not changed). Where the reciter goes
back and reads words again, they light again in that order (`EVENTS`).

    python3 samples/word_reel/make_word_reel.py <set.json> <caption.txt> <recitation.mp3> <out.mp4>

set.json: {"entry": "quran:31:14", "map": [[0,1,2], ...], "events": [[word, start_ms, end_ms], ...]}
  map[k]    = English word numbers (of the meaning as shown, split on spaces) for Arabic word k
  events    = every word as it is heard, in order, repeats included
Layout, colours, hook, slogan, closing line and progress line are the system template's (scripts/reels.py).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import reels as RL  # noqa: E402
import render as R  # noqa: E402

SET, CAPTION, MP3, OUT = (Path(a) for a in sys.argv[1:5])
S = json.loads(SET.read_text(encoding="utf-8"))
L = RL.plan(S["entry"], CAPTION.read_text(encoding="utf-8"))
assert L.get("template") == "v3" and len(L["verses"]) == 1, "one-verse v3 plans only"
assert not RL.issues(L), RL.issues(L)
SW, SH, FPS = RL.SW, RL.SH, RL.FPS

HOT_AR = (255, 244, 214)      # the word being recited: warm white
HOT_EN = (246, 214, 140)      # its meaning: bright gold
READ_AR = (188, 158, 98)      # words already recited: a calmer gold, so the current word stands out
RISE, FALL = 0.20, 0.50       # seconds into the bright state and back (eased)
BEHIND = False   # owner, 13 Nov: no light patch behind the word (it read as a band); glow on the letters only


def soft_light(img, box, pad, alpha, blur):
    """A soft gold light behind a word: a rounded patch, blurred so it has no edge."""
    x0, y0, x1, y1 = box
    patch = Image.new("RGBA", img.size, (0, 0, 0, 0))
    r = (y1 - y0 + 2 * pad[1]) / 2
    ImageDraw.Draw(patch).rounded_rectangle((x0 - pad[0], y0 - pad[1], x1 + pad[0], y1 + pad[1]), radius=r,
                                            fill=(214, 178, 104, alpha))
    img.alpha_composite(patch.filter(ImageFilter.GaussianBlur(blur)))


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)

# ---------- Arabic words, each on its own layers ----------
v = L["verses"][0]
size = L["arabic_size"]
font = R._font(R.F_QURAN, size)
tokens = [t for line in v["lines"] for t in line.split(" ")]
assert len(tokens) == len(S["map"]), (len(tokens), len(S["map"]))


def blank():
    return Image.new("RGBA", (SW, SH), (0, 0, 0, 0))


ar_dim, ar_on, ar_hot = blank(), [], []
y, k = v["y"], 0
d_dim = ImageDraw.Draw(ar_dim)
for line in v["lines"]:
    words = line.split(" ")
    w_line = font.getlength(line, direction="rtl", language="ar")
    right = (SW + w_line) / 2
    space = font.getlength(" ", direction="rtl", language="ar")
    x_r = right
    for wd in words:
        w = font.getlength(wd, direction="rtl", language="ar")
        pos = (x_r - w, y)
        d_dim.text(pos, wd, font=font, fill=RL.VERSE_DIM + (255,), direction="rtl", language="ar")
        on = blank(); ImageDraw.Draw(on).text(pos, wd, font=font, fill=READ_AR + (255,), direction="rtl", language="ar")
        box = ImageDraw.Draw(on).textbbox(pos, wd, font=font, direction="rtl", language="ar")
        src = blank(); ImageDraw.Draw(src).text(pos, wd, font=font, fill=(255, 214, 130, 255), direction="rtl", language="ar")
        hot = blank()
        hot.alpha_composite(src.filter(ImageFilter.GaussianBlur(22)))   # wide glow
        hot.alpha_composite(src.filter(ImageFilter.GaussianBlur(7)))    # close glow
        ImageDraw.Draw(hot).text(pos, wd, font=font, fill=HOT_AR + (255,), direction="rtl", language="ar")
        ar_on.append(on); ar_hot.append(hot)
        x_r -= w + space
        k += 1
    y += RL.ar_lh(size)

# ---------- English words ----------
msize = L["meal_size"]
en_dim, en_on, en_hot = blank(), [], []
dd = ImageDraw.Draw(en_dim)
y, n = L["meal_y"], 0
for line in L["full_lines"]:
    words = line.split(" ")
    x0 = (SW - R._width_ltr(line, msize)) / 2
    for j, word in enumerate(words):
        x = x0 + (R._width_ltr(" ".join(words[:j]) + " ", msize) if j else 0)
        on, hot = blank(), blank()
        wpx = sum(f.getlength(t_) for t_, f in R._runs(word.rstrip(".,"), msize))
        asc, desc = R._runs(word, msize)[0][1].getmetrics()
        for img, col in ((en_dim, RL.MEAL_DIM), (on, RL.MEAL), (hot, HOT_EN)):
            xx, d = x, ImageDraw.Draw(img)
            for t_, f in R._runs(word, msize):
                d.text((xx, y), t_, font=f, fill=col + (255,))
                xx += f.getlength(t_)
        en_on.append(on); en_hot.append(hot)
        n += 1
    y += RL.en_lh(msize)
assert sorted(j for g in S["map"] for j in g) == list(range(n)), "map must use every English word once"

# ---------- timing ----------
EV = [(w, a / 1000, b / 1000) for w, a, b in S["events"]]
assert all(0 <= w < len(tokens) for w, _, _ in EV)
assert all(EV[i][1] <= EV[i + 1][1] for i in range(len(EV) - 1)), "events must be in order"
assert {w for w, _, _ in EV} == set(range(len(tokens))), "every word must be heard"
last = EV[-1][2]
end = last + RL.tail_seconds(L)


def state(t):
    """(read, heat): read[k] = 1 once word k has started; heat[k] = how bright it is now (0..1)."""
    read = np.zeros(len(tokens)); heat = np.zeros(len(tokens))
    for w, a, b in EV:
        if t >= a:
            read[w] = 1
            if t < b:
                heat[w] = max(heat[w], smooth((t - a) / RISE))
            else:
                heat[w] = max(heat[w], 1 - smooth((t - b) / FALL))
    return read, heat


# ---------- frames ----------
ly = RL.layers(L)
st, sl, ct = RL._Layer(ly["static"]), RL._Layer(ly["slogan"]), RL._Layer(ly["cta"])
A_dim, E_dim = RL._Layer(ar_dim), RL._Layer(en_dim)
A_on, A_hot = [RL._Layer(x) for x in ar_on], [RL._Layer(x) for x in ar_hot]
E_on, E_hot = [RL._Layer(x) for x in en_on], [RL._Layer(x) for x in en_hot]
owner = {j: k for k, g in enumerate(S["map"]) for j in g}
bg = RL.background()

wav = OUT.with_suffix(".rec.m4a")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(MP3), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100",
                "-c:a", "aac", "-b:a", "160k", str(wav)], check=True)
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}", "-r", str(FPS),
       "-i", "-", "-i", str(wav), "-map", "0:v", "-map", "1:a", "-filter:a", "apad", "-c:v", "libx264", "-preset", "veryfast",
       "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
       "-t", f"{end:.2f}", "-movflags", "+faststart", str(OUT)]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
stills = {}
for i in range(int(round(end * FPS))):
    t = i / FPS
    frame = RL._ground(bg, t, end)
    A_dim.over(frame, 1.0); E_dim.over(frame, 1.0); st.over(frame, 1.0)
    read, heat = state(t)
    for k in range(len(tokens)):
        if read[k]:
            A_on[k].over(frame, 1.0)
        if heat[k] > 0:
            A_hot[k].over(frame, heat[k])
    for j in range(n):
        k = owner[j]
        if read[k]:
            E_on[j].over(frame, 1.0)
        if heat[k] > 0:
            E_hot[j].over(frame, heat[k])
    c = min(1.0, max(0.0, (t - last - RL.CTA_DELAY) / 0.35))
    sl.over(frame, 1.0 - c); ct.over(frame, c)
    RL._progress(frame, t / end, "quran")
    img = frame.clip(0, 255).astype(np.uint8)
    proc.stdin.write(img.tobytes())
    for want in S.get("check_at", []):
        if abs(t - want) < 0.5 / FPS:
            stills[want] = img
proc.stdin.close()
assert proc.wait() == 0
wav.unlink()
for want, img in stills.items():
    Image.fromarray(img).save(OUT.with_name(f"{OUT.stem}_{want:05.2f}.jpg"), quality=88)
print(json.dumps({"ok": True, "video": str(OUT), "seconds": round(end, 2), "recitation_end": last}))
