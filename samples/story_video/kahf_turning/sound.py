"""Ambient bed and small effects for the Kahf 18:18 video (noise and sine only: no samples, no music, no melody).
python3 sound.py <out.wav> <timeline.json>"""
import json, subprocess, sys
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
OUT, TL = sys.argv[1], json.load(open(sys.argv[2]))
SR, END = 48000, TL["end"]; C = TL["cues"]; N = int(END * SR)
rng = np.random.default_rng(18)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f): return sosfilt(butter(2, f, btype="low", fs=SR, output="sos"), x)
def db(d): return 10 ** (d / 20)
out = np.zeros(N)
def add(sig, t0, g):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if 0 <= i < N: out[i:j] += sig[:j - i] * g
t = np.arange(N) / SR
# a low, slowly moving room tone (no pitch you could hum)
drone = lp(rng.standard_normal(N), 180) * (0.7 + 0.3 * np.sin(2 * np.pi * t / 23))
drone = drone / np.abs(drone).max()
out += drone * db(-30)
# soft whoosh into every scene
for k, v in C.items():
    if k.startswith("s_") and v > .5:
        n = int(.9 * SR); x = np.linspace(0, 1, n)
        add(bp(rng.standard_normal(n), 300, 3000) * (x ** 1.5) * (1 - x) ** 2 * 3, v - .55, db(-30))
# monitor beeps during the intensive-care shots
for a, b in ((C["s_icu"], C["s_surah"]), (C["s_med"], C["s_tissue"])):
    for tb in np.arange(a + .4, b - .3, 1.53):
        n = int(.09 * SR); s = np.sin(2 * np.pi * 980 * np.arange(n) / SR) * np.hanning(n); add(s, tb, db(-34))
# low pulse when the vessel closes and when the tissue dies
for tk in ("t_block", "t_dead"):
    n = int(.7 * SR); tt = np.arange(n) / SR; add(np.sin(2 * np.pi * 55 * tt) * np.exp(-tt / .18), C[tk], db(-22))
fade = int(1.2 * SR); out[-fade:] *= np.linspace(1, 0, fade)
out /= max(1e-9, np.abs(out).max()); out *= .5
wavfile.write(OUT, SR, (out * 32767).astype(np.int16)); print("fx", OUT)
