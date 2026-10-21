"""Adds the recitation to verse Reels. Runs in GitHub Actions (the Claude workspace cannot reach
everyayah.com).

    python scripts/reel_audio.py          # every queue item with status "audio_pending"
    python scripts/reel_audio.py check    # only checks that each configured reciter's files exist

For each pending Reel: downloads the recitation of exactly the verses on the card (one file per
verse, everyayah.com/data/<reciter>/<SSSAAA>.mp3), joins them, stretches the silent video so the
text is revealed while the verses are recited, holds the finished card for a moment at the end,
and writes the result over queue/<slot>.mp4. Only then is the item marked "ready", so the
publisher never posts a Reel without its recitation. On failure the item goes on "hold" with the
reason in `error` (the panel sync run reports it).
"""
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
BASE = "https://everyayah.com/data"
TAIL = 1.5   # seconds the finished card stays after the recitation ends


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(path):
    out = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        raise RuntimeError(f"cannot read duration of {path.name}")
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def download(reciter, ayah, dest):
    r = requests.get(f"{BASE}/{reciter}/{ayah}.mp3", timeout=60)
    c = r.content
    is_mp3 = c[:3] == b"ID3" or (len(c) > 1 and c[0] == 0xFF and (c[1] & 0xE0) == 0xE0)
    if r.status_code != 200 or len(c) < 2000 or not is_mp3:
        raise RuntimeError(f"recitation file {reciter}/{ayah}.mp3 not available (HTTP {r.status_code})")
    dest.write_bytes(r.content)


def mix(video, ayah_files, out, max_seconds):
    tmp = Path(tempfile.mkdtemp())
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in ayah_files))
    audio = tmp / "recitation.m4a"
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "aac", "-b:a", "160k", str(audio)], check=True)
    a = duration(audio)
    if a > max_seconds:
        raise RuntimeError(f"recitation is {a:.0f}s, longer than the {max_seconds}s limit")
    v = duration(video)
    total = a + TAIL
    k = max(1.0, a / max(v - 1.0, 1.0))   # reveal across the recitation, never faster than the silent cut
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
                    "-filter_complex", f"[0:v]setpts=PTS*{k:.4f},tpad=stop_mode=clone:stop_duration={TAIL + 5}[v];[1:a]apad[a]",
                    "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-r", "30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    return a, duration(out)


def git_commit(msg):
    subprocess.run(["git", "add", "queue"], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
    for _ in range(3):
        if subprocess.run(["git", "push"], cwd=ROOT).returncode == 0:
            return
        subprocess.run(["git", "pull", "--rebase"], cwd=ROOT)
    raise RuntimeError("git push failed")


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    rec = (cfg.get("reels") or {}).get("recitation") or {}
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        for r in rec.get("reciters", []):
            ok = requests.head(f"{BASE}/{r['id']}/001001.mp3", timeout=30, allow_redirects=True).status_code == 200
            print(("OK  " if ok else "MISSING ") + r["id"])
        return
    done = []
    for p in sorted(QUEUE.glob("*.json")):
        item = json.loads(p.read_text(encoding="utf-8"))
        if item.get("status") != "audio_pending":
            continue
        au = item["audio"]
        try:
            tmp = Path(tempfile.mkdtemp())
            files = []
            for ayah in au["ayahs"]:
                f = tmp / f"{ayah}.mp3"
                download(au["reciter"], ayah, f)
                files.append(f)
            video = ROOT / item["video"]
            out = tmp / "out.mp4"
            a, total = mix(video, files, out, int(rec.get("max_seconds", 75)))
            video.write_bytes(out.read_bytes())
            au.update(done=True, seconds=round(a, 1), video_seconds=round(total, 1),
                      added_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
            item["status"] = "ready"
            soon = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)
            if dt.datetime.fromisoformat(item["publish_at"].replace("Z", "+00:00")) < soon:
                item["publish_at"] = soon.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            print(f"ready {item['slot']}: {a:.1f}s recitation by {au['reciter']}, video {total:.1f}s")
        except Exception as e:  # noqa: BLE001 — keep it off the publisher and say why
            item["status"] = "hold"
            item["error"] = f"recitation could not be added: {str(e)[:300]}"
            print(f"hold {item['slot']}: {e}")
        p.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        done.append(f"{item['status']} {item['slot']}")
    if done:
        git_commit("reel audio: " + ", ".join(done))
    else:
        print("no Reels waiting for audio")


if __name__ == "__main__":
    main()
