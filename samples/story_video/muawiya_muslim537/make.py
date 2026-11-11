"""Muslim 537 Reel: Kokoro narration, back-view prayer rows, Arabic cards, word-by-word captions.
python3 make.py <out_dir> [until]"""
import json, re, subprocess, sys, wave, numpy as np, soundfile as sf
from pathlib import Path
HERE = Path(__file__).parent; TTS = HERE / "tts"; OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
UNTIL = float(sys.argv[2]) if len(sys.argv) > 2 else 0
FPS, SR = 30, 24000
S = json.load(open(HERE / "script.json"))
P = {n: json.load(open(TTS / f"{n}.json")) for n in ("hook", "body", "note", "outro")}
ALNUM = lambda x: re.search(r"[A-Za-z0-9]", x or "") is not None
def toks(part): return [t for t in P[part]["tokens"] if t["text"] != "<line>" and ALNUM(t["text"])]
def same(a, b): return re.sub(r"[^a-z]", "", a.lower()) == re.sub(r"[^a-z]", "", b.lower())

HOOK0 = 0.5
BODY0 = round(HOOK0 + P["hook"]["duration"] + 0.45, 3)
NOTE0 = round(BODY0 + P["body"]["duration"] + 0.6, 3)
OUTRO0 = round(NOTE0 + P["note"]["duration"] + 0.9, 3)
END0 = round(OUTRO0 + P["outro"]["duration"] + 0.4, 3)
END = UNTIL or (END0 + 3.6)

# hadith words: every shown word gets the time of its spoken words
tk, words, k = toks("body"), [], 0
for w in S["words"]:
    sw = [x for x in w["s"].split() if ALNUM(x)]
    seg = tk[k:k + len(sw)]; k += len(sw)
    for x, s in zip(seg, sw): assert same(x["text"], s), (x["text"], s)
    words.append({"d": w["d"], "t0": round(BODY0 + seg[0]["start"], 3), "t1": round(BODY0 + seg[-1]["end"], 3)})
assert k == len(tk)
# our own lines (hook / note / outro)
def ours(text, spoken, part, t0):
    tk, out, k = toks(part), [], 0
    for d in text.split(" "):
        n = 4 if d == "ﷺ" else 1
        seg = tk[k:k + n]; k += n
        if d != "ﷺ": assert same(seg[0]["text"], d), (seg[0]["text"], d)
        out.append({"d": d, "t0": round(t0 + seg[0]["start"], 3), "t1": round(t0 + seg[-1]["end"], 3)})
    assert k == len(tk), (text, k, len(tk))
    return out
hookW = ours(S["hook"], S["hook_spoken"], "hook", HOOK0)
noteW = ours(S["note"], S["note"], "note", NOTE0)
outroW = ours(S["outro"], S["outro"], "outro", OUTRO0)

# cards (Arabic straight from the source, English = the shown words of that range)
cards, inside = {}, set()
for c in S["cards"]:
    a, b = c["range"]; inside.update(range(a, b + 1))
    ws = words[a:b + 1]
    show = [[max(ws[0]["t0"] - 0.45, words[a - 1]["t1"] + 0.05), ws[-1]["t1"] + 0.55]]
    card = {"words": [{"d": w["d"], "t0": w["t0"], "t1": w["t1"]} for w in ws], "show": show}
    if "arabic" in c: card["arabic"] = c["arabic"]
    if "arabic_lines" in c:
        card["lines"] = []
        lw_ts = [next(x for x in ws if x["d"] == lw) for lw in c["line_words"]]
        for j, (ar, lw) in enumerate(zip(c["arabic_lines"], c["line_words"])):
            w = lw_ts[j]
            stop = min(w["t1"] + 0.35, lw_ts[j + 1]["t0"] - 0.05) if j + 1 < len(lw_ts) else w["t1"] + 0.35
            rep = NOTE0 + 0.9 + j * 0.75                                           # the reprise under "Look at the three things…"
            card["lines"].append({"ar": ar, "label": lw.rstrip(","), "times": [[w["t0"] - 0.05, stop], [rep, rep + 0.7]]})
        card["show"].append([NOTE0 - 0.4, OUTRO0 - 0.5])
    cards[c["id"]] = card

# captions for the words that are not on a card
chunks, cur = [], []
def flush():
    global cur
    if cur: chunks.append(cur); cur = []
for i, w in enumerate(words):
    if i in inside: flush(); continue
    cur.append(w)
    nxt = words[i + 1]["d"] if i + 1 < len(words) else None
    txt = " ".join(x["d"] for x in cur)
    clause = re.search(r'[.,;:?!]["”\')]*$', w["d"]) and w["d"] != "b."
    if nxt is None or clause or len(cur) >= 7 or len(txt) + 1 + len(nxt) > 40 or (i + 1) in inside:
        flush()
