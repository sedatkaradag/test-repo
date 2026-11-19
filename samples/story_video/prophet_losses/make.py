"""'The Prophet ﷺ lost so much before he turned 50' (remake of @kulturselarsiv's reel DfnU09VMo0j, owner's pick 19 Nov).
python3 make.py <out_dir> [--stills=t1,...]

Every person is a glowing line running down through the years of the Prophet's ﷺ life (age axis on the left).
When someone passes away their line ends and their name rises into the sky as a star; at 63 the Prophet ﷺ
becomes a star too, the stars join into one constellation, then "only Fatimah" and Al-Anbiyaa 21:107.
Sources: Bukhari/Muslim where there is a narration (notes in PEOPLE); ages and the sons al-Qasim and Abdullah
from the sira (Ibn Ishaq / Ibn Hisham): the owner approved sira for this video on 19 Nov.
Sound: our own ambience (sines), light rain (CC0 recording, see below), soft blooms when a star rises; no music. 21:107 recited by
Alafasy (drafts-audio, word times from quran-align) with the words lighting up; no rain under the recitation (owner, 19 Nov).
python3 make.py <out> expects REC=/home/claude/pl/rec (021107.mp3 + align.json) unless --rec=<dir>.
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
FPS, SR = 30, 48000
HA, HU = "raḍiyAllāhu ʿanhā", "raḍiyAllāhu ʿanhu"
SAW = '<span class="saw">ﷺ</span>'
# id, role, name, honorific, colour, column order, from age, to age, how the line starts, sky slot (x, y, label side)
PEOPLE = [
    ("am", "GRANDFATHER", "Abdul-Muttalib", "", "#b9b4ff", 0, -9, 8.0, None, (300, 318, "L")),          # sira: died when he was 8
    ("amina", "MOTHER", "Aminah", "", "#ff8f9f", 1, -9, 6.0, None, (160, 398, "R")),                     # sira: died when he was 6 (her grave: Muslim 976)
    ("khadijah", "WIFE", "Khadijah", HA, "#f28fd8", 2, 25.0, 50.15, "left", (272, 640, "R")),           # died 3 years before the Hijrah: Bukhari 3896
    ("qasim", "SON", "al-Qasim", HU, "#7fe0b0", 3, 27.0, 29.6, "prophet", (452, 350, "T")),              # sira
    ("zaynab", "DAUGHTER", "Zaynab", HA, "#dde47e", 4, 30.0, 61.0, "prophet", (165, 532, "R")),          # her washing: Muslim 939
    ("ruqayyah", "DAUGHTER", "Ruqayyah", HA, "#b394ff", 5, 33.0, 55.0, "prophet", (640, 350, "T")),      # ill at Badr: Bukhari 3130
    ("ummk", "DAUGHTER", "Umm Kulthum", HA, "#ffab70", 6, 34.0, 62.0, "prophet", (662, 742, "R")),       # her burial: Bukhari 1285
    ("fatimah", "DAUGHTER", "Fatimah", HA, "#72d8ea", 7, 35.0, 63.5, "prophet", (428, 742, "L")),        # six months after him: Bukhari 4240
    ("abdullah_s", "SON", "Abdullah", HU, "#9cd0ff", 8, 41.0, 42.6, "prophet", (818, 318, "R")),         # sira
    ("prophet", "", "Prophet Muhammad " + SAW, "", "#f2c862", 9, 0.0, 63.0, "amina", (545, 866, "R")),        # 63: Bukhari 3536
    ("ibrahim", "SON", "Ibrahim", HU, "#f4f1e6", 10, 61.1, 62.65, "prophet", (818, 640, "L")),           # Bukhari 1303
    ("abutalib", "UNCLE", "Abu Talib", "", "#e6e6e6", 11, 8.0, 49.95, "right", (926, 532, "L")),        # his death: Bukhari 3884
    ("father", "FATHER", "Abdullah", "", "#8fb4ff", 12, -9, -0.3, None, (926, 398, "L")),                # sira: died before his birth (93:6)
]
EDGES = [("am", "qasim"), ("qasim", "ruqayyah"), ("ruqayyah", "abdullah_s"), ("am", "amina"), ("abdullah_s", "father"),
         ("amina", "zaynab"), ("zaynab", "khadijah"), ("khadijah", "fatimah"), ("fatimah", "prophet"),
         ("father", "abutalib"), ("abutalib", "ibrahim"), ("ibrahim", "ummk"), ("ummk", "prophet")]
# (time s, age): slower where something happens
KF = [(0, -1.6), (2.4, -0.9), (4.6, 0.3), (7.4, 3.0), (9.6, 6.25), (11.8, 8.35), (17.0, 24.3), (19.0, 25.6), (20.6, 27.3),
      (22.6, 29.8), (24.0, 30.6), (27.6, 35.4), (30.4, 41.2), (32.6, 42.8), (36.2, 49.7), (39.0, 50.35), (42.0, 55.25),
      (45.4, 61.2), (47.4, 62.1), (49.4, 62.75), (51.6, 63.02), (54.0, 63.52)]
REC = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--rec=")), "/home/claude/pl/rec"))
AL = json.load(open(REC / "align.json"))["021107"]
SC = {"introEnd": 7.6, "fade": 55.0, "const": 56.4, "fat": 58.4, "verse": 65.6}
REC_T = SC["verse"] + .9; REC_END = REC_T + AL[-1][3] / 1000
SC["logo"] = round(REC_END + 1.9, 2)
END = SC["logo"] + 3.4

v = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", "quran:21:107"], capture_output=True, text=True, check=True).stdout)
name, num = v["reference"].replace("Surah ", "").rsplit(" ", 1)
verse = {"ar": v["arabic_display"].rstrip(" ١٠٧").strip(), "en": v["english"], "ref": f"{name.upper()} {num}"}
assert len(verse["ar"].split(" ")) == len(AL), (verse["ar"], AL)
verse["words"] = [{"s": round(REC_T + a / 1000, 3), "e": round(REC_T + b / 1000, 3)} for _, _, a, b in AL]
people = [{"id": i, "role": r, "name": n, "hon": h, "color": c, "order": o, "from": a0, "to": a1,
           "enter": e if e in ("left", "right") else None, "parent": e if e not in ("left", "right") else None, "slot": list(s)}
          for i, r, n, h, c, o, a0, a1, e, s in PEOPLE]
data = {"people": people, "edges": EDGES, "kf": KF, "scenes": SC, "head": 900, "ppy": 78, "xl": 165, "xr": 935, "maxsp": 250,
        "verse": verse, "logo": [str(p) for p in sorted((REPO / "samples/logo_draw/frames_800").iterdir())]}
mark = sorted((REPO / "samples/logo_draw/frames_478").iterdir())[-1]
page = (HERE / "page.html").read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__REPO__", str(REPO)).replace("__MARK__", str(mark))
run = OUT / "page_run.html"; run.write_text(page)
print("end", END, verse)

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

# ---------- sound: soft night ambience, a bloom for every star ----------
def time_at(a):
    for (t0, a0), (t1, a1) in zip(KF, KF[1:]):
        if a <= a1: return t0 + (t1 - t0) * max(0, (a - a0) / (a1 - a0))
    return KF[-1][0]
N = int(END * SR); L = np.zeros(N); R = np.zeros(N); rng = np.random.default_rng(7)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f): return sosfilt(butter(2, f, btype="low", fs=SR, output="sos"), x)
def db(d): return 10 ** (d / 20)
def add(sig, t0, g, pan=0.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if 0 <= i < N: s = sig[:j - i] * g; L[i:j] += s * np.sqrt((1 - pan) / 2) * 1.41; R[i:j] += s * np.sqrt((1 + pan) / 2) * 1.41
def env(n, a, r): e = np.ones(n); na, nr = max(1, int(a * SR)), max(1, int(r * SR)); e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
tt = np.arange(N) / SR
pad = sum(np.sin(2 * np.pi * f * tt + k) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / (9 + 2 * k))) for k, f in enumerate([55, 82.4, 110, 164.8]))
add(lp(pad, 400) / 4 * env(N, 4, 3), 0, db(-35))
def bloom(t0, g, low=120, hi=1400, dur=1.6):
    n = int(dur * SR); x = np.linspace(0, 1, n)
    add(lp(bp(rng.standard_normal(n), low, hi), 900) * (x ** .8) * (1 - x) ** 1.8 * 4, t0 - .2, g, rng.uniform(-.3, .3))
for p in people:
    if p["to"] < 63.6:
        t0 = time_at(p["to"])
        if p["id"] == "prophet": bloom(t0, db(-24), 60, 900, 3.2)
        else: bloom(t0, db(-30))
# light rain until the verse, none under the recitation. Owner, 19 Nov: synthesised rain sounded like static, wind, then
# nothing like rain, so this is a real recording: "Rain (loopable)" no. 4 by Ylmir, OpenGameArt, CC0 (rain_cc0_ylmir.mp3),
# the lightest of the four. Looped with a 2 s crossfade, rumble below 150 Hz removed.
n = int((REC_T - .2) * SR)
rr = subprocess.run(["ffmpeg", "-v", "error", "-i", str(HERE / "rain_cc0_ylmir.mp3"), "-af", "highpass=f=150", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
rain = np.frombuffer(rr, np.float32).astype(float).reshape(-1, 2); xf = int(2 * SR); w = np.linspace(0, 1, xf)[:, None]
loop = rain.copy()
while len(loop) < n:
    loop = np.concatenate([loop[:-xf], loop[-xf:] * (1 - w) + rain[:xf] * w, rain[xf:]])
loop = loop[:n] * env(n, 3, 1.8)[:, None]; RAIN_UNDER_REC = 30   # dB below the recitation's level
_rr = subprocess.run(["ffmpeg", "-v", "error", "-i", str(REC / "021107.mp3"), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
_x = np.frombuffer(_rr, np.float32).astype(float); rec_rms = np.sqrt((_x[np.abs(_x) > 1e-3] ** 2).mean()) / np.abs(_x).max() * db(-4)
loop /= np.sqrt((loop ** 2).mean()) / (rec_rms * db(-RAIN_UNDER_REC))
L[:n] += loop[:, 0]; R[:n] += loop[:, 1]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(REC / "021107.mp3"), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
rec = np.frombuffer(raw, np.float32).astype(float)[:int((AL[-1][3] / 1000 + .5) * SR)]; rec *= env(len(rec), .02, .45)
add(rec / np.abs(rec).max(), REC_T, db(-4))
bloom(SC["const"], db(-31), 200, 2000, 2.2); bloom(SC["fat"], db(-33)); bloom(SC["verse"], db(-31), 100, 1200, 2.4); bloom(SC["logo"] + .1, db(-30))
mix = np.stack([lp(L, 11000), lp(R, 11000)], 1); f = int(1.2 * SR); mix[-f:] *= np.linspace(1, 0, f)[:, None]
i0, i1 = int(REC_T * SR), int(REC_END * SR); seg = mix[i0:i1]
mix *= db(-15) / np.sqrt((seg[np.abs(seg) > 1e-3] ** 2).mean())        # recitation at about -15 dBFS RMS
pk = np.abs(mix).max(); mix *= min(1, db(-1) / pk)
wavfile.write(OUT / "amb.wav", SR, (mix * 32767).astype(np.int16))

video = OUT / "prophet_losses.mp4"; tmp = OUT / "prophet_losses_tmp.mp4"
if "--audio-only" in sys.argv:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(OUT / "amb.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)], check=True); tmp.rename(video)
    print(json.dumps({"ok": True, "video": str(video), "audio_only": True})); sys.exit(0)
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-", "-i", str(OUT / "amb.wav"),
                       "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                       "-t", f"{END:.2f}", "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE)
for _, buf in shots([i / FPS for i in range(int(round(END * FPS)))]):
    ff.stdin.write(buf)
ff.stdin.close(); assert ff.wait() == 0; tmp.rename(video)
print(json.dumps({"ok": True, "video": str(video), "seconds": END}))
