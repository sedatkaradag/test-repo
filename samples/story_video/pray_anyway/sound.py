"""Ambient sound for 'Pray anyway', made from noise and sine partials (no samples, no music, no melody).
python3 sound.py <out_dir>  -> <out_dir>/ambient.wav (48 kHz stereo, loudness-normalised)"""
import subprocess, sys
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SR, END = 48000, 28.4
rng = np.random.default_rng(7)
N = int(SR * END)
L = np.zeros(N); R = np.zeros(N)
T = {"fajr": 0.0, "dhuhr": 1.9, "asr": 3.6, "maghrib": 5.3, "isha": 7.0, "low": 8.7, "broken": 10.3,
     "joy": 11.9, "grateful": 13.5, "anyway": 15.1, "hadith": 18.4, "logo": 25.6}
CUT = sorted(T.values()) + [END]

def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)
def hp(x, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)
def db(d):
    return 10 ** (d / 20)
def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if i >= N or j <= i: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2) * 1.41; R[i:j] += s * np.sqrt((1 + pan) / 2) * 1.41
def env(n, a=.005, r=.05):
    e = np.ones(n); na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
def bed(t0, t1, sig_fn, gain, pan=0.0):
    n = int((t1 - t0) * SR); s = sig_fn(n) * env(n, .02, .03); add(s, t0, gain, pan)
def noise(n):
    return rng.standard_normal(n)
def brown(n):
    b = np.cumsum(noise(n)); b = hp(b, 20); return b / (np.abs(b).max() + 1e-9)
def decay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))
def click(dur=.012, lo=1500, hi=9000):
    n = int(dur * SR); return bp(noise(n), lo, hi) * decay(n, dur / 4)
def thud(f=70, dur=.35, nmix=.5):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t * (1 - .25 * t / dur)) + nmix * lp(noise(n), 300)) * decay(n, dur / 5)
def metal(dur=.5, parts=(2350, 5230, 8100), tau=.12):
    n = int(dur * SR); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * decay(n, tau * (1.2 - k * .3)) / (k + 1) for k, f in enumerate(parts))
def chirp(f0, f1, dur):
    n = int(dur * SR); t = np.arange(n) / SR; f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / dur) ** 2
def bird(t0, pan, n=3, base=3600, gain=db(-30)):
    t = t0
    for _ in range(n):
        f0 = base * rng.uniform(.9, 1.2); add(chirp(f0, f0 * rng.uniform(1.3, 1.7), rng.uniform(.05, .09)), t, gain, pan)
        t += rng.uniform(.09, .16)
def plus(*xs):
    m = max(len(x) for x in xs); return sum(np.pad(x, (0, m - len(x))) for x in xs)
def room(n, color):
    return lp(brown(n), color)

# room tone under each scene (different rooms)
ROOM = {"fajr": (300, -40), "dhuhr": (900, -42), "asr": (500, -40), "maghrib": (700, -41), "isha": (350, -40),
        "low": (400, -41), "broken": (300, -42), "joy": (900, -42), "grateful": (500, -41), "anyway": (250, -47),
        "hadith": (250, -45), "logo": (250, -54)}
for k, t0 in T.items():
    t1 = CUT[CUT.index(t0) + 1]
    c, g = ROOM[k]; bed(t0, t1, lambda n: room(n, c), db(g))

# Fajr: phone vibrating on the floor, then a first bird outside
for a, b in ((.12, .55), (.78, 1.2)):
    n = int((b - a) * SR); t = np.arange(n) / SR
    buzz = np.tanh(3 * np.sin(2 * np.pi * 165 * t)) * (0.6 + .4 * np.sin(2 * np.pi * 28 * t)) + .3 * bp(noise(n), 150, 900)
    add(lp(buzz, 2500) * env(n, .01, .04), a, db(-31), .5)
bird(1.45, -.6, 2, 3300, db(-36))
# Dhuhr: typing, an air conditioner
bed(1.9, 3.6, lambda n: bp(noise(n), 200, 1200), db(-46), .2)
t = 2.0
while t < 3.45:
    add(plus(click(.01, 1800, 7000), .4 * thud(210, .04, .3)), t, db(-21) * rng.uniform(.6, 1), .35); t += rng.uniform(.06, .17)
# Asr: a clock ticking, a gust of wind
for k in range(4):
    add(click(.008, 2500, 9000), 3.7 + k * .5, db(-23) * (1 if k % 2 else .7), -.3)
