"""Hand-made posts (quizzes, story videos ...) that the owner approves in the control panel's
"Elle gönderiler" section. Nothing here posts by itself: `enqueue` only writes a queue item that the
regular publisher (publish.yml) sends at its next check, after the owner pressed "Paylaş".

    python3 scripts/manual_post.py add --id <id> --title "<title>" --format "<format>" \
        --video <mp4> [--cover <jpg>] --caption <txt> [--verses "20:25-28, 99:7-8"] [--reciter "..."]
    python3 scripts/manual_post.py enqueue <id> --caption <txt>     # the caption the owner approved
    python3 scripts/manual_post.py mark <id> <rejected|revision> [--note "..."]
    python3 scripts/manual_post.py status                            # repo state of every item, JSON

Files live in manual/<id>/ (video.mp4, cover.jpg, post.json). The queue item points at those files, so
nothing is copied. `add` also writes /tmp/manual_panel/<id>.json: the panel document without the
media urls (the agent uploads video.mp4 and cover.jpg as panel assets and adds video_url / image_url).
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "manual"
QUEUE = ROOT / "queue"
PANEL_OUT = Path("/tmp/manual_panel")
LEAD = dt.timedelta(minutes=2)          # publish_at = approval time + this
CAPTION_MAX, TAGS_MAX = 2200, 30        # Instagram limits


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def load(pid):
    p = MANUAL / pid / "post.json"
    if not p.exists():
        sys.exit(f"REJECT: no manual post {pid}")
    return p, json.loads(p.read_text(encoding="utf-8"))


def save(p, post):
    p.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_caption(text):
    text = text.strip()
    if not text:
        sys.exit("REJECT: empty caption")
    if len(text) > CAPTION_MAX:
        sys.exit(f"REJECT: caption is {len(text)} characters (Instagram takes {CAPTION_MAX})")
    if len(re.findall(r"#\w+", text)) > TAGS_MAX:
        sys.exit(f"REJECT: more than {TAGS_MAX} hashtags")
    return text


def seconds_of(video):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(video)], capture_output=True, text=True, check=True).stdout
        return round(float(out.strip()), 1)
    except Exception:  # noqa: BLE001
        return None


def cmd_add(a):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,60}", a.id):
        sys.exit("REJECT: id must be lowercase letters, digits and dashes (e.g. 2026-11-13-guess-surah)")
    d = MANUAL / a.id
    if (d / "post.json").exists() and not a.replace:
        sys.exit(f"REJECT: {a.id} exists (use --replace for a revised version)")
    d.mkdir(parents=True, exist_ok=True)
    old = json.loads((d / "post.json").read_text(encoding="utf-8")) if (d / "post.json").exists() else {}
    if old.get("status") in ("queued", "published"):
        sys.exit(f"REJECT: {a.id} is already {old['status']}")
    shutil.copyfile(a.video, d / "video.mp4")
    if a.cover:
        shutil.copyfile(a.cover, d / "cover.jpg")
    post = {
        "id": a.id, "title": a.title, "format": a.format,
        "caption": check_caption(Path(a.caption).read_text(encoding="utf-8")),
        "verses": a.verses or "", "reciter": a.reciter or "",
        "seconds": seconds_of(d / "video.mp4"),
        "video": f"manual/{a.id}/video.mp4",
        "cover": f"manual/{a.id}/cover.jpg" if a.cover else "",
        "status": "pending", "created_at": old.get("created_at") or iso(now()),
        "version": int(old.get("version", 0)) + 1,
        "notes": old.get("notes", []),
    }
    if old:
        post["updated_at"] = iso(now())
    save(d / "post.json", post)
    PANEL_OUT.mkdir(parents=True, exist_ok=True)
    panel = {k: post[k] for k in ("title", "format", "caption", "verses", "reciter", "seconds",
                                  "status", "created_at", "version")}
    if old:
        panel["updated_at"] = post["updated_at"]
        panel["note"] = ""          # the revision note is answered by this version
    (PANEL_OUT / f"{a.id}.json").write_text(json.dumps(panel, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": True, "id": a.id, "version": post["version"], "panel_doc": str(PANEL_OUT / f"{a.id}.json")}))


def cmd_enqueue(a):
    p, post = load(a.id)
    if post.get("status") in ("queued", "published"):
        sys.exit(f"REJECT: {a.id} is already {post['status']} ({post.get('slot', '')})")
    if post.get("status") == "rejected":
        sys.exit(f"REJECT: {a.id} was rejected")
    caption = check_caption(Path(a.caption).read_text(encoding="utf-8"))
    if not (ROOT / post["video"]).exists():
        sys.exit(f"REJECT: {post['video']} missing")
    t = now() + LEAD
    slot = f"{t.date().isoformat()}_handmade-{t.strftime('%H%M')}"
    if (QUEUE / f"{slot}.json").exists():
        sys.exit(f"REJECT: slot {slot} already filled, try again in a minute")
    item = {
        "entry_id": f"manual:{a.id}",
        "type": "reel",
        "content_type": "manual",
        "manual": True,
        "manual_id": a.id,
        "reference": post["title"],
        "slot": slot,
        "publish_at": iso(t),
        "local_slot": f"{t.strftime('%Y-%m-%d %H:%M')} UTC (owner approved)",
        "image": post["cover"] or post["video"],
        "cover": post["cover"],
        "video": post["video"],
        "trial": False,          # hand-made posts go to followers like the owner's own posts did
        "story": False,          # no automatic Story for hand-made posts
        "caption": caption,
        "theme": post.get("format", ""),
        "verses": post.get("verses", ""),
        "recitation": post.get("reciter", ""),
        "review": "Hand-made post: approved by the owner in the control panel",
        "flags": [],
        "status": "ready",
        "created_at": iso(now()),
    }
    if not post["cover"]:
        sys.exit("REJECT: no cover image (add --cover); the publisher needs one")
    (QUEUE / f"{slot}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    post.update(status="queued", slot=slot, approved_caption=caption, approved_at=iso(now()))
    save(p, post)
    print(json.dumps({"ok": True, "id": a.id, "slot": slot, "publish_at": item["publish_at"]}))


def cmd_mark(a):
    p, post = load(a.id)
    if post.get("status") in ("queued", "published"):
        sys.exit(f"REJECT: {a.id} is already {post['status']}")
    post["status"] = a.status
    if a.note:
        post.setdefault("notes", []).append({"ts": iso(now()), "status": a.status, "note": a.note})
    save(p, post)
    print(json.dumps({"ok": True, "id": a.id, "status": a.status}))


def cmd_status(a):
    out = []
    for p in sorted(MANUAL.glob("*/post.json")):
        post = json.loads(p.read_text(encoding="utf-8"))
        row = {k: post.get(k) for k in ("id", "title", "status", "slot", "version")}
        q = QUEUE / f"{post.get('slot')}.json" if post.get("slot") else None
        if q and q.exists():
            item = json.loads(q.read_text(encoding="utf-8"))
            row.update(queue_status=item.get("status"), media_id=item.get("media_id"),
                       posted_at=item.get("posted_at"), error=item.get("error"))
        out.append(row)
    print(json.dumps(out, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    s.add_argument("--id", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--format", required=True)
    s.add_argument("--video", required=True)
    s.add_argument("--cover")
    s.add_argument("--caption", required=True)
    s.add_argument("--verses")
    s.add_argument("--reciter")
    s.add_argument("--replace", action="store_true")
    s.set_defaults(f=cmd_add)
    s = sub.add_parser("enqueue")
    s.add_argument("id")
    s.add_argument("--caption", required=True)
    s.set_defaults(f=cmd_enqueue)
    s = sub.add_parser("mark")
    s.add_argument("id")
    s.add_argument("status", choices=["rejected", "revision"])
    s.add_argument("--note")
    s.set_defaults(f=cmd_mark)
    s = sub.add_parser("status")
    s.set_defaults(f=cmd_status)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
