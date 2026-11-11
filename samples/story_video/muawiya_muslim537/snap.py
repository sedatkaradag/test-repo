import sys
from playwright.sync_api import sync_playwright
from PIL import Image
d = "/tmp/claude-0/-home-claude/210372c4-8ad9-59ab-9204-54f74252b840/scratchpad/story2/"
times = [float(x) for x in sys.argv[2:]]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto(f"file://{d}page_run.html"); pg.evaluate("window.ready"); pg.wait_for_timeout(300)
    ims = []
    for t in times:
        pg.evaluate(f"window.render({t})"); pg.screenshot(path=d + "tmp.png"); ims.append(Image.open(d + "tmp.png").resize((360, 640)))
    b.close()
c = Image.new("RGB", (360 * min(5, len(ims)), 640 * ((len(ims) + 4) // 5)))
for i, im in enumerate(ims): c.paste(im, ((i % 5) * 360, (i // 5) * 640))
c.save(d + sys.argv[1])