bed(3.6, 5.3, lambda n: bp(noise(n), 250, 1400) * (0.3 + .7 * np.sin(np.linspace(0, np.pi, n)) ** 2), db(-29), .1)
# Maghrib: the door closes, keys land, a bag is set down
add(thud(68, .45, .7), 5.34, db(-22), .2); add(hp(click(.05, 800, 5000), 600), 5.34, db(-28), .2)
for k in range(5):
    add(metal(.35, (rng.uniform(3000, 4200), rng.uniform(5500, 7000), rng.uniform(8000, 9500)), .06), 5.95 + k * rng.uniform(.03, .07), db(-31), -.4)
add(thud(110, .2, 1.0), 6.45, db(-26), -.5)
# Isha: crickets outside, a cup on its saucer
for k in range(5):
    t0 = 7.05 + k * .33
    for j in range(3):
        n = int(.018 * SR); add(np.sin(2 * np.pi * 4450 * np.arange(n) / SR) * np.hanning(n), t0 + j * .032, db(-35), .7)
add(metal(.6, (2350, 5230, 8100), .14), 7.75, db(-26), .45)
# Low: rain on the window, a paper crumpled
def rain(n):
    s = bp(noise(n), 900, 7000) * .5
    for _ in range(int(n / SR * 90)):
        i = rng.integers(0, max(1, n - 600)); s[i:i + 600] += click(600 / SR, 2000, 9000)[:600] * rng.uniform(.3, 1)
    return s
bed(8.7, 11.9, rain, db(-31), -.2)
t = 8.95
for _ in range(14):
    add(click(.006, 1500, 9000), t, db(-27) * rng.uniform(.5, 1), -.5); t += rng.uniform(.015, .05)
# Heartbroken: rain continues, distant thunder
n = int(1.6 * SR); add(lp(noise(n), 120) * np.sin(np.linspace(0, np.pi, n)) ** 2, 10.55, db(-17), 0)
# Joy: birds, a breeze
for t0, pan in ((12.0, -.6), (12.55, .5), (13.1, -.3)):
    bird(t0, pan, int(rng.integers(2, 4)), rng.uniform(3200, 4200), db(-30))
bed(11.9, 13.5, lambda n: bp(noise(n), 400, 2500) * (.4 + .6 * np.sin(np.linspace(0, np.pi, n))), db(-40), .3)
# Grateful: a page turns, prayer beads click
n = int(.45 * SR); sw = bp(noise(n), 1200, 6000) * np.sin(np.linspace(0, np.pi, n)) ** 1.5
add(sw, 13.75, db(-25), .5)
for k in range(6):
    add(plus(click(.007, 2500, 8000), .3 * metal(.05, (4200, 6100), .01)), 14.35 + k * .11, db(-29), -.5)
# Anyway: everything stops; hands meet the rug
add(lp(noise(int(.18 * SR)), 260) * decay(int(.18 * SR), .04), 15.32, db(-20), 0)
# Hadith and logo: quiet room, one far bird
bird(21.2, .6, 2, 3000, db(-44))

# The rug opens at the start of every scene up to the climax: a fabric swish, then it settles flat
for k in ("fajr", "dhuhr", "asr", "maghrib", "isha", "low", "broken", "joy", "grateful", "anyway"):
    dur = 1.35 if k == "anyway" else .72
    n = int(dur * SR); x = np.linspace(0, 1, n)
    sw = bp(noise(n), 260, 2600) * (x ** .4) * (1 - x) ** 1.6 * 3.2
    add(sw, T[k] + .06, db(-27 if k == "anyway" else -30), 0)
    m = int(.12 * SR); add(lp(noise(m), 220) * decay(m, .025), T[k] + .06 + dur * .92, db(-27), 0)

mix = np.stack([lp(L, 11000, 4), lp(R, 11000, 4)], 1)   # soften the clicks
fade = int(.8 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix /= np.abs(mix).max() + 1e-9
raw = OUT / "ambient_raw.wav"; wavfile.write(raw, SR, (mix * .9 * 32767).astype(np.int16))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-19:TP=-1.5:LRA=14", "-ar", str(SR),
                str(OUT / "ambient.wav")], check=True)
for k, t0 in T.items():
    t1 = CUT[CUT.index(t0) + 1]; s = mix[int(t0 * SR):int(t1 * SR)]
    print(f"{k:9s} rms {20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9):6.1f} dB  peak {20 * np.log10(np.abs(s).max() + 1e-9):6.1f} dB")
print("ok", OUT / "ambient.wav")