flush()
CH = []
for j, c in enumerate(chunks):
    nxt_t = chunks[j + 1][0]["t0"] if j + 1 < len(chunks) else c[-1]["t1"] + 0.6
    end = min(nxt_t, c[-1]["t1"] + 0.9) - 0.06
    for cd in cards.values():                     # a caption leaves before a card comes in
        s0 = cd["show"][0][0]
        if c[0]["t0"] < s0 < end: end = s0
    CH.append({"id": j, "start": round(c[0]["t0"] - 0.08, 3), "end": round(end, 3), "words": c})

def at(text, n=1):
    hits = [w for w in words if w["d"] == text]; return hits[n - 1]["t0"]
cue = {"mu": words[0]["t0"] - 0.1, "sneezed": at("sneezed.") + 0.25, "stared": at("stared"),
       "strike": at("strike"), "silence": at("silence"), "calm": at("When", 1) - 0.2}
yr = S["yar"]["range"]
yar = {"arabic": S["yar"]["arabic"], "t0": words[yr[0]]["t0"], "t1": words[yr[1]]["t1"] + 0.8}

# audio
mix = np.zeros(int((END + 1) * SR), dtype=np.float32)
def add(t, n):
    a, sr = sf.read(TTS / f"{n}.wav", dtype="float32"); assert sr == SR
    i = int(t * SR); a = a[: max(0, len(mix) - i)]; mix[i:i + len(a)] += a
add(HOOK0, "hook"); add(BODY0, "body"); add(NOTE0, "note"); add(OUTRO0, "outro")
mix *= 0.89 / max(1e-6, np.abs(mix).max())
with wave.open(str(OUT / "audio.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())

tch, thr = cards["teacher"]["show"][0], cards["three"]["show"][0]
cuts = [("wide", 0.0), ("medium", cue["mu"] - 0.15), ("look", cue["stared"] - 0.35), ("hands", cue["strike"] - 0.35),
        ("wide", cue["calm"]), ("medium", tch[1] - 0.2), ("wide", thr[0] + 0.1)]
shots = [{"kind": k, "t0": round(t0, 3), "t1": round(cuts[i + 1][1] if i + 1 < len(cuts) else 9999, 3), "bow": k == "medium" and i > 1}
         for i, (k, t0) in enumerate(cuts)]
logo = sorted((Path("/home/claude/test-repo/samples/logo_draw/frames_800")).iterdir())[-1].name
data = {"hookW": hookW, "noteW": noteW, "outroW": outroW, "hookEnd": round(BODY0 - 0.25, 2), "note0": NOTE0, "note1": OUTRO0 - 0.5,
        "outro0": OUTRO0, "end0": END0, "chunks": CH, "cards": cards, "cue": cue, "yar": yar, "shots": shots}
html = (HERE / "page.html").read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__LOGO__", logo)
(HERE / "page_run.html").write_text(html)
json.dump(data, open(OUT / "timeline.json", "w"), ensure_ascii=False, indent=0)
if "--no-video" in sys.argv: sys.exit(0)
from playwright.sync_api import sync_playwright
video = OUT / "muawiya_muslim537.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                       "-i", str(OUT / "audio.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-t", f"{END:.2f}",
                       "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto(f"file://{HERE / 'page_run.html'}"); pg.evaluate("window.ready"); pg.wait_for_timeout(300)
    # the rows that never move are drawn once per kind of shot and reused as pictures
    layers = {}
    for kind in sorted({s["kind"] for s in shots if s["kind"] != "hands"}):
        layers[kind] = {}
        for part in ("far", "near"):
            pg.evaluate(f"window.prepLayer('{kind}', '{part}')"); pg.wait_for_timeout(100)
            f = OUT / f"layer_{kind}_{part}.png"
            pg.screenshot(path=str(f), omit_background=(part == "near"))
            layers[kind][part] = f"file://{f.resolve()}"
    pg.evaluate(f"window.endPrep({json.dumps(layers)})")
    for s in shots:                                   # show each shot once so its pictures are loaded before recording
        if s["kind"] != "hands": pg.evaluate(f"window.render({s['t0'] + 0.5})"); pg.wait_for_timeout(400)
    START = float(dict(a.split('=') for a in sys.argv if a.startswith('start=')).get('start', 0))
    for i in range(int(round(START * FPS)), int(round(END * FPS))):
        pg.evaluate(f"window.render({i / FPS})"); ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
    b.close()
ff.stdin.close(); ff.wait()
print("ok", video, round(END, 1))
