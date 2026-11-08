"""Re-create the logo drawing as transparent PNG frames (30 fps) and ProRes 4444 .mov files with alpha,
from assets/logo.png and the drawing in samples/trivia/make_trivia.py.

    python3 samples/logo_draw/export_logo.py <repo> <out_dir>
"""
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
from PIL import Image

repo, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
tmp = Path(tempfile.mkdtemp())
(tmp / "align.json").write_text("{}")
(tmp / "rounds.json").write_text("[]")
sys.argv = [sys.argv[0], str(repo), str(tmp), str(tmp / "out"), str(tmp / "rounds.json")]
mt = types.ModuleType("mt")
src = (repo / "samples" / "trivia" / "make_trivia.py").read_text().split("# ---------- layers ----------")[0]
exec(compile(src, "make_trivia.py", "exec"), mt.__dict__)
for data, px in ((None, mt.LOGO_PX), (mt.FIN_LOGO, mt.FIN_PX)):
    d = out / f"frames_{px}"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    n = int(round((mt.LOGO_DONE + 0.25) * 30)) + 1
    for i in range(n):
        fr = []
        for bgv in (0., 255.):           # drawn over black and over white -> colour and alpha
            f = np.full((px, px, 3), bgv, np.float32)
            mt.draw_logo_at(f, i / 30, cx=px / 2, cy=px / 2, data=data, px=px)
            fr.append(f)
        a = np.clip(1 - (fr[1] - fr[0]).mean(2) / 255, 0, 1)
        rgb = np.where(a[..., None] > 1e-3, fr[0] / np.maximum(a[..., None], 1e-3), 0)
        Image.fromarray(np.dstack([rgb, a * 255]).clip(0, 255).astype(np.uint8), "RGBA").save(d / f"{i:03d}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(d / "%03d.png"), "-c:v", "prores_ks",
                    "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(out / f"logo_draw_{px}.mov")], check=True)
    print(px, n, "frames")
