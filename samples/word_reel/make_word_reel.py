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

HOT_AR = (255, 236, 186)      # the word being recited
HOT_EN = (240, 206, 128)      # its meaning
RISE, FALL = 0.10, 0.30       # seconds: into the bright state, back to plain gold

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
        on = blank(); ImageDraw.Draw(on).text(pos, wd, font=font, fill=RL.VERSE_ON + (255,), direction="rtl", language="ar")
        hot = blank(); ImageDraw.Draw(hot).text(pos, wd, font=font, fill=RL.VERSE_ON + (255,), direction="rtl", language="ar")
        glow = hot.filter(ImageFilter.GaussianBlur(14))
        hot = blank()
        hot.alpha_composite(glow); hot.alpha_composite(glow)
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
                heat[w] = max(heat[w], min(1.0, (t - a) / RISE))
            else:
                heat[w] = max(heat[w], max(0.0, 1 - (t - b) / FALL))
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
