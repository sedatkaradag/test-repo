"""'Pray anyway' Reel: top-down prayer rug through five prayers and four moods, then Sahih al-Bukhari 1117.
python3 make.py <out_dir> [--frames=t1,t2,...]   (audio: sound.py writes <out_dir>/ambient.wav first)"""
import html, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from content import display_text, split_narrator  # typography only, never changes words

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
FRAMES = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--frames=")), None)
FPS = 30

# Our own wording (owner: same idea, our words). Times in seconds.
SCENES = [
    (0.0, "fajr", "FAJR", "Half asleep."),
    (1.9, "dhuhr", "DHUHR", "Buried in work."),
    (3.6, "asr", "ASR", "Running on empty."),
    (5.3, "maghrib", "MAGHRIB", "Just walked in."),
    (7.0, "isha", "ISHA", "Worn out."),
    (8.7, "low", "", "Feeling low."),
    (10.3, "broken", "", "Heart in pieces."),
    (11.9, "joy", "", "Full of joy."),
    (13.5, "grateful", "", "Simply grateful."),
    (15.1, "anyway", "", "Pray. <em>Anyway.</em>"),
    (18.4, "hadith", "", ""),
    (25.6, "logo", "", ""),
]
END = 28.4

# Hadith: text only from the verified database
h = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", "hadith:bukhari:1117"],
                              capture_output=True, text=True, check=True).stdout)
assert h["status"] == "sahih", h["status"]
who, body = split_narrator(display_text(h["english"]))
HL = "then pray Lying on your side"
assert HL in body, body
en_html = html.escape(body).replace(html.escape(HL), f'<span class="hl">{html.escape(HL)}</span>', 1)
ar = h["arabic"]
W = ar.split()
assert len(W) == 52, len(W)
AR = " ".join(W[40:51])  # the Prophet's words, cut from the source by word position, never typed
data = {
    "scenes": [{"t": t, "key": k, "label": lab, "text": txt} for t, k, lab, txt in SCENES],
    "hadith": {"who": who, "en_html": en_html, "ar": AR, "ref": h["reference"].upper(), "hl_at": 4.2},
}
logo = sorted((REPO / "samples/logo_draw/frames_800").iterdir())[-1].name
page = (HERE / "page.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__LOGO__", logo)
run = OUT / "page_run.html"; run.write_text(page, encoding="utf-8")
json.dump(data, open(OUT / "timeline.json", "w"), ensure_ascii=False, indent=1)

from playwright.sync_api import sync_playwright
if FRAMES:
    from PIL import Image
    ts = [float(x) for x in FRAMES.split(",")]
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(500)
        ims = []
        for t in ts:
            pg.evaluate(f"window.render({t})"); f = OUT / f"f_{t:05.2f}.jpg"; pg.screenshot(path=str(f), type="jpeg", quality=88)
            ims.append(Image.open(f).resize((360, 640)))
        b.close()
    cols = min(6, len(ims)); c = Image.new("RGB", (360 * cols, 640 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims): c.paste(im, ((i % cols) * 360, (i // cols) * 640))
    c.save(OUT / "sheet.jpg", quality=85); print("sheet", OUT / "sheet.jpg"); sys.exit(0)

audio = OUT / "ambient.wav"
assert audio.exists(), "run sound.py first"
video = OUT / "pray_anyway.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                       "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{END:.2f}", "-movflags", "+faststart", str(video)],
                      stdin=subprocess.PIPE)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(500)
    for i in range(int(round(END * FPS))):
        pg.evaluate(f"window.render({i / FPS})"); ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
    b.close()
ff.stdin.close(); ff.wait()
print("ok", video)
