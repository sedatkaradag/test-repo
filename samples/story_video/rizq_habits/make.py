"""'Innocent habits blocking your rizq' (remake of @reminders.in.frames, owner's pick 18 Nov).
python3 make.py <out_dir> [--stills=t1,t2,...]

Owner's choices: the habit lines and "say instead" lines stay as in the reference; under each one goes an
exact sentence of the verse it cited (from scripts/find.py, checked as a substring), because the reference's
"Qur'an x:y" lines were paraphrases, not verses. Closing: Hud 11:6 instead of "Rizq isn't blocked because
Allah withholds" (contradicts 13:26). Sound: ambient, no music.
"""
import io, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
STILLS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--stills=")), None)
FPS = 30


def verse(entry, part):
    d = json.loads(subprocess.run(["python3", str(REPO / "scripts/find.py"), "get", entry], capture_output=True, text=True, check=True).stdout)
    assert part in d["english"], (entry, part)
    name, num = d["reference"].replace("Surah ", "").rsplit(" ", 1)
    return part, f"{name.upper()} {num}"


HABITS = [
    ("“I’m broke.”", "This closes doors.", "SAY INSTEAD", "Allah is our Provider.", "quran:65:3", "He will provide for him from where he does not expect."),
    ("Constant money worry", "Worry is not tawakkul.", "SAY INSTEAD", "Ya Razzaq, You never fail us.", "quran:65:3", "Whoever puts his trust in Allah, He is sufficient for him."),
    ("Comparing your life", "It whispers “Allah forgot me.”", "REMEMBER", "What is written for us will reach us.", "quran:4:32", "Do not wish for what Allah has bestowed upon some of you over others."),
    ("Ungrateful speech", "Complaining blocks. Shukr multiplies.", "PRACTICE", "Alhamdulillah for what we have, and what’s on the way.", "quran:14:7", "If you are grateful, I will surely give you more"),
    ("“Nothing works for me.”", "A dua of hopelessness.", "SAY INSTEAD", "Allah’s plan is better than what we’re praying for.", "quran:2:216", "Allah knows and you do not know"),
]
TITLE, HAB, TURN = 3.8, 8.6, 3.5
habits, scenes = [], {"title": [0, TITLE]}
for i, (head, sub, label, say, entry, part) in enumerate(HABITS):
    v, ref = verse(entry, part)
    habits.append({"head": head, "sub": sub, "label": label, "say": say, "verse": v, "ref": ref, "turn": TURN})
    scenes[f"h{i}"] = [TITLE + i * HAB, TITLE + (i + 1) * HAB]
t_end = TITLE + len(HABITS) * HAB
close_v, close_ref = verse("quran:11:6", "There is no moving creature on earth but upon Allah is its provision.")
scenes["end"] = [t_end, t_end + 7.0]
scenes["logo"] = [t_end + 7.0, t_end + 10.2]
END = round(t_end + 10.2, 2)

logo = sorted((REPO / "samples/logo_draw/frames_800").iterdir())
mark = sorted((REPO / "samples/logo_draw/frames_478").iterdir())[-1]
data = {"scenes": scenes, "habits": habits, "close": {"verse": close_v, "ref": close_ref, "lines": 3}, "end": END, "logo": [str(p) for p in logo]}
page = (HERE / "page.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__REPO__", str(REPO)).replace("__MARK__", str(mark))
run = OUT / "page_run.html"; run.write_text(page, encoding="utf-8")
json.dump({"end": END, "scenes": scenes, "habits": habits, "turn": TURN}, open(OUT / "timeline.json", "w"), indent=1, ensure_ascii=False)
print("end", END)

from playwright.sync_api import sync_playwright


def shots(ts):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{run}"); pg.evaluate("window.ready"); pg.wait_for_timeout(400)
        for t in ts:
            pg.evaluate(f"window.render({t})"); yield t, pg.screenshot(type="jpeg", quality=90)
        b.close()


if STILLS:
    from PIL import Image
    ims = []
    for t, buf in shots([float(x) for x in STILLS.split(",")]):
        im = Image.open(io.BytesIO(buf)); im.save(OUT / f"s_{t:06.2f}.jpg", quality=88); ims.append(im.resize((360, 640)))
    cols = min(6, len(ims)); c = Image.new("RGB", (360 * cols, 640 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims): c.paste(im, ((i % cols) * 360, (i // cols) * 640))
    c.save(OUT / "sheet.jpg", quality=85); print("sheet", OUT / "sheet.jpg"); sys.exit(0)

subprocess.run(["python3", str(HERE / "sound.py"), str(OUT), str(OUT / "timeline.json")], check=True)
video = OUT / "rizq_habits.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                       "-i", str(OUT / "ambient.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{END:.2f}", "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)
for k, (t, buf) in enumerate(shots([i / FPS for i in range(int(round(END * FPS)))])):
    ff.stdin.write(buf)
ff.stdin.close(); assert ff.wait() == 0
print(json.dumps({"ok": True, "video": str(video), "seconds": END}))
