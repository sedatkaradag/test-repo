"""Bukhari 1968 story Reel (sample): Kokoro narration + flat illustrated scenes + word-by-word captions.
python3 make_story.py <out_dir> <until_seconds or 0 for all>"""
import json, re, subprocess, sys, wave, numpy as np, soundfile as sf
from pathlib import Path
HERE = Path(__file__).parent; TTS = HERE / "tts"; OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
UNTIL = float(sys.argv[2]) if len(sys.argv) > 2 else 0
FPS, SR = 30, 24000
S = json.load(open(HERE / "script.json"))
hook, body, outro = (json.load(open(TTS / f"{n}.json")) for n in ("hook", "body", "outro"))
HOOK0 = 0.5; BODY0 = round(HOOK0 + hook["duration"] + 0.35, 3)

# word timings: every display word gets the time of its spoken words (Kokoro tokens, punctuation skipped)
toks = [t for t in body["tokens"] if t["text"] != "<line>" and re.search(r"[A-Za-z0-9]", t["text"] or "")]
words, k = [], 0
for w in S["words"]:
    n = len([x for x in w["s"].split() if re.search(r"[A-Za-z0-9]", x)])
    if n == 0:
        words.append({"d": w["d"], "n": 0}); continue
    seg = toks[k:k + n]; k += n
    for x, sw in zip(seg, [x for x in w["s"].split() if re.search(r"[A-Za-z0-9]", x)]):
        assert re.sub(r"[^a-z]", "", x["text"].lower()) == re.sub(r"[^a-z]", "", sw.lower()), (x["text"], sw)
    words.append({"d": w["d"], "t0": BODY0 + seg[0]["start"], "t1": BODY0 + seg[-1]["end"]})
assert k == len(toks), (k, len(toks))
for i, w in enumerate(words):              # a word with nothing spoken (the split "Ad-") shares the next word's time
    if "t0" not in w:
        nx = next(x for x in words[i + 1:] if "t0" in x); w["t0"], w["t1"] = nx["t0"], nx["t1"]
# the source has "Juhaifa:The" with no space: shown as two caption words with no space between them
for i, w in enumerate(words):
    w["glue"] = (w["d"] == "Juhaifa:" and words[i + 1]["d"] == "The")

# caption chunks: up to 6 words / 34 letters, a new chunk after a sentence or clause end
chunks, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    txt = " ".join(x["d"] for x in cur)
    end_clause = re.search(r'[.,;:?!]["”\']?$', w["d"]) is not None
    nxt = words[i + 1]["d"] if i + 1 < len(words) else None
    if nxt is None or end_clause or len(cur) >= 6 or len(txt) + 1 + len(nxt) > 34:
        chunks.append(cur); cur = []
CH = []
for j, c in enumerate(chunks):
    start = c[0]["t0"] - 0.08
    end = chunks[j + 1][0]["t0"] - 0.08 if j + 1 < len(chunks) else c[-1]["t1"] + 0.5
    CH.append({"id": j, "start": round(start, 3), "end": round(end, 3),
               "words": [{"d": w["d"], "t0": round(w["t0"], 3), "t1": round(max(w["t1"], w["t0"] + 0.12), 3), "glue": w["glue"]} for w in c]})

# hook / outro words with their spoken times (the text is ours, shown big at the top)
def timed(text, part, t0):
    tk = [x for x in part["tokens"] if x["text"] != "<line>" and re.search(r"[A-Za-z0-9]", x["text"] or "")]
    ws = text.split(" "); assert len(ws) == len(tk), (ws, [x["text"] for x in tk])
    return [{"d": w, "t0": round(t0 + x["start"], 3), "t1": round(t0 + x["end"], 3)} for w, x in zip(ws, tk)]
OUTRO0 = round(BODY0 + body["duration"] + 0.5, 3)
END0 = round(OUTRO0 + outro["duration"] + 0.4, 3)
hookW, outroW = timed(S["hook"], hook, HOOK0), timed(S["outro"], outro, OUTRO0)
at = lambda i: round(words[i]["t0"], 3)
cue = {"umm": at(25) - 0.3, "ate": at(97), "got1": at(113), "sleep1": at(125), "got2": at(136), "sleep2": at(143)}
cuts = [0, 12, 55, 100, 144, 167, 208]
bounds = [0.0] + [round(at(i) - 0.25, 2) for i in cuts[1:]] + [round(OUTRO0 - 0.3, 2)]
scenes = [{"id": f"scene{j + 1}", "t0": bounds[j], "t1": bounds[j + 1]} for j in range(7)]
scenes[0]["first"] = True
scenes.append({"id": "scene8", "t0": bounds[-1], "t1": 9999})
END = UNTIL or (END0 + 3.6)
# audio
def load(n):
    a, sr = sf.read(TTS / f"{n}.wav" if (TTS / f"{n}.wav").exists() else TTS / f"{n}.flac", dtype="float32"); assert sr == SR; return a
mix = np.zeros(int((END + 1) * SR), dtype=np.float32)
def add(t, a):
    i = int(t * SR); a = a[: max(0, len(mix) - i)]; mix[i:i + len(a)] += a
add(HOOK0, load("hook")); add(BODY0, load("body")); add(OUTRO0, load("outro"))
mix *= 0.89 / max(1e-6, np.abs(mix).max())
with wave.open(str(OUT / "audio.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())

data = {"hookWords": hookW, "outroWords": outroW, "outro0": OUTRO0, "end0": END0, "cue": cue, "hookEnd": round(BODY0 - 0.2, 2), "chunks": CH, "scenes": scenes}
(HERE / "page_run.html").write_text((HERE / "page.html").read_text().replace("__DATA__", json.dumps(data)))
from playwright.sync_api import sync_playwright
video = OUT / "salman_abu_darda_bukhari1968.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                       "-i", str(OUT / "audio.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-t", f"{END:.2f}",
                       "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)
marks = [2.0, 4.0, BODY0 + 1.5] + [s["t0"] + 1.5 for s in scenes[1:]] + [cue["got1"] + 0.3, cue["sleep1"] + 1.5, scenes[4]["t0"] + 5, OUTRO0 + 2, END - 0.2]
(OUT / "frames").mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto(f"file://{HERE / 'page_run.html'}"); pg.evaluate("window.ready"); pg.wait_for_timeout(300)
    for i in range(int(round(END * FPS))):
        t = i / FPS; pg.evaluate(f"window.render({t})"); jpg = pg.screenshot(type="jpeg", quality=92); ff.stdin.write(jpg)
        for m in list(marks):
            if abs(t - m) < 0.5 / FPS: (OUT / "frames" / f"f_{m:05.2f}.jpg").write_bytes(jpg); marks.remove(m)
    b.close()
ff.stdin.close(); ff.wait()
print("ok", video, round(END, 1), scenes)
