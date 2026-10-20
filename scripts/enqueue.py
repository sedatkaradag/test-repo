"""Render an entry and put it in the publishing queue (with all safety checks).

    python scripts/enqueue.py slots --days 2      # empty slots, e.g. 2026-10-21_us-evening
    python scripts/enqueue.py add --entry quran:94:5-6 --slot 2026-10-21_us-evening \
        --caption-file /path/caption.txt --theme "hope in hardship" \
        --review "approved by verifier: ..."
    python scripts/enqueue.py list

Each slot gets a random offset of +-jitter_minutes (config) so posts never go
out at exactly the same minute.

Text on the image always comes from the database. The caption is checked so it
cannot quietly carry a different version of the text.
"""
import argparse
import datetime as dt
import json
import random
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from content import ROOT, get, used_ids
from render import TooLong, make_story, render, render_cover, render_reel

QUEUE = ROOT / "queue"


def config():
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def slot_utc(date_str, slot, tz):
    local = dt.datetime.fromisoformat(f"{date_str}T{slot}:00").replace(tzinfo=ZoneInfo(tz))
    return local.astimezone(dt.timezone.utc)


def slot_by_key(cfg, key):
    """'2026-10-21_us-evening' -> (slot dict, local date)."""
    date_str, _, name = key.partition("_")
    for s in all_slots(cfg):
        if s["name"] == name:
            return s, date_str
    raise SystemExit(f"REJECT: unknown slot '{name}' (see config.yaml)")


def all_slots(cfg):
    slots = list(cfg["slots"])
    reels = cfg.get("reels") or {}
    if reels.get("enabled") and reels.get("slot"):
        slots.append({**reels["slot"], "type": "reel"})
    car = cfg.get("carousel") or {}
    if car.get("enabled") and car.get("slot"):
        slots.append({**car["slot"], "type": "carousel"})
    return slots


def upcoming_slots(cfg, days):
    """All slot keys from now until `days` ahead, with their base UTC time."""
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for s in all_slots(cfg):
        today = dt.datetime.now(ZoneInfo(s["tz"])).date()
        for d in range(days + 1):
            date = today + dt.timedelta(days=d)
            if "weekday" in s and date.weekday() != int(s["weekday"]):
                continue
            day = date.isoformat()
            when = slot_utc(day, s["time"], s["tz"])
            if when > now + dt.timedelta(minutes=20):
                out.append((when, f"{day}_{s['name']}", s))
    return sorted(out)


def queued():
    items = []
    for p in sorted(QUEUE.glob("*.json")):
        items.append(json.loads(p.read_text(encoding="utf-8")))
    return items


def hashtags(caption):
    return {t.lower() for t in re.findall(r"#\w+", caption)}


