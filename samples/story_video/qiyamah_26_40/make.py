"""Al-Qiyamah 75:26-40, one verse at a time, each with its own small scene (remake of @ahvalikuran's reel DezZgZ6hw5F,
owner's pick 20 Nov). English meaning, our design and closing.
python3 make.py <out_dir> [--rec=<dir with audio/075026.mp3 ... and align.json>] [--stills=t1,...]

Recitation: Alafasy (everyayah via audio-fetch, word times from quran-align), chosen by me (owner: "güzel bi kari sen seç"):
melodious, 85 s for the 15 verses (Husary 119 s), and word timings exist. Before use the 15 files were checked by
speech-to-text: each holds its own verse only (lesson of the 7:199 file, 20 Nov).
Words light softly as they are recited (dim gold -> gold, the current word glows: 0.35 s in, 0.7 s out).
Sound: the recitation only, as the reference.
"""
import io, json, re, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
STILLS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--stills=")), None)
REC = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--rec=")), "/home/claude/qiy/Alafasy_128kbps"))
FPS, SR, SURAH, VS = 30, 48000, 75, range(26, 41)
INTRO = 0.9
AL = json.load(open(REC / "align.json"))

def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)

verses, clips, t = [], [], INTRO
for v in VS:
    d = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", f"quran:{SURAH}:{v}"], capture_output=True, text=True, check=True).stdout)
    ar = re.sub(r"[\s\u00a0]*[٠-٩]+\s*$", "", d["arabic_display"]).strip()   # drop the verse number; the page draws it in its ornament
    key = f"{SURAH:03d}{v:03d}"; al = AL[key]; x = load(REC / "audio" / f"{key}.mp3")
    assert len(ar.split(" ")) == len(al), (v, ar, al)
    last = al[-1][3] / 1000; dur = min(len(x) / SR, last + .55)   # cut the trailing silence of the file
    clips.append((t, x[:int(dur * SR)]))
    verses.append({"n": v, "ar": ar, "en": d["english"], "t0": round(t, 3), "t1": round(t + dur, 3),
                   "words": [{"s": round(t + a / 1000, 3), "e": round(t + b / 1000, 3)} for _, _, a, b in al]})
    t += dur
LOGO = round(t + .9, 2); END = LOGO + 3.4

N = int(END * SR); mono = np.zeros(N)
for t0, x in clips:
    i = int(t0 * SR); x = x.copy(); f = int(.04 * SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f); mono[i:i + len(x)] += x
spoken = mono[np.abs(mono) > 1e-3]; mono *= 10 ** (-16 / 20) / np.sqrt((spoken ** 2).mean())
mono *= min(1, 10 ** (-1 / 20) / np.abs(mono).max())
env = np.array([np.sqrt((mono[int(k / FPS * SR):int((k + 1) / FPS * SR)] ** 2).mean()) for k in range(int(END * FPS) + 1)])
env = np.clip(env / (np.percentile(env[env > 0], 95) + 1e-9), 0, 1)

data = {"verses": verses, "logo": LOGO, "env": [round(float(e), 3) for e in env],
        "logo_frames": None}
data["logo"] = LOGO
logo = [str(p) for p in sorted((REPO / "samples/logo_draw/frames_800").iterdir())]
mark = sorted((REPO / "samples/logo_draw/frames_478").iterdir())[-1]
page = (HERE / "page.html").read_text().replace("__DATA__", json.dumps({**data, "logo": LOGO, "logo_frames": logo}, ensure_ascii=False))
page = page.replace("D.logo.map(", "D.logo_frames.map(").replace("__REPO__", str(REPO)).replace("__MARK__", str(mark))
run = OUT / "page_run.html"; run.write_text(page)
print("end", round(END, 2), "verses", [(v["n"], v["t0"]) for v in verses])

from playwright.sync_api import sync_playwright
def shots(ts):
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(400)
        for x in ts:
            pg.evaluate(f"window.render({x})"); yield x, pg.screenshot(type="jpeg", quality=92)
        br.close()

if STILLS:
    from PIL import Image
    ims = []
    for x, buf in shots([float(s) for s in STILLS.split(",")]):
        im = Image.open(io.BytesIO(buf)); im.save(OUT / f"s_{x:06.2f}.jpg", quality=88); ims.append(im.resize((360, 640)))
    cols = min(6, len(ims)); c = Image.new("RGB", (360 * cols, 640 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims): c.paste(im, ((i % cols) * 360, (i // cols) * 640))
    c.save(OUT / "sheet.jpg", quality=85); print("sheet"); sys.exit(0)

wavfile.write(OUT / "rec.wav", SR, (np.stack([mono, mono], 1) * 32767).astype(np.int16))
video = OUT / "qiyamah_26_40.mp4"; tmp = OUT / "qiyamah_26_40_tmp.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-", "-i", str(OUT / "rec.wav"),
                       "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                       "-t", f"{END:.2f}", "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE)
for _, buf in shots([i / FPS for i in range(int(round(END * FPS)))]):
    ff.stdin.write(buf)
ff.stdin.close(); assert ff.wait() == 0; tmp.rename(video)
print(json.dumps({"ok": True, "video": str(video), "seconds": round(END, 2)}))
