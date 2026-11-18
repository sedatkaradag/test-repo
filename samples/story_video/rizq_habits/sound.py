"""Night ambience and small effects for 'Innocent habits blocking your rizq' (noise and sines only: no samples, no music).
python3 sound.py <out_dir> <timeline.json>  -> <out_dir>/ambient.wav"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
OUT = Path(sys.argv[1]); TL = json.load(open(sys.argv[2]))
SR, END = 48000, TL["end"]; SC, TURN = TL["scenes"], TL["turn"]; N = int(SR * END)
rng = np.random.default_rng(5); L = np.zeros(N); R = np.zeros(N)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f): return sosfilt(butter(2, f, btype="low", fs=SR, output="sos"), x)
def db(d): return 10 ** (d / 20)
def noise(n): return rng.standard_normal(n)
def add(sig, t0, g, pan=0.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if 0 <= i < N: s = sig[:j - i] * g; L[i:j] += s * np.sqrt((1 - pan) / 2) * 1.41; R[i:j] += s * np.sqrt((1 + pan) / 2) * 1.41
def env(n, a, r): e = np.ones(n); na, nr = max(1, int(a * SR)), max(1, int(r * SR)); e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
def dec(n, tau): return np.exp(-np.arange(n) / (tau * SR))
# night bed: soft air, low hum, far crickets
bed = lp(np.cumsum(noise(N)), 300); bed /= np.abs(bed).max(); add(bed * env(N, 1.5, 2), 0, db(-34))
air = bp(noise(N), 300, 2200) * (0.5 + 0.5 * np.sin(2 * np.pi * np.arange(N) / SR / 11)); add(air / np.abs(air).max() * env(N, 2, 2), 0, db(-44))
for t0 in np.arange(1.0, END - 3, 0.9):
    if rng.random() < .6:
        for j in range(3):
            n = int(.016 * SR); add(np.sin(2 * np.pi * 4300 * np.arange(n) / SR) * np.hanning(n), t0 + j * .03, db(-46) * rng.uniform(.5, 1), rng.uniform(-.8, .8))
def shimmer(t0, g):
    """Soft warm 'bloom' (owner, 18 Nov: the old high sine sparkle was grating): low breathy swell, no pitch."""
    n = int(1.6 * SR); x = np.linspace(0, 1, n)
    swell = lp(bp(noise(n), 120, 1400), 900) * (x ** .8) * (1 - x) ** 1.8 * 4
    add(swell, t0 - .2, g * .9)
def keys(t0, text):
    """A keyboard key for every typed character (owner, 18 Nov)."""
    for k, ch in enumerate(text):
        n = int(.045 * SR); tick = bp(noise(n), 1200, 5200) * dec(n, .006)
        thud = lp(noise(n), 260) * dec(n, .012) * .8
        g = db(-27) * rng.uniform(.65, 1.0) * (1.25 if ch == " " else 1.0)
        add(tick + thud, t0 + k * .055 + rng.uniform(-.006, .006), g, rng.uniform(-.25, .25))
def strike(t0):  # pen line across the words
    n = int(.42 * SR); x = np.linspace(0, 1, n); add(bp(noise(n), 1500, 6500) * (np.sin(np.pi * x) ** .6), t0, db(-33), -.3 + .6 * 0)
shimmer(.4, db(-34))
for i, h in enumerate(TL["habits"]):
    t0 = SC[f"h{i}"][0]; add(bp(noise(int(.7 * SR)), 300, 2500) * np.hanning(int(.7 * SR)), t0 - .35, db(-36))   # soft whoosh in
    keys(t0 + .35, h["head"])
    strike(t0 + .35 + len(h["head"]) * .055 + .35)
    tt = t0 + TURN
    if i == 0:   # door creaks open, light
        n = int(1.0 * SR); tt_ = np.arange(n) / SR; cr = np.sin(2 * np.pi * (180 + 60 * np.sin(tt_ * 9)) * tt_) * bp(noise(n), 200, 1200) * 2
        add(cr * env(n, .05, .3), tt, db(-36), .2); shimmer(tt + .5, db(-30))
    if i == 1:   # rain, then quiet water
        n = int((TURN + .1) * SR); r = bp(noise(n), 1200, 7000) * .5
        for _ in range(int(n / SR * 70)):
            k = rng.integers(0, n - 500); r[k:k + 500] += bp(noise(500), 2500, 8000) * dec(500, .002) * rng.uniform(.4, 1)
        add(r * env(n, .3, .6), t0 + .1, db(-33))
        n = int(4.5 * SR); w = lp(noise(n), 500) * (0.6 + 0.4 * np.sin(2 * np.pi * np.arange(n) / SR * .7)); add(w * env(n, .8, 1.2), tt, db(-34))
    if i == 2:   # five light switches
        for j in range(5):
            n = int(.03 * SR); add(bp(noise(n), 1500, 6000) * dec(n, .004), tt - 1.2 + j * .35 + .15, db(-28), -.6 + j * .3)
    if i == 3:   # leaves unfold
        for j in range(4):
            n = int(.35 * SR); add(bp(noise(n), 2000, 7000) * np.hanning(n), tt - .3 + j * .15, db(-38), rng.uniform(-.4, .4))
        shimmer(tt + .6, db(-34))
    if i == 4:   # lantern catches
        n = int(.5 * SR); add(lp(noise(n), 900) * dec(n, .12), tt, db(-28)); n = int(4 * SR); add(bp(noise(n), 200, 1500) * env(n, .4, 1), tt + .2, db(-44))
shimmer(SC["end"][0] + .3, db(-32)); shimmer(SC["logo"][0] + .1, db(-30))
mix = np.stack([lp(L, 11000), lp(R, 11000)], 1); f = int(1.0 * SR); mix[-f:] *= np.linspace(1, 0, f)[:, None]
mix /= np.abs(mix).max() + 1e-9
raw = OUT / "ambient_raw.wav"; wavfile.write(raw, SR, (mix * .9 * 32767).astype(np.int16))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-20:TP=-1.5:LRA=12", "-ar", str(SR), str(OUT / "ambient.wav")], check=True)
print("ok", OUT / "ambient.wav")
