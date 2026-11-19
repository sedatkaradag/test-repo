"""A to Z Islamic Quiz (owner's pick 19 Nov: English TTS version of @islamveihsan's 'A'dan Z'ye Dini Bilgiler').
python3 make.py <out_dir> [--stills=t1,...]     narration: tts/<id>.flac + .json (Kokoro bm_george 0.95)

25 letters (no X). One question per letter, read by the voice; a 2 s timer; the answer is stamped and read.
Questions and answers: questions.json (basic facts, source noted per item). Sound: voice, soft ticks, stamp, no music.
"""
import io, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
STILLS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--stills=")), None)
FPS, SR, THINK = 30, 48000, 1.5
Q = json.load(open(HERE / "questions.json"))


def tts(i):
    j = json.load(open(HERE / f"tts/{i}.json"))
    tk = [x for x in j["tokens"] if x["start"] is not None and x["text"].strip()]
    a, b = max(0, tk[0]["start"] - .05), min(j["duration"], max(x["end"] for x in tk) + .1)
    return j, tk, a, b


segs, items = [], []
t = .4
j, tk, a, b = tts("intro"); segs.append(("intro", t, a, b)); t += b - a + .9
for q in Q:
    item = {"l": q["l"], "a": q["a"], "start": round(t - .35, 3)}
    j, tk, a, b = tts(f"q_{q['l']}"); segs.append((f"q_{q['l']}", t, a, b))
    # words of the question as shown (display text), timed by the voice's words in order
    shown = q["q"].split(" ")
    voice = [x for x in tk if any(ch.isalnum() for ch in x["text"])]
    times = [t + x["start"] - a for x in voice]
    item["words"] = [{"w": w, "s": round(times[min(i * len(times) // len(shown), len(times) - 1)], 3)} for i, w in enumerate(shown)]
    t += b - a
    item["think"] = round(t + .1, 3); t += THINK
    item["ans"] = round(t, 3)
    j, tk, a, b = tts(f"a_{q['l']}"); segs.append((f"a_{q['l']}", t, a, b)); t += b - a + .4
    item["next"] = round(t - .1, 3)
    items.append(item)
outro_t = t
j, tk, a, b = tts("outro"); segs.append(("outro", t + .3, a, b)); t += .3 + b - a + 1.2
logo_t = t; END = round(t + 3.0, 2)
data = {"items": items, "outro_t": outro_t, "logo_t": logo_t, "end": END,
        "intro_hint": "Let’s see how many you get", "outro_hint": "Comment your score  ?/25",
        "logo": [str(p) for p in sorted((REPO / "samples/logo_draw/frames_800").iterdir())]}
mark = sorted((REPO / "samples/logo_draw/frames_478").iterdir())[-1]
page = (HERE / "page.html").read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__REPO__", str(REPO)).replace("__MARK__", str(mark))
run = OUT / "page_run.html"; run.write_text(page)
print("end", END, "letters", len(items))

from playwright.sync_api import sync_playwright


def shots(ts):
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(400)
        for x in ts:
            pg.evaluate(f"window.render({x})"); yield x, pg.screenshot(type="jpeg", quality=90)
        br.close()


if STILLS:
    from PIL import Image
    ims = []
    for x, buf in shots([float(v) for v in STILLS.split(",")]):
        im = Image.open(io.BytesIO(buf)); im.save(OUT / f"s_{x:06.2f}.jpg", quality=88); ims.append(im.resize((360, 640)))
    cols = min(6, len(ims)); c = Image.new("RGB", (360 * cols, 640 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims): c.paste(im, ((i % cols) * 360, (i // cols) * 640))
    c.save(OUT / "sheet.jpg", quality=85); print("sheet"); sys.exit(0)

# ---------- audio ----------
N = int(END * SR); voice = np.zeros(N); fx = np.zeros(N); rng = np.random.default_rng(3)
def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)
for sid, t0, a, b in segs:
    x = load(HERE / f"tts/{sid}.flac")[int(a * SR):int(b * SR)]; f = int(.015 * SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    i = int(t0 * SR); voice[i:i + len(x)] += x[:N - i]
voice *= .12 / np.sqrt((voice[np.abs(voice) > 1e-4] ** 2).mean())
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f): return sosfilt(butter(2, f, btype="low", fs=SR, output="sos"), x)
def add(sig, t0, g):
    i = int(t0 * SR); j2 = min(N, i + len(sig))
    if 0 <= i < N: fx[i:j2] += sig[:j2 - i] * g
for it in items:
    for k in range(3):   # soft clock ticks during the 1.5 s timer
        n = int(.03 * SR); add(bp(rng.standard_normal(n), 1800, 6000) * np.exp(-np.arange(n) / (.004 * SR)), it["think"] + .1 + k * .5, .10 if k % 2 == 0 else .07)
    n = int(.25 * SR); tt = np.arange(n) / SR   # stamp
    add((np.sin(2 * np.pi * 95 * tt) * .8 + lp(rng.standard_normal(n), 900) * .5) * np.exp(-tt / .045), it["ans"] - .02, .32)
    n = int(.5 * SR); x = np.linspace(0, 1, n); add(bp(rng.standard_normal(n), 400, 3000) * x ** 1.5 * (1 - x) ** 2 * 3, it["start"] - .2, .05)
n = N; room = lp(np.cumsum(rng.standard_normal(n)), 220); room /= np.abs(room).max(); fx += room * .02
mix = voice + fx; mix /= max(1.0, np.abs(mix).max() / .95)
wavfile.write(OUT / "mix_raw.wav", SR, (mix * 32767).astype(np.int16))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / "mix_raw.wav"), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SR), str(OUT / "mix.wav")], check=True)
video = OUT / "az_quiz.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-", "-i", str(OUT / "mix.wav"),
                       "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                       "-t", f"{END:.2f}", "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)
for _, buf in shots([i / FPS for i in range(int(round(END * FPS)))]):
    ff.stdin.write(buf)
ff.stdin.close(); assert ff.wait() == 0
print(json.dumps({"ok": True, "video": str(video), "seconds": END}))
