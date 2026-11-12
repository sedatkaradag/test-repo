"""Kishk "Death" test Reel (not for posting): sermon audio, our English subtitles, line drawings.
python3 make.py <out_dir> [until] [start=S] [--frames t1,t2,...]"""
import html, json, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).parent
REPO = HERE.parents[2]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
AUDIO = Path("/home/claude/kishk/audio.m4a")
FPS, END = 30, 171.0
args = [a for a in sys.argv[2:] if not a.startswith("--") and "=" not in a]
UNTIL = float(args[0]) if args else END
START = float(dict(a.split("=") for a in sys.argv if a.startswith("start=")).get("start", 0))
FRAMES = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--frames=")), None)

sys.path.insert(0, str(REPO / "scripts"))
q = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", "quran:40:16"], capture_output=True, text=True, check=True).stdout)
ar = q["arabic_display"]
W = ar.split()            # cut by word position from the source text, never typed
assert len(W) == 16 and W[-1] == "١٦", W
AR_DOM = " ".join(W[9:12])   # to whom is the dominion today
AR_FIN = " ".join(W[12:15])  # to Allah, the One, the Subjugator
SURAH = {"81": "AT-TAKWIR", "40": "GHAFIR"}

lines = []
for raw in (HERE / "lines.txt").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#"): continue
    parts = [p.strip() for p in raw.split("|")]
    t, text, vis = float(parts[0]), parts[1], parts[2]
    tag = parts[3] if len(parts) > 3 else ""
    scene = vis.split(":")[0]
    if scene in ("aod", "call", "ask", "four", "call4", "outj", "ask3", "three", "outm", "two", "outi", "call1", "ask1", "one", "call1b", "die", "die2", "dead", "smoke"):
        scene = "hall"
    if tag:   # verse lines must be verbatim from the database
        ref = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", f"quran:{tag}"], capture_output=True, text=True, check=True).stdout)["english"]
        assert text.replace("[", "").replace("]", "") in ref, (tag, text)
    h = html.escape(text).replace("[", "<em>").replace("]", "</em>")
    lines.append({"t": t, "html": h, "plain": text, "scene": scene, "tag": f"{SURAH[tag.split(':')[0]]} {tag}" if tag else ""})

def at(prefix, n=1):
    hits = [l["t"] for l in lines if l["plain"].startswith(prefix)]
    return hits[n - 1]
cue = {
    "nameJ": at("none is left but"), "nameM": at("[Mika'il]"), "nameI": at("and [Israfil]"),
    "outJ": at("So he [takes] the soul of Jibril") + .3, "outM": at("So he [takes] it.", 1) + .3, "outI": at("So he [takes] it.", 2) + .3,
    "zoom": at("Then [Allah] says to him:", 2), "die": at("“[Die]", 1), "dead": at("And the Angel of Death") + .5,
    "ruins": at("And Allah looks upon"),
}
lab = {"J": [[cue["nameJ"], cue["nameJ"] + 2.6], [at("“[Take] the soul of Jibril"), cue["outJ"]]],
       "M": [[cue["nameM"], cue["nameM"] + 2.6], [at("He says: “[Mika'il]"), at("He says: “[Mika'il]") + 2.4], [at("“Take the soul of [Mika'il]"), cue["outM"]]],
       "I": [[cue["nameI"], cue["nameI"] + 2.6], [at("“Take the soul of [Israfil]"), cue["outI"]]]}
ask = [[at("“Who is [left] of creation"), at("He says: “My [God]")], [at("“Who is [left]?”"), at("He says: “[Mika'il]")],
       [at("“Who is left of creation"), at("He says: “None")]]
calls = [at("[Allah] asks him"), at("Then [Allah] says to him:", 1), at("Then the [Compeller]"), at("Then [Allah] says to him:", 2), at("“[Die]", 2)]
data = {"lines": lines, "cue": cue, "lab": lab, "ask": ask, "calls": calls, "arDominion": AR_DOM, "arFinal": AR_FIN}
logo = sorted((REPO / "samples/logo_draw/frames_800").iterdir())[-1].name
page = (HERE / "page.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__LOGO__", logo)
run = OUT / "page_run.html"; run.write_text(page, encoding="utf-8")
json.dump(data, open(OUT / "timeline.json", "w"), ensure_ascii=False, indent=0)

from playwright.sync_api import sync_playwright
if FRAMES:
    from PIL import Image
    ts = [float(x) for x in FRAMES.split(",")]
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(400)
        ims = []
        for t in ts:
            pg.evaluate(f"window.render({t})"); f = OUT / f"f_{t:06.2f}.jpg"; pg.screenshot(path=str(f), type="jpeg", quality=88)
            ims.append(Image.open(f).resize((360, 640)))
        b.close()
    cols = min(6, len(ims)); c = Image.new("RGB", (360 * cols, 640 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims): c.paste(im, ((i % cols) * 360, (i // cols) * 640))
    c.save(OUT / "sheet.jpg", quality=85); print("sheet", OUT / "sheet.jpg"); sys.exit(0)

video = OUT / ("death_kishk.mp4" if START == 0 and UNTIL == END else f"part_{START:g}_{UNTIL:g}.mp4")
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                       "-ss", f"{START:.3f}", "-i", str(AUDIO), "-map", "0:v", "-map", "1:a", "-af", "apad",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-t", f"{UNTIL - START:.2f}", "-movflags", "+faststart", str(video)],
                      stdin=subprocess.PIPE)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(400)
    for i in range(int(round(START * FPS)), int(round(UNTIL * FPS))):
        pg.evaluate(f"window.render({i / FPS})"); ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
    b.close()
ff.stdin.close(); ff.wait()
print("ok", video)
