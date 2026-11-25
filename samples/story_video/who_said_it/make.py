"""'Who said it?' (remake of the reel DfR8FsygV58, owner's pick 25 Nov; reciters and verses free, our closing at the end).
python3 make.py <out_dir> [--stills=t1,...]

Three rounds: the quoted words of a verse (an exact slice of find.py's Arabic, from the first word of the quote to the end
of the verse, and the quoted part of find.py's English) are recited and light word by word (our soft light), then a
timer, then the answer. Each round has its own reciter, all studio recordings with word timings (quran-align):
  1 Alafasy 21:87 (Yunus)   2 Minshawi 12:18 (Ya'qub)   3 Husary 37:102 (Ismail answering his father)
The audio starts in the quietest moment around quran-align's start of the quote's first word; it ends where the voice ends (found from the sound,
quran-align ends early on long madds). Every cut was checked by speech-to-text. Abdul Basit was dropped: his quran-align
timings are ~6 s off this everyayah file (align ends at 54 s, the file is 46 s).
Audio files: /tmp/a_<reciter>/ (audio-fetch, drafts-audio).
"""
import io, json, re, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
STILLS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--stills=")), None)
FPS, SR = 30, 48000
GAP, THINK, REVEAL, FIRST = .35, 3.0, 3.0, .8
ROUNDS = [  # reciter dir, display name, surah, verse, first word of the quote (1-based), options, answer, who line, ref
    ("Alafasy_128kbps", "Mishary Alafasy", 21, 87, 15, ["Musa", "Yunus", "Ayyub", "Ibrahim"], 1, "Yunus, calling on his Lord", "Al-Anbiya 21:87"),
    ("Minshawy_Murattal_128kbps", "Mohamed Siddiq Al-Minshawi", 12, 18, 6, ["Yusuf", "Ibrahim", "Ya'qub", "Nuh"], 2, "Ya'qub, to his sons", "Yusuf 12:18"),
    ("Husary_128kbps", "Mahmoud Khalil Al-Husary", 37, 102, 17, ["Ibrahim", "Ishaq", "Yusuf", "Ismail"], 3, "Ismail, to his father", "As-Saffat 37:102"),
]

def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)

rounds, clips, t = [], [], FIRST
for rec, name, s, v, w0, opts, ans, who, ref in ROUNDS:
    d = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", f"quran:{s}:{v}"], capture_output=True, text=True, check=True).stdout)
    words = re.sub(r"[\s ]*[٠-٩]+\s*$", "", d["arabic_display"]).strip().split(" ")
    key = f"{s:03d}{v:03d}"; al = json.load(open(f"/tmp/a_{rec}/align.json"))[key]
    assert len(words) == len(al), (key, len(words), len(al))
    x = load(f"/tmp/a_{rec}/audio/{key}.mp3"); assert al[-1][3] / 1000 <= len(x) / SR + .3, ("align runs past the file", rec, key)
    en = d["english"]; q = en.find("He said,") if (s, v) == (12, 18) else en.rfind("“") + 1   # an exact slice of find.py's English
    en_q = en[q:].rstrip().rstrip("”").strip()
    hop = SR // 100; e = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
    # start at quran-align's start of the first word, skipping any silence before the voice. Minshawi reads "qala bal"
    # in one breath (no pause to cut at, and quran-align puts "qala" inside the pause before it), so round 2 starts
    # at "qala" itself and its English at "He said," (speech-to-text, 25 Nov). Alafasy's "an la" is joined by idgham:
    # starting at "la" is clean.
    a0 = al[w0 - 1][2] / 1000; k = int(a0 * 100)
    while k < len(e) and 20 * np.log10(e[k] / e.max() + 1e-9) < -35: k += 1
    a0 = max(a0, k / 100 - .02)
    act = np.where(20 * np.log10(e / e.max() + 1e-9) > -40)[0]; s_end = (act[-1] + 1) * hop / SR
    clip = x[int(a0 * SR):int(min(len(x) / SR, s_end + .15) * SR)].copy()
    f = int(.03 * SR); clip[:f] *= np.linspace(0, 1, f); f = int(.12 * SR); clip[-f:] *= np.linspace(1, 0, f)
    # word light: from speech-to-text on this exact clip (word_times.json), not quran-align: on 25 Nov quran-align was
    # off from the voice by up to 2.7 s (Minshawi 12:18) and 3.2 s (Husary 37:102); Alafasy within 0.3 s.
    wavfile.write(OUT / f"clip_{len(rounds)}.wav", 16000, (np.interp(np.arange(0, len(clip), SR / 16000), np.arange(len(clip)), clip) * 32767).astype(np.int16))
    WT = json.load(open(HERE / "word_times.json")) if (HERE / "word_times.json").exists() else {}
    if key in WT:
        assert len(WT[key]) == len(words) - w0 + 1, (key, len(WT[key]))
        ws = [{"s": round(t + a, 3), "e": round(t + b, 3)} for a, b in WT[key]]
    else:
        ws = [{"s": round(t + (b0 / 1000 - a0), 3), "e": round(t + (b1 / 1000 - a0), 3)} for _, _, b0, b1 in al[w0 - 1:]]
    ws[-1]["e"] = round(max(ws[-1]["e"], t + s_end - a0 - .15), 3)
    rec_end = t + len(clip) / SR; think = rec_end + GAP; reveal = think + THINK; t1 = reveal + REVEAL
    rounds.append({"ar": " ".join(words[w0 - 1:]), "en": en_q, "en_open": not en_q.startswith("He said"), "options": opts, "answer": ans, "who": who, "ref": ref, "reciter": name,
                   "words": ws, "t0": round(t, 3), "think": round(think, 3), "reveal": round(reveal, 3), "t1": round(t1, 3)})
    clips.append((t, clip)); t = t1 + .5
LOGO = round(rounds[-1]["t1"], 2); END = LOGO + 3.4

N = int(END * SR); mono = np.zeros(N)
for t0, c in clips:
    seg = c / np.sqrt((c[np.abs(c) > 1e-3] ** 2).mean()) * 10 ** (-17 / 20)   # the three reciters at one level
    i = int(t0 * SR); mono[i:i + len(seg)] += seg
mono *= min(1, 10 ** (-1 / 20) / np.abs(mono).max())

logo = [str(p) for p in sorted((REPO / "samples/logo_draw/frames_800").iterdir())]
page = (HERE / "page.html").read_text().replace("__DATA__", json.dumps({"rounds": rounds, "logo": LOGO, "logo_frames": logo}, ensure_ascii=False)).replace("__REPO__", str(REPO))
run = OUT / "page_run.html"; run.write_text(page)
print("end", round(END, 2), [(r["ref"], r["t0"], r["think"], r["reveal"], r["t1"]) for r in rounds])

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
video = OUT / "who_said_it.mp4"; tmp = OUT / "who_said_it_tmp.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-", "-i", str(OUT / "rec.wav"),
                       "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                       "-t", f"{END:.2f}", "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE)
for _, buf in shots([i / FPS for i in range(int(round(END * FPS)))]): ff.stdin.write(buf)
ff.stdin.close(); assert ff.wait() == 0; tmp.rename(video)
print(json.dumps({"ok": True, "video": str(video), "seconds": round(END, 2)}))
