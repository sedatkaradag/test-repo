"""Adds the Qur'an recitation to verse videos. Runs in GitHub Actions (the Claude workspace cannot
reach everyayah.com).

    python scripts/reel_audio.py          # every video waiting for its recitation
    python scripts/reel_audio.py check    # only checks that each configured reciter's files exist

Two kinds of work:
  * Reels and stand-alone Stories with status "audio_pending": the item is published only after
    this step, so a verse video never goes out half-made.
  * Verse feed posts with `story_audio` not yet done: their Story becomes the recitation video;
    if that fails, the publisher simply posts the image Story as before.

Reciters: the assigned reciter is tried first, then the others in the configured order. The first
one with every verse available is used and named in the caption. If none has them (or the
recitation is too long), Reels and stand-alone Stories go out silent, and feed posts keep the
image Story.
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
TAIL = 1.5           # seconds the finished card stays after the recitation ends
STORY_MAX = 59       # Instagram Stories take videos up to 60 seconds


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
        raise RuntimeError(f"{reciter}/{ayah}.mp3 not available (HTTP {r.status_code})")
    dest.write_bytes(c)


def find_recitation(reciters, first_id, ayahs):
    """Try the assigned reciter, then the others in order. Returns (reciter, files, tried)."""
    ids = [r["id"] for r in reciters]
    start = ids.index(first_id) if first_id in ids else 0
    tried = []
    for k in range(len(reciters)):
        rec = reciters[(start + k) % len(reciters)]
        tmp = Path(tempfile.mkdtemp())
        try:
            files = []
            for a in ayahs:
                f = tmp / f"{a}.mp3"
                download(rec["id"], a, f)
                files.append(f)
            return rec, files, tried
        except Exception as e:  # noqa: BLE001 — try the next reciter
            tried.append(f"{rec['id']}: {str(e)[:120]}")
    return None, None, tried


def mix(video, ayah_files, out, max_seconds):
    tmp = Path(tempfile.mkdtemp())
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in ayah_files))
    audio = tmp / "recitation.m4a"
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "aac", "-b:a", "160k", str(audio)], check=True)
    a = duration(audio)
    if a + TAIL > max_seconds:
        raise RuntimeError(f"recitation is {a:.0f}s, too long for {max_seconds}s")
    v = duration(video)
    total = a + TAIL
    k = max(1.0, a / max(v - 1.0, 1.0))   # reveal across the recitation, never faster than the silent cut
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
                    "-filter_complex", f"[0:v]setpts=PTS*{k:.4f},tpad=stop_mode=clone:stop_duration={TAIL + 5}[v];"
                    "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100,apad[a]",
                    "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-r", "30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    return a, duration(out)


def add_recitation(video_rel, au, reciters, max_seconds):
    """Mixes the recitation into ROOT/video_rel in place. Returns (ok, note) and updates `au`."""
    rec, files, tried = find_recitation(reciters, au["reciter"], au["ayahs"])
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if not rec:
        au.update(done=False, failed=True, tried=tried, checked_at=stamp)
        return False, "no reciter had these verses"
    video = ROOT / video_rel
    out = Path(tempfile.mkdtemp()) / "out.mp4"
    try:
        a, total = mix(video, files, out, max_seconds)
    except Exception as e:  # noqa: BLE001
        au.update(done=False, failed=True, tried=tried + [str(e)[:160]], checked_at=stamp)
        return False, str(e)[:160]
    video.write_bytes(out.read_bytes())
    if rec["id"] != au["reciter"]:
        au["assigned"] = au["reciter"]
    au.update(reciter=rec["id"], reciter_name=rec["name"], done=True, failed=False, tried=tried,
              seconds=round(a, 1), video_seconds=round(total, 1), added_at=stamp)
    return True, f"{a:.1f}s by {rec['id']}"


def decode_wav(src, dest):
    """Decode one verse file to 44.1 kHz stereo PCM; returns its exact length in seconds."""
    import wave
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-ar", "44100", "-ac", "2",
                    "-c:a", "pcm_s16le", str(dest)], check=True)
    with wave.open(str(dest)) as w:
        return w.getnframes() / w.getframerate()


def add_recitation_v2(video_rel, layout, layout_hash, au, reciters, max_seconds):
    """Template v2 verse video (Reel or a verse post's Story): drawn here from the approved layout,
    each verse lit for exactly as long as its own recitation file lasts. If the layout drawn here is
    not pixel-identical to the one checked before queueing (layout_hash), the preview video is
    stretched to the recitation instead (the earlier way)."""
    import wave
    rec, files, tried = find_recitation(reciters, au["reciter"], au["ayahs"])
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if not rec:
        au.update(done=False, failed=True, tried=tried, checked_at=stamp)
        return False, "no reciter had these verses"
    tmp = Path(tempfile.mkdtemp())
    try:
        durs, wavs = [], []
        for k, f in enumerate(files):
            w = tmp / f"{k}.wav"
            durs.append(decode_wav(f, w))
            wavs.append(w)
        total = sum(durs)
        sys.path.insert(0, str(ROOT / "scripts"))
        import reels as RL
        if total + RL.tail_seconds(layout) > max_seconds:   # the finished frame stays a moment after it
            raise RuntimeError(f"recitation is {total:.0f}s, too long for {max_seconds}s")
        joined = tmp / "all.wav"
        with wave.open(str(joined), "wb") as out:
            for k, w in enumerate(wavs):
                with wave.open(str(w)) as src:
                    if k == 0:
                        out.setparams(src.getparams())
                    out.writeframes(src.readframes(src.getnframes()))
        audio = tmp / "recitation.m4a"
        subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(joined),
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100",
                        "-c:a", "aac", "-b:a", "160k", str(audio)], check=True)
        sys.path.insert(0, str(ROOT / "scripts"))
        import reels as RL
        video = ROOT / video_rel
        out = tmp / "out.mp4"
        if RL.layout_hash(layout) == layout_hash:
            bounds = [0.0]
            for d in durs:
                bounds.append(round(bounds[-1] + d, 3))
            RL.render_video(layout, out, bounds=bounds, audio=audio)
            timing = "verse by verse"
        else:   # never publish text drawn differently from what was approved
            a_s, _ = mix(video, files, out, max_seconds)
            timing = "stretched preview (layout differed on GitHub)"
        video.write_bytes(out.read_bytes())
    except Exception as e:  # noqa: BLE001
        au.update(done=False, failed=True, tried=tried + [str(e)[:160]], checked_at=stamp)
        return False, str(e)[:160]
    if rec["id"] != au["reciter"]:
        au["assigned"] = au["reciter"]
    au.update(reciter=rec["id"], reciter_name=rec["name"], done=True, failed=False, tried=tried,
              seconds=round(total, 1), video_seconds=round(duration(ROOT / video_rel), 1),
              verse_seconds=[round(d, 2) for d in durs], timing=timing, added_at=stamp)
    return True, f"{total:.1f}s by {rec['id']}, {timing}"


def set_recitation_line(caption, name):
    caption = re.sub(r"\n*^Recitation: .*$", "", caption, flags=re.M).rstrip()
    return f"{caption}\n\nRecitation: {name}" if name else caption


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
    reciters = rec.get("reciters") or []
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        for r in reciters:
            ok = requests.head(f"{BASE}/{r['id']}/001001.mp3", timeout=30, allow_redirects=True).status_code == 200
            print(f"::notice::{'OK' if ok else 'MISSING'} {r['id']}")
        return
    now = dt.datetime.now(dt.timezone.utc)
    done = []
    for p in sorted(QUEUE.glob("*.json")):
        item = json.loads(p.read_text(encoding="utf-8"))
        changed = False
        if item.get("status") == "audio_pending" and item.get("audio"):
            is_story = item.get("type") == "story"
            if item.get("template") == "v2" and item.get("reel_layout"):
                ok, note = add_recitation_v2(item["video"], item["reel_layout"], item.get("layout_hash"),
                                             item["audio"], reciters, int(rec.get("max_seconds", 75)))
            else:
                ok, note = add_recitation(item["video"], item["audio"], reciters,
                                          STORY_MAX if is_story else int(rec.get("max_seconds", 75)))
            if not is_story and "caption" in item:
                item["caption"] = set_recitation_line(item["caption"], item["audio"]["reciter_name"] if ok else "")
            if not ok:
                item["audio"]["silent"] = True
            item["status"] = "ready"
            soon = now + dt.timedelta(minutes=5)
            if dt.datetime.fromisoformat(item["publish_at"].replace("Z", "+00:00")) < soon:
                item["publish_at"] = soon.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            done.append(f"{item['slot']} {'with recitation' if ok else 'silent'} ({note})")
            changed = True
        sa = item.get("story_audio")
        if (sa and not sa.get("done") and not sa.get("failed") and item.get("status") == "ready"
                and item.get("story_video")):
            if item.get("story_layout"):
                ok, note = add_recitation_v2(item["story_video"], item["story_layout"],
                                             item.get("story_layout_hash"), sa, reciters, STORY_MAX)
            else:
                ok, note = add_recitation(item["story_video"], sa, reciters, STORY_MAX)
            done.append(f"{item['slot']} story {'with recitation' if ok else 'stays an image'} ({note})")
            changed = True
        if changed:
            p.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            print(done[-1])
    if done:
        git_commit("recitation: " + "; ".join(done))
    else:
        print("nothing waiting for a recitation")


if __name__ == "__main__":
    main()
