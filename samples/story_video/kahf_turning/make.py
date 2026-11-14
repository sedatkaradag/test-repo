"""Kahf 18:18 'turned right and left' explainer (English TTS remake of the owner's reference video, 14 Nov).
python3 make.py <out_dir> [--stills=t1,t2,...]      (narration in tts/, recitation dir in $AUD or /home/claude/kahf/aud)

Verse text (Arabic and English) only from scripts/find.py, cut by word position, never typed.
Narration: Kokoro bm_george 0.95 (tts/<id>.flac + .json word times). Recitation: Alafasy 18:18, words 4-8.
"""
import json, os, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
STILLS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--stills=")), None)
AUD = Path(os.environ.get("AUD", "/home/claude/kahf/aud"))
FPS, SR = 30, 48000

# ---------- verse from the database ----------
v = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", "quran:18:18"], capture_output=True, text=True, check=True).stdout)
AR = v["arabic_display"].split()
assert len(AR) == 23 and AR[-1] == "١٨", len(AR)
EN = v["english"]
EN_CARD = EN[:EN.index("entrance.") + len("entrance.")]          # first three sentences, as in the reference
TURN = "We turned them over on their right and left sides"
DOGW = "stretching its forelegs"
assert TURN in EN_CARD and DOGW in EN_CARD

# ---------- narration timeline ----------
lines = {L["id"]: L["text"] for L in json.load(open(HERE / "tts/lines.json"))}
ORDER = ["hook1", "hook2", "intro", "verse", "ref", "notice", "REC1", "turn", "why", "medicine", "vessels", "oxygen",
         "ulcer", "rule", "detail", "dog1", "dog2", "whydog", "sphinx", "nosore", "protect", "REC2", "outro"]
GAP = {"hook2": .45, "intro": .55, "verse": .35, "ref": .45, "notice": .7, "REC1": .35, "turn": .35, "why": .7,
       "medicine": .5, "vessels": .6, "oxygen": .3, "ulcer": .35, "rule": .7, "detail": .8, "dog1": .4, "dog2": .35,
       "whydog": .6, "sphinx": .6, "nosore": .5, "protect": .7, "REC2": .4, "outro": .8}
al = json.load(open(AUD / "align.json"))["018018"]
REC_A, REC_B = al[4][2] / 1000, al[8][3] / 1000            # words 4-8: wa-nuqallibuhum ... ash-shimal
REC_WORDS = [(w[0], w[2] / 1000 - REC_A, w[3] / 1000 - REC_A) for w in al[4:9]]

t, segs, words = .35, [], {}
for sid in ORDER:
    t += .7 * GAP.get(sid, 0)
    if sid.startswith("REC"):
        segs.append({"id": sid, "t0": round(t, 3), "t1": round(t + REC_B - REC_A, 3), "kind": "rec"})
        words[sid] = [{"w": f"ar{i}", "s": round(t + a, 3), "e": round(t + b, 3)} for i, a, b in REC_WORDS]
        t += REC_B - REC_A
        continue
    j = json.load(open(HERE / f"tts/{sid}.json"))
    tk = [x for x in j["tokens"] if x["start"] is not None and x["text"].strip()]
    a, b = max(0, tk[0]["start"] - .06), min(j["duration"], max(x["end"] for x in tk) + .12)
    segs.append({"id": sid, "t0": round(t, 3), "t1": round(t + b - a, 3), "kind": "tts", "a": a, "b": b})
    words[sid] = [{"w": x["text"], "s": round(t + x["start"] - a, 3), "e": round(t + x["end"] - a, 3)} for x in tk]
    t += b - a
END = round(t + 2.8, 2)

def T(sid, word, nth=0, end=False):
    """Global time of the nth token in line sid that starts with `word` (case-insensitive)."""
    hits = [x for x in words[sid] if x["w"].lower().strip(",.:;?!'\"") == word.lower()]
    assert len(hits) > nth, (sid, word, [x["w"] for x in words[sid]])
    return hits[nth]["e" if end else "s"]

S = {s["id"]: s for s in segs}
# Arabic of the verse card: word groups revealed with the English that carries them
CARD_AR = [(0, T("verse", "You")), (1, T("verse", "awake")), (2, T("verse", "although")), (3, T("verse", "asleep")),
           (4, T("verse", "We")), (5, T("verse", "right")), (6, T("verse", "right")), (7, T("verse", "left")),
           (8, T("verse", "sides")), (9, T("verse", "dog")), (10, T("verse", "stretching")), (11, T("verse", "forelegs")),
           (12, T("verse", "entrance"))]