def closing_line(caption):
    """The last paragraph before the hashtags (the call to action)."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", caption) if p.strip()]
    paras = [p for p in paras if not p.startswith("#")]
    return paras[-1].lower() if paras else ""


def recent_captions(n=8, exclude_slot=None):
    items = [i for i in queued() if i.get("slot") != exclude_slot]
    items.sort(key=lambda i: i["publish_at"])
    return [i["caption"] for i in items[-n:]]


def check_caption(caption, entry, exclude_slot=None):
    problems = []
    if len(caption) > 2200:
        problems.append("caption longer than 2200 characters")
    tags = hashtags(caption)
    if not 3 <= len(tags) <= 5:
        problems.append(f"{len(tags)} hashtags (use 3-5; more can reduce reach)")
    if entry["reference"].split(" ")[-1] not in caption:
        problems.append(f"caption must cite the reference ({entry['reference']})")
    if re.search(r"https?://|www\.|\b[\w-]+\.(com|org|net|io|co)\b", caption, re.I):
        problems.append("no links or domain names in captions")
    if re.search(r"translation\s*:|translated by|quranenc|rowwad", caption, re.I):
        problems.append("do not name the translation source in the caption")
    # Any quotation in the caption must be copied from the database text.
    src = re.sub(r"\W+", " ", entry["english"]).lower()
    for q in re.findall(r"[“\"]([^”\"]{8,})[”\"]", caption):
        if re.sub(r"\W+", " ", q).lower().strip() not in src:
            problems.append("caption quotes text that is not in the verified source")
    # Variety: no repeated closing line, no near-identical hashtag sets.
    recent = recent_captions(exclude_slot=exclude_slot)
    if closing_line(caption) and closing_line(caption) in {closing_line(c) for c in recent}:
        problems.append("closing line repeats one of the last 8 captions — phrase it differently")
    for c in recent[-4:]:
        other = hashtags(c)
        if tags and other and len(tags & other) / len(tags | other) > 0.5:
            problems.append("hashtags too similar to a recent post — rotate them")
            break
    return problems


def cmd_add(a):
    cfg = config()
    entry = get(a.entry)
    base_ids = {a.entry}
    m = re.fullmatch(r"quran:(\d+):(\d+)-(\d+)", a.entry)
    if m:
        s, x, y = map(int, m.groups())
        base_ids = {f"quran:{s}:{v}" for v in range(x, y + 1)} | {a.entry}
    recent = used_ids(cfg["repeat_days"]) | {i["entry_id"] for i in queued()}
    if base_ids & recent:
        sys.exit(f"REJECT: {a.entry} was posted or queued recently")
    if entry["type"] == "hadith" and entry["status"] not in ("sahih", "hasan"):
        sys.exit("REJECT: hadith grade not sahih/hasan")

    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    problems = check_caption(caption, entry, exclude_slot=a.slot)
    if problems:
        sys.exit("REJECT caption: " + "; ".join(problems))

    if a.slot == "now":
        # One-off post a few minutes from now (owner asked for it explicitly).
        when = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=4)).replace(microsecond=0)
        date_str = when.strftime("%Y-%m-%d")
        slot = {"time": when.strftime("%H:%M"), "tz": "UTC"}
        a.slot = f"{date_str}_manual-{when.strftime('%H%M')}"
    else:
        slot, date_str = slot_by_key(cfg, a.slot)
        if slot.get("type") and slot["type"] != entry["type"]:
            sys.exit(f"REJECT: slot {a.slot} takes {slot['type']}, not {entry['type']}")
        base = slot_utc(date_str, slot["time"], slot["tz"])
        if base <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=20):
            sys.exit("REJECT: slot is in the past or too close")
        jitter = int(cfg.get("jitter_minutes", 0)) * 60
        when = base + dt.timedelta(seconds=random.randint(-jitter, jitter))
    stem = a.slot
    if (QUEUE / f"{stem}.json").exists():
        sys.exit(f"REJECT: slot {stem} already filled")

    img = QUEUE / f"{stem}.jpg"
    try:
        render(a.entry, img)
    except TooLong:
        sys.exit("REJECT: too long for one image, choose a shorter entry")

    story = QUEUE / f"{stem}_story.jpg"
    make_story(img, story)

    item = {
        "entry_id": a.entry,
        "type": entry["type"],
        "reference": entry["reference"],
        "slot": a.slot,
        "publish_at": when.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "local_slot": f"{date_str} {slot['time']} {slot['tz']} (±{cfg.get('jitter_minutes', 0)} min)",
        "image": f"queue/{stem}.jpg",
        "story_image": f"queue/{stem}_story.jpg",
        "caption": caption,
        "alt_text": f"{entry['english'][:900]} — {entry['reference']}",
        "theme": a.theme,
        "review": a.review,
        "status": "ready",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (QUEUE / f"{stem}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QUEUED {stem} {a.entry} -> {img}")


def cmd_add_reel(a):
    """Silent Reel from an already approved post of the same day (no new text)."""
    cfg = config()
    src = json.loads((QUEUE / f"{a.source}.json").read_text(encoding="utf-8"))
    entry = get(src["entry_id"])
    slot, date_str = slot_by_key(cfg, a.slot)
    if slot.get("type") != "reel":
        sys.exit(f"REJECT: {a.slot} is not the reel slot")
    base = slot_utc(date_str, slot["time"], slot["tz"])
    if base <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=30):
        sys.exit("REJECT: slot is in the past or too close")
    if (QUEUE / f"{a.slot}.json").exists():
        sys.exit(f"REJECT: slot {a.slot} already filled")
    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    problems = check_caption(caption, entry, exclude_slot=a.slot)
    if problems:
        sys.exit("REJECT caption: " + "; ".join(problems))
    jitter = int(cfg.get("jitter_minutes", 0)) * 60
    when = base + dt.timedelta(seconds=random.randint(-jitter, jitter))
    video = QUEUE / f"{a.slot}.mp4"
    render_reel(src["entry_id"], video)
    item = {
        "entry_id": src["entry_id"],
        "type": "reel",
        "source_slot": a.source,
        "reference": entry["reference"],
        "slot": a.slot,
        "publish_at": when.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "local_slot": f"{date_str} {slot['time']} {slot['tz']} (±{cfg.get('jitter_minutes', 0)} min)",
        "image": src["image"],
        "video": f"queue/{a.slot}.mp4",
        "trial": bool((cfg.get("reels") or {}).get("trial", True)),
        "caption": caption,
        "alt_text": src.get("alt_text", ""),
        "theme": src.get("theme", ""),
        "review": a.review,
        "status": "ready",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (QUEUE / f"{a.slot}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QUEUED REEL {a.slot} from {a.source} -> {video}")


def cmd_add_carousel(a):
    """Weekly carousel: a cover card plus 3-7 verified entries on one theme."""
    cfg = config()
    ids = [x.strip() for x in a.entries.split(",") if x.strip()]
    if not 3 <= len(ids) <= 7:
        sys.exit("REJECT: a carousel takes 3-7 entries")
    slot, date_str = slot_by_key(cfg, a.slot)
    if slot.get("type") != "carousel":
        sys.exit(f"REJECT: {a.slot} is not the carousel slot")
    base = slot_utc(date_str, slot["time"], slot["tz"])
    if base <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=30):
        sys.exit("REJECT: slot is in the past or too close")
    if (QUEUE / f"{a.slot}.json").exists():
        sys.exit(f"REJECT: slot {a.slot} already filled")
    recent = used_ids(cfg["repeat_days"]) | {i["entry_id"] for i in queued() if i.get("type") != "reel"}
    entries = []
    for i in ids:
        e = get(i)
        if e["type"] == "hadith" and e["status"] not in ("sahih", "hasan"):
            sys.exit(f"REJECT: {i} grade not sahih/hasan")
        if i in recent:
            sys.exit(f"REJECT: {i} was posted or queued recently")
        entries.append(e)
    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    problems = []
    if len(caption) > 2200:
        problems.append("caption longer than 2200 characters")
    for e in entries:
        if e["reference"].split(" ")[-1] not in caption:
            problems.append(f"caption must cite {e['reference']}")
    tags = hashtags(caption)
    if not 3 <= len(tags) <= 5:
        problems.append(f"{len(tags)} hashtags (use 3-5)")
    if re.search(r"https?://|www\.|\b[\w-]+\.(com|org|net|io|co)\b", caption, re.I):
        problems.append("no links or domain names in captions")
    if re.search(r"translation\s*:|translated by|quranenc|rowwad", caption, re.I):
        problems.append("do not name the translation source in the caption")
    recent_caps = recent_captions(exclude_slot=a.slot)
    if closing_line(caption) in {closing_line(c) for c in recent_caps}:
        problems.append("closing line repeats a recent caption")
    if problems:
        sys.exit("REJECT caption: " + "; ".join(problems))
    stem = a.slot
    images = [f"queue/{stem}_0.jpg"]
    render_cover(a.title, a.subtitle, QUEUE / f"{stem}_0.jpg", count=len(entries))
    for n, i in enumerate(ids, start=1):
        try:
            render(i, QUEUE / f"{stem}_{n}.jpg")
        except TooLong:
            for f in QUEUE.glob(f"{stem}_*.jpg"):
                f.unlink()
            sys.exit(f"REJECT: {i} too long for one card")
        images.append(f"queue/{stem}_{n}.jpg")
    jitter = int(cfg.get("jitter_minutes", 0)) * 60
    when = base + dt.timedelta(seconds=random.randint(-jitter, jitter))
    item = {
        "entry_id": ",".join(ids),
        "entry_ids": ids,
        "type": "carousel",
        "reference": a.title,
        "slot": a.slot,
        "publish_at": when.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "local_slot": f"{date_str} {slot['time']} {slot['tz']} (±{cfg.get('jitter_minutes', 0)} min)",
        "image": images[0],
        "images": images,
        "caption": caption,
        "alt_text": a.title,
        "theme": a.theme,
        "review": a.review,
        "status": "ready",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (QUEUE / f"{stem}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QUEUED CAROUSEL {stem}: {len(images)} cards")


def cmd_recaption(a):
    """Replace the caption of a queued (not yet published) item, with all checks."""
    path = QUEUE / f"{a.slot}.json"
    item = json.loads(path.read_text(encoding="utf-8"))
    if item["status"] != "ready":
        sys.exit(f"REJECT: {a.slot} is {item['status']}")
    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    problems = check_caption(caption, get(item["entry_id"]), exclude_slot=a.slot)
    if problems:
        sys.exit("REJECT caption: " + "; ".join(problems))
    item["caption"] = caption
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RECAPTIONED {a.slot}")


def cmd_list(_):
    for i in queued():
        print(f"{i['publish_at']}  {i.get('slot', ''):<28} {i['status']:<13} {i['entry_id']:<24} {i.get('theme', '')}")


def cmd_slots(a):
    cfg = config()
    filled = {i.get("slot") for i in queued()}
    for when, key, s in upcoming_slots(cfg, a.days):
        if key not in filled:
            print(f"EMPTY {key:<28} {s.get('type', 'any'):<7} base {when.isoformat().replace('+00:00', 'Z')}  ({s['time']} {s['tz']})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    ad = sub.add_parser("add")
    ad.add_argument("--entry", required=True)
    ad.add_argument("--slot", required=True, help="slot key printed by `slots` (e.g. 2026-10-21_us-evening), or 'now' for a one-off post in ~4 minutes")
    ad.add_argument("--caption-file", required=True)
    ad.add_argument("--theme", default="")
    ad.add_argument("--review", default="")
    ar = sub.add_parser("add-reel")
    ar.add_argument("--source", required=True, help="slot key of an approved post (same day)")
    ar.add_argument("--slot", required=True, help="reel slot key, e.g. 2026-10-21_reel")
    ar.add_argument("--caption-file", required=True)
    ar.add_argument("--review", default="")
    ac = sub.add_parser("add-carousel")
    ac.add_argument("--entries", required=True, help="comma-separated ids, 3-7")
    ac.add_argument("--slot", required=True, help="carousel slot key, e.g. 2026-10-21_carousel")
    ac.add_argument("--title", required=True, help="cover title, e.g. '5 Hadith on Patience'")
    ac.add_argument("--subtitle", default="")
    ac.add_argument("--caption-file", required=True)
    ac.add_argument("--theme", default="")
    ac.add_argument("--review", default="")
    rc = sub.add_parser("recaption")
    rc.add_argument("--slot", required=True)
    rc.add_argument("--caption-file", required=True)
    sub.add_parser("list")
    sl = sub.add_parser("slots")
    sl.add_argument("--days", type=int, default=2)
    a = p.parse_args()
    {"add": cmd_add, "add-reel": cmd_add_reel, "add-carousel": cmd_add_carousel, "recaption": cmd_recaption, "list": cmd_list, "slots": cmd_slots}[a.cmd](a)
