"""Sample (not part of the system): 'voice note' Reel. A message at night (HIM / HER panels), answered
with a voice note of Al-Isra 17:32 (Alafasy). Rendered frame by frame from page.html in Chromium.

    python3 samples/voice_note/make_voice_note.py <repo> <audio_dir> <out_dir>
"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

REPO, AUD, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
HERE = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "scripts"))
import render as R
from content import get

SR, FPS = 44100, 30
entry = get("quran:17:32")
words = R._arabic_words(entry["arabic_display"])          # last word keeps its verse number
english = entry["english"].strip()
# the English in three parts that follow the verse's own pauses (text unchanged, only split)
p1, rest = english.split(", ", 1)
i = rest.index(" and an evil way")
parts = [p1 + ",", rest[:i], rest[i + 1:]]
assert " ".join(parts) == english, parts
# which English words go with each Arabic word (for the reading emphasis; the text itself is not changed)
# (English word indices per Arabic word: inna-hu = "for it ... indeed", kana = "is")
phrases = [{"words": [0, 1, 2], "english": parts[0], "map": [[0, 1], [2, 3], [4]]},        # Do not | go near | adultery,
           {"words": [3, 4, 5], "english": parts[1], "map": [[0, 1, 3], [2], [4, 5, 6]]},  # for it..indeed | is | a shameful act
           {"words": [6, 7], "english": parts[2], "map": [[0, 1, 2], [3]]}]                # and an evil | way
for p in phrases:
    assert sorted(j for g in p["map"] for j in g) == list(range(len(p["english"].split(" ")))), p
assert len(words) == 8
seg = json.loads((AUD / "align.json").read_text())["017032"]
assert len(seg) == 8

subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(AUD / "audio" / "017032.mp3"), "-ac", "1", "-ar", str(SR), str(OUT / "rec.wav")], check=True)
with wave.open(str(OUT / "rec.wav")) as w:
    rec = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
rec = rec / (np.abs(rec).max() + 1e-9) * 10 ** (-4 / 20)
hop = SR // FPS
env = np.array([np.sqrt(np.mean(rec[i:i + hop] ** 2)) for i in range(0, len(rec), hop)])
env = np.sqrt(env / (env.max() + 1e-9)).round(3).tolist()

# the two messages he types: dots, typing (one tap per letter), the bubble turns into a heart, the heart flies
msgs, t0 = [], 0.7
for text, heart in [("I like you...", False), ("Can we talk tonight? Just us", True)]:
    d0 = t0; ty0 = d0 + 0.35; ty1 = ty0 + 0.065 * (len(text) + heart); mo = ty1 + 0.35; f0 = mo + 0.25; f1 = f0 + 0.8
    msgs.append({"text": text, "heart": heart, "lines": [text] if len(text) < 20 else [text[:text.index("? ") + 1], text[text.index("? ") + 2:]], "dots0": round(d0, 2), "type0": round(ty0, 2), "type1": round(ty1, 2), "morph": round(mo, 2), "fly0": round(f0, 2), "fly1": round(f1, 2)})
    t0 = f1 + 0.35
last = msgs[-1]["fly1"]
T = {"zoom0": round(last + 1.1, 2)}
T["zoom1"] = round(T["zoom0"] + 0.8, 2)
T["m1"] = round(T["zoom0"] + 0.55, 2); T["m2"] = round(T["m1"] + 0.35, 2)
T["rec0"] = round(T["m2"] + 1.3, 2); T["a0"] = A0 = round(T["rec0"] + 0.4, 2)
T["rel"] = round(A0 + seg[-1][3] / 1000 + 0.6, 2)
T["fade0"] = round(T["rel"] + 1.6, 2)
T["end0"] = round(T["fade0"] + 0.6, 2)
END = T["end0"] + 4.2
vdur = f"0:{int(round(T['rel'] - T['rec0'])):02d}"
logo = [f"file://{p}" for p in sorted((REPO / "samples" / "logo_draw" / "frames_800").glob("*.png"))]
data = {"msgs": msgs, "words": words, "phrases": phrases, "ref": "Surah Al-Isra 17:32", "seg": seg, "env": env, "T": T, "logo": logo, "vdur": vdur}
html = (HERE / "page.html").read_text().replace("<script>\nconst D", "<script>window.DATA=" + json.dumps(data, ensure_ascii=False) + "</script>\n<script>\nconst D", 1)
(HERE / "page_run.html").write_text(html)

# ---------- sounds ----------
def tt(sec): return np.arange(int(sec * SR)) / SR
def ping():
    t = tt(0.9); out = np.zeros_like(t)
    for k, (f, st) in enumerate([(1318.5, 0), (1760, 0.09)]):
        m = t >= st; u = t[m] - st
        out[m] += (np.sin(2 * np.pi * f * u) + 0.3 * np.sin(4 * np.pi * f * u)) * np.exp(-u / 0.22) * np.minimum(1, u / 0.004)
    return out * 0.15
def whoosh(up=True):
    t = tt(0.55); rng = np.random.default_rng(3); n = rng.standard_normal(len(t))
    f = np.linspace(600, 2600, len(t)) if up else np.linspace(2600, 600, len(t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    out = np.convolve(n, np.ones(12) / 12, "same") * (0.6 + 0.4 * np.sin(ph)) * np.sin(np.pi * t / t[-1]) ** 2
    return out * 0.09
def blip():
    t = tt(0.18); f = np.linspace(700, 1150, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.06) * 0.10
def tick():
    t = tt(0.12); return (np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.012) + 0.4 * np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.03)) * 0.08
def close():
    t = tt(3.2); out = np.zeros_like(t)
    for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        st = k * 0.16; m = t >= st; u = t[m] - st
        out[m] += (np.sin(2 * np.pi * f * u) + 0.25 * np.sin(4 * np.pi * f * u)) * np.exp(-u / 1.1) * np.minimum(1, u / 0.01)
    for dly, g in [(0.11, 0.3), (0.23, 0.15)]:
        d = int(dly * SR); out[d:] += g * out[:-d].copy()
    return out * 0.10
def tap(seed):
    t = tt(0.05); rng = np.random.default_rng(seed)
    return np.convolve(rng.standard_normal(len(t)), [1, -0.95], "same") * np.exp(-t / 0.006) * 0.05
mix = np.zeros(int((END + 1) * SR))
def add(at, sig):
    i = int(at * SR); n = min(len(sig), len(mix) - i); mix[i:i + n] += sig[:n]
def pop():
    t = tt(0.16); f = np.linspace(500, 900, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * 0.10
for ms in msgs:
    chars = "".join(ms["lines"]) + ("*" if ms["heart"] else "")     # one tap per letter, and one for the heart
    n = len(chars)
    for i in range(n):
        if chars[i] != " ":
            add(ms["type0"] + (ms["type1"] - ms["type0"]) * i / n, tap(int(ms["type0"] * 1000) + i))
    add(ms["morph"], pop()); add(ms["fly0"], whoosh(False)); add(ms["fly1"], ping())
add(T["rec0"], blip()); add(A0, rec); add(T["rel"], whoosh(True))
add(T["end0"] + 0.25, close())
mix = mix[:int(END * SR)]
pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
with wave.open(str(OUT / "audio.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

# ---------- frames ----------
from playwright.sync_api import sync_playwright
video = OUT / "voice_note_1732_alafasy.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                       "-i", str(OUT / "audio.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-t", f"{END:.2f}",
                       "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)
marks = sorted({round(x, 2) for x in [0.9, msgs[0]["type0"] + 0.4, msgs[0]["type1"] + 0.1, msgs[0]["morph"] + 0.15, (msgs[0]["fly0"] + msgs[0]["fly1"]) / 2, msgs[0]["fly1"] + 0.3, msgs[1]["type0"] + 1.0, msgs[1]["morph"] + 0.15, (msgs[1]["fly0"] + msgs[1]["fly1"]) / 2, msgs[1]["fly1"] + 0.5, T["zoom0"] + 0.4, T["m2"] + 0.6, A0 + 1.0, A0 + 3.5, A0 + 5.5, A0 + 8.0, A0 + 10.4, T["rel"] + 0.8, T["fade0"] + 0.3, T["end0"] + 1.0, END - 0.1]})
(OUT / "frames").mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.goto(f"file://{HERE / 'page_run.html'}")
    pg.evaluate("window.ready")
    pg.wait_for_timeout(300)
    n = int(round(END * FPS))
    for i in range(n):
        t = i / FPS
        pg.evaluate(f"window.render({t})")
        jpg = pg.screenshot(type="jpeg", quality=93)
        ff.stdin.write(jpg)
        for m in list(marks):
            if abs(t - m) < 0.5 / FPS:
                (OUT / "frames" / f"f_{m:05.2f}.jpg").write_bytes(jpg); marks.remove(m)
    b.close()
ff.stdin.close(); ff.wait()
print("ok", video, f"{END:.1f}s", T)