CARD_GOLD = {5, 6, 7, 8, 10, 11}
en_tokens = [{"w": x["w"], "s": x["s"]} for x in words["verse"]]
assert "".join(x["w"] for x in en_tokens).replace(" ", "") == EN_CARD.replace(" ", ""), "English card text must be the source text"

data = {
    "end": END,
    "segs": segs,
    "words": words,
    "ar": AR,
    "card": {"ar": [{"i": i, "t": tt, "gold": i in CARD_GOLD} for i, tt in CARD_AR], "en": en_tokens,
             "gold": ["right", "left", "turned", "forelegs", "stretching"]},
    "turn_ar": [4, 5, 6, 7, 8],
    "dog_ar": [10, 11],
    "turn_en": TURN, "dog_en": DOGW,
    "cues": {
        # scene starts
        "s_hook": 0, "s_icu": S["hook2"]["t0"] - .2, "s_surah": S["intro"]["t0"] - .25, "s_card": S["verse"]["t0"] - .35,
        "s_notice": S["notice"]["t0"] - .35, "s_why": S["why"]["t0"] - .3, "s_med": S["medicine"]["t0"] - .3,
        "s_tissue": S["vessels"]["t0"] - .3, "s_rule": S["rule"]["t0"] - .35, "s_detail": S["detail"]["t0"] - .4,
        "s_whydog": S["whydog"]["t0"] - .3, "s_sphinx": S["sphinx"]["t0"] - .3, "s_nosore": S["nosore"]["t0"] - .25,
        "s_protect": S["protect"]["t0"] - .35, "s_logo": S["outro"]["t0"] - .3,
        # hook
        "h_l1": .15, "h_l2": T("hook1", "turn"), "h_x": T("hook1", "left"), "h_spots": T("hook1", "body"),
        "h_l3": T("hook1", "body"),
        # icu
        "i_l1": T("hook2", "used"), "i_l2": T("hook2", "vital"), "i_turn": T("hook2", "intensive"),
        "i_l3": T("hook2", "Surah"), "i_l4": T("hook2", "word"),
        # surah title
        "su_ar": S["intro"]["t0"], "su_en": T("intro", "Surah"), "su_v": T("intro", "eighteen"), "su_cave": T("intro", "young"),
        "su_cap": T("intro", "asleep"),
        # notice
        "n_title": S["notice"]["t0"], "n_ar": S["REC1"]["t0"] - .3, "n_body": S["REC1"]["t0"], "n_en": S["turn"]["t0"],
        # why
        "w_l1": T("why", "In"), "w_l2": T("why", "why"), "w_l3": T("why", "turned"), "w_q": T("why", "left"),
        # medicine
        "m_tag": S["medicine"]["t0"], "m_l1": T("medicine", "this"), "m_l2": T("medicine", "vital"),
        # tissue
        "t_l1": T("vessels", "same"), "t_l2": T("vessels", "still"), "t_bone": T("vessels", "bones"),
        "t_floor": T("vessels", "surface"), "t_press": T("vessels", "caught"), "t_block": T("vessels", "blocked"),
        "t_l3": T("vessels", "blocked"), "t_oxy": T("oxygen", "Oxygen"), "t_dead": T("ulcer", "tissue"),
        "t_ulcer": T("ulcer", "decubitus"), "t_bedsore": T("ulcer", "bedsore"), "t_clot": T("ulcer", "clotting"),
        # rule
        "r_body": S["rule"]["t0"], "r_l0": T("rule", "intensive"), "r_l1": T("rule", "keeping"), "r_l2": T("rule", "basic"), "r_clock": T("rule", "regular"),
        "r_l3": T("rule", "regular"), "r_turn": T("rule", "turn"), "r_l4": T("rule", "turn"),
        # detail / dog
        "d_title": S["detail"]["t0"], "d_body": T("dog1", "young"), "d_lab": T("dog1", "turned"), "d_dog": T("dog1", "dog"),
        "d_ar": T("dog1", "stretching"), "d_en": T("dog1", "stretching"), "d_x": T("dog2", "not"), "d_lab2": T("dog2", "dog"),
        "wd_l1": T("whydog", "why"), "wd_l2": T("whydog", "but"), "wd_q": T("whydog", "dog"),
        # sphinx
        "sp_tag": S["sphinx"]["t0"], "sp_l1": T("sphinx", "chest"), "sp_legs": T("sphinx", "forelegs"),
        "sp_l2": T("sphinx", "sphinx"), "sp_arrows": T("sphinx", "weight"), "sp_l3": T("sphinx", "weight"),
        "sp_l4": T("sphinx", "vessels"),
        "ns_l1": T("nosore", "In"), "ns_l2": T("nosore", "bedsores"),
        "p_l1": T("protect", "turning"), "p_dog": T("protect", "posture"), "p_l2": T("protect", "posture"),
        "p_ar": S["REC2"]["t0"] - .2, "p_en": S["REC2"]["t1"] - 1.2,
        "logo_draw": S["outro"]["t0"],
    },
}
logo = sorted((REPO / "samples/logo_draw/frames_800").iterdir())
data["logo_frames"] = [str(p) for p in logo]
page = (HERE / "page.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__HERE__", str(HERE)).replace("__REPO__", str(REPO))
run = OUT / "page_run.html"; run.write_text(page, encoding="utf-8")
json.dump({k: data[k] for k in ("end", "segs", "cues")}, open(OUT / "timeline.json", "w"), indent=1)
print("end", END, "s")

from playwright.sync_api import sync_playwright

def shots(ts, size=(1080, 1920)):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(400)
        for t in ts:
            pg.evaluate(f"window.render({t})"); yield t, pg.screenshot(type="jpeg", quality=90)
        b.close()

if STILLS:
    from PIL import Image
    import io
    ts = [float(x) for x in STILLS.split(",")]
    ims = []
    for t, buf in shots(ts):
        im = Image.open(io.BytesIO(buf)); im.save(OUT / f"s_{t:06.2f}.jpg", quality=88); ims.append(im.resize((360, 640)))
    cols = min(6, len(ims)); c = Image.new("RGB", (360 * cols, 640 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims): c.paste(im, ((i % cols) * 360, (i // cols) * 640))
    c.save(OUT / "sheet.jpg", quality=85); print("sheet", OUT / "sheet.jpg"); sys.exit(0)

# ---------- audio ----------
N = int(END * SR); nar = np.zeros(N); rec = np.zeros(N)
def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(float)
recit = load(AUD / "audio/018018.mp3")
for s in segs:
    i0 = int(s["t0"] * SR)
    if s["kind"] == "tts":
        x = load(HERE / f"tts/{s['id']}.flac")[int(s["a"] * SR):int(s["b"] * SR)]
        f = int(.02 * SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        nar[i0:i0 + len(x)] += x[:N - i0]
    else:
        x = recit[int(REC_A * SR) - int(.03 * SR):int(REC_B * SR) + int(.25 * SR)].copy()
        f = int(.03 * SR); x[:f] *= np.linspace(0, 1, f); f2 = int(.25 * SR); x[-f2:] *= np.linspace(1, 0, f2)
        i0 -= int(.03 * SR); rec[i0:i0 + len(x)] += x[:N - i0]
def rms(x): return np.sqrt((x[np.abs(x) > 1e-4] ** 2).mean())
nar *= .12 / rms(nar); rec *= .12 / rms(rec)          # same speech level for both
subprocess.run(["python3", str(HERE / "sound.py"), str(OUT / "fx.wav"), str(OUT / "timeline.json")], check=True)
sr2, fx = wavfile.read(OUT / "fx.wav"); fx = fx.astype(float) / 32768
fx = np.pad(fx, (0, max(0, N - len(fx))))[:N]
speech = np.abs(nar) + np.abs(rec)
env = np.convolve(speech, np.ones(int(.25 * SR)) / int(.25 * SR), mode="same")
duck = 1 - .55 * np.clip(env / .05, 0, 1)
mix = nar + rec + fx * duck
mix /= max(1.0, np.abs(mix).max() / .95)
wavfile.write(OUT / "mix_raw.wav", SR, (mix * 32767).astype(np.int16))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / "mix_raw.wav"), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SR),
                str(OUT / "mix.wav")], check=True)

# ---------- video ----------
video = OUT / "kahf_turning.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                       "-i", str(OUT / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{END:.2f}", "-movflags", "+faststart", str(video)],
                      stdin=subprocess.PIPE)
n = int(round(END * FPS))
for k, (t, buf) in enumerate(shots([i / FPS for i in range(n)])):
    ff.stdin.write(buf)
    if k % 300 == 0: print("frame", k, "/", n, flush=True)
ff.stdin.close(); assert ff.wait() == 0
print(json.dumps({"ok": True, "video": str(video), "seconds": END}))
