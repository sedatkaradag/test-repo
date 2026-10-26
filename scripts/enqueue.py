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
from integrity import check as integrity_check, unknown_lowercase

QUEUE = ROOT / "queue"

# Islamic terms that are correct in English captions but unknown to a dictionary.
CAPTION_TERMS = {
    "dua", "duas", "du'a", "sabr", "shukr", "tawbah", "tawakkul", "dhikr", "sunnah", "deen",
    "akhlaq", "ibadah", "alhamdulillah", "subhanallah", "insha", "inshallah", "mashallah",
    "jazakallah", "khair", "jumu", "ah", "salah", "salat", "sadaqah", "zakah", "ummah",
    "imaan", "iman", "taqwa", "jannah", "akhirah", "dunya", "qur", "an", "hadith", "ahadith",
    "ayah", "ayat", "surah", "ramadan", "eid", "hajj", "umrah", "astaghfirullah",
}

# Everyday modern words the dictionary does not know but which are correct English
# (a caption once had to swap "app" and "inbox" only to get past the check). Captions only;
# the source-text typo checks in integrity.py stay as strict as before.
CAPTION_TERMS |= {
    "app", "apps", "inbox", "inboxes", "smartphone", "smartphones", "selfie", "selfies",
    "podcast", "podcasts", "playlist", "playlists", "livestream", "livestreams", "wifi",
    "hashtag", "hashtags", "repost", "reposts", "dms", "texting", "texted", "voicemail",
    "overthink", "overthinking", "overthinker", "doomscroll", "doomscrolling",
}


REVIEWS = ROOT / "history" / "reviews.jsonl"


def require_approval(entry_id, slot, after=None, manual=False):
    """Refuse unless the verifier's latest recorded decision for this entry in this slot is an
    approval (history/reviews.jsonl, written by review_log.py). `after`: the approval must be newer
    than this time (a held item needs a fresh verifier). One-off posts may be logged with --slot manual."""
    slots = {slot, "manual"} if manual else {slot}
    rows = []
    if REVIEWS.exists():
        for line in REVIEWS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("entry_id") == entry_id and r.get("slot") in slots:
                    rows.append(r)
    if manual:   # a manual approval only counts for a few hours
        cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6)).isoformat()
        rows = [r for r in rows if r.get("slot") == slot or r["ts"] >= cut[:19]]
    if not rows:
        sys.exit(f"REJECT: no recorded verifier decision for {entry_id} in {slot}; "
                 "run the verifier and log it with review_log.py first")
    last = rows[-1]
    if last["verdict"] != "approve":
        sys.exit(f"REJECT: the verifier's latest decision for {entry_id} in {slot} is '{last['verdict']}'")
    if after and last["ts"] <= after:
        sys.exit(f"REJECT: no verifier approval for {entry_id} in {slot} after it was put on hold ({after})")
    return last


def require_integrity(entry_ids):
    """Hard stop on any text or rendering problem; return verifier flags."""
    flags = []
    for i in entry_ids:
        hard, f = integrity_check(i)
        if hard:
            sys.exit(f"REJECT integrity {i}: " + "; ".join(hard))
        flags += [f"{i}: {x}" for x in f]
    return flags


def config():
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def slot_utc(date_str, slot, tz):
    local = dt.datetime.fromisoformat(f"{date_str}T{slot}:00").replace(tzinfo=ZoneInfo(tz))
    return local.astimezone(dt.timezone.utc)


def slot_by_key(cfg, key):
    """'2026-10-21_us-evening' -> (slot dict, local date)."""
    date_str, _, name = key.partition("_")
    for s in all_slots(cfg):
        if s["name"] == name and slot_active(s, date_str):
            return s, date_str
    raise SystemExit(f"REJECT: unknown slot '{name}' (see config.yaml)")


def all_slots(cfg):
    """Every slot: feed posts, Reels (each Reels slot names its content: quran or hadith) and the
    carousel. A slot may carry `from` / `until` (local dates) while the schedule changes."""
    slots = list(cfg["slots"])
    reels = cfg.get("reels") or {}
    if reels.get("enabled"):
        for s in reels.get("slots") or ([reels["slot"]] if reels.get("slot") else []):
            slots.append({**s, "type": "reel"})
    car = cfg.get("carousel") or {}
    if car.get("enabled") and car.get("slot"):
        slots.append({**car["slot"], "type": "carousel"})
    return slots


def slot_active(s, date):
    """Is slot `s` in use on local date `date` (a date or 'YYYY-MM-DD')?"""
    d = date if isinstance(date, str) else date.isoformat()
    return str(s.get("from", "0000")) <= d <= str(s.get("until", "9999"))


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
            if not slot_active(s, date):
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
    paras = [p for p in paras if not p.startswith("#") and not p.lower().startswith("recitation:")]
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
    if re.search("[\u2014\u2013]", caption):
        problems.append("no long dashes (\u2014 or \u2013) in captions; use a comma, a full stop or a new line")
    if re.search(r"translation\s*:|translated by|quranenc|rowwad", caption, re.I):
        problems.append("do not name the translation source in the caption")
    # Spelling: every lowercase word outside hashtags must be a real word or a known term.
    body = re.sub(r"#\w+", " ", caption)
    odd = [w for w in unknown_lowercase(body) if w not in CAPTION_TERMS]
    if odd:
        problems.append(f"possible spelling mistake in caption: {', '.join(odd)}")
    # Any quotation in the caption must be copied from the database text.
    src = re.sub(r"\W+", " ", entry["english"]).lower()
    for q in re.findall(r"[“\"]([^”\"]{8,})[”\"]", caption):
        if re.sub(r"\W+", " ", q).lower().strip() not in src:
            problems.append("caption quotes text that is not in the verified source")
    # Variety: no repeated closing line, no near-identical hashtag sets.
    recent = recent_captions(exclude_slot=exclude_slot)
    if closing_line(caption) and closing_line(caption) in {closing_line(c) for c in recent}:
        problems.append("closing line repeats one of the last 8 captions; phrase it differently")
    for c in recent[-4:]:
        other = hashtags(c)
        if tags and other and len(tags & other) / len(tags | other) > 0.5:
            problems.append("hashtags too similar to a recent post; rotate them")
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
    flags = require_integrity([a.entry])

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
    if not getattr(a, "check", False):
        require_approval(a.entry, a.slot, manual="_manual-" in a.slot)
    if (QUEUE / f"{stem}.json").exists():
        sys.exit(f"REJECT: slot {stem} already filled")

    img = QUEUE / f"{stem}.jpg"
    try:
        render(a.entry, img)
    except TooLong:
        sys.exit("REJECT: too long for one image, choose a shorter entry")

    story = QUEUE / f"{stem}_story.jpg"
    make_story(img, story)
    story_audio = recitation_plan(cfg, a.entry) if cfg.get("stories", True) else None
    story_layout = None
    if story_audio:
        story_layout = story_video(a.entry, QUEUE / f"{stem}_story.mp4", preview=not getattr(a, "check", False))

    item = {
        "entry_id": a.entry,
        "type": entry["type"],
        "reference": entry["reference"],
        "slot": a.slot,
        "publish_at": when.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "local_slot": f"{date_str} {slot['time']} {slot['tz']} (±{cfg.get('jitter_minutes', 0)} min)",
        "image": f"queue/{stem}.jpg",
        "story_image": f"queue/{stem}_story.jpg",
        **({"story_video": f"queue/{stem}_story.mp4", "story_audio": story_audio} if story_audio else {}),
        **({"story_layout": story_layout[0], "story_layout_hash": story_layout[1]} if story_layout else {}),
        "caption": caption,
        "alt_text": f"{entry['english'][:900]} ({entry['reference']})",
        "theme": a.theme,
        "review": a.review,
        "flags": flags,
        "integrity": "passed",
        "status": "ready",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (QUEUE / f"{stem}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QUEUED {stem} {a.entry} -> {img}")
    for f in flags:
        print(f"FLAG {f}")


def story_video(entry_id, out, preview=True):
    """Recitation Story of a verse post. Template v2 (verse by verse, drawn again on GitHub with the
    real recitation timing) when the passage fits the frame and every drawn-text check passes;
    otherwise the earlier Story (the post card revealed top to bottom). Returns (layout, hash) or None."""
    import reels as RL
    try:
        layout = RL.plan_story(entry_id)
        if RL.issues(layout):
            raise RL.TooLong("drawn-text check failed")
    except RL.TooLong:
        render_reel(entry_id, out, label="TODAY'S REMINDER")
        return None
    if preview:
        RL.render_video(layout, out)
    return layout, RL.layout_hash(layout)


def reel_cover(video, out):
    """9:16 cover for the profile grid and Reels tab: the last frame, the finished card."""
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", str(video),
                    "-frames:v", "1", "-q:v", "2", str(out)], check=True)


def pick_reciter(reciters, history, window=30):
    """Weighted rotation: each reciter's share of the last `window` recitations follows its
    `weight` in config.yaml (popular voices more often); never the same reciter twice in a row."""
    recent = history[-window:]
    last = recent[-1] if recent else None
    def score(k):
        r = reciters[k]
        w = float(r.get("weight", 1))
        return ((recent.count(r["id"]) + 1) / w, -w, k)
    order = sorted(range(len(reciters)), key=score)
    for k in order:
        if reciters[k]["id"] != last or len(reciters) == 1:
            return reciters[k]
    return reciters[order[0]]


def recitation_plan(cfg, entry_id):
    """Recitation for a verse video: the next reciter in rotation (over every Reel and Story that
    already has one) and the verse files, one per verse on the card. None when switched off."""
    rec = (cfg.get("reels") or {}).get("recitation") or {}
    if not entry_id.startswith("quran:") or not rec.get("enabled") or not rec.get("reciters"):
        return None
    reciters = rec["reciters"]
    planned = []
    for i in queued():
        if i.get("status") == "deleted":
            continue
        for key in ("audio", "story_audio"):
            if i.get(key):
                planned.append((i.get("publish_at", ""), i[key].get("assigned") or i[key]["reciter"]))
    nxt = pick_reciter(reciters, [r for _, r in sorted(planned)])
    m = re.fullmatch(r"quran:(\d+):(\d+)(?:-(\d+))?", entry_id)
    sura, first, end = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
    return {"reciter": nxt["id"], "reciter_name": nxt["name"],
            "ayahs": [f"{sura:03d}{v:03d}" for v in range(first, end + 1)], "done": False}


def reel_hooks(n=10, exclude_slot=None):
    """First lines (hooks) of the latest Reels, newest last."""
    reels = [i for i in queued() if i.get("type") == "reel" and i.get("slot") != exclude_slot
             and i.get("status") != "deleted"]
    reels.sort(key=lambda i: i["publish_at"])
    return [i["caption"].strip().splitlines()[0] for i in reels[-n:] if i.get("caption")]


def _opening(line, k=2):
    return " ".join(re.findall(r"[a-z0-9']+", line.lower())[:k])


def cmd_add_reel(a):
    """A Reel with its own verse or hadith (never a copy of a feed post), in template v2:
    verses light up one by one in gold with the recitation, hadith phrases in silver, silent.
    Each Reels slot names its content (config.yaml -> reels.slots[].content)."""
    import reels as RL
    cfg = config()
    entry = get(a.entry)
    base_ids = {a.entry}
    m = re.fullmatch(r"quran:(\d+):(\d+)-(\d+)", a.entry)
    if m:
        s, x, y = map(int, m.groups())
        base_ids = {f"quran:{s}:{v}" for v in range(x, y + 1)} | {a.entry}
    recent = used_ids(cfg["repeat_days"]) | {i["entry_id"] for i in queued() if i.get("status") != "deleted"}
    for i in queued():
        recent |= set(i.get("entry_ids") or [])
    if base_ids & recent:
        sys.exit(f"REJECT: {a.entry} was posted or queued recently (Reels must not repeat a post)")
    if entry["type"] == "hadith" and entry["status"] not in ("sahih", "hasan"):
        sys.exit("REJECT: hadith grade not sahih/hasan")
    flags = require_integrity([a.entry])

    if a.at:
        # One-off Reel at a given UTC time (owner asked for it explicitly).
        when = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00")).astimezone(dt.timezone.utc).replace(microsecond=0)
        date_str = when.strftime("%Y-%m-%d")
        slot = {"time": when.strftime("%H:%M"), "tz": "UTC"}
        a.slot = f"{date_str}_reel-manual-{when.strftime('%H%M')}"
        if when <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=20):
            sys.exit("REJECT: time is in the past or too close")
    else:
        slot, date_str = slot_by_key(cfg, a.slot)
        if slot.get("type") != "reel":
            sys.exit(f"REJECT: {a.slot} is not a Reels slot")
        if slot.get("content") and slot["content"] != entry["type"]:
            sys.exit(f"REJECT: Reels slot {a.slot} takes {slot['content']}, not {entry['type']}")
        base = slot_utc(date_str, slot["time"], slot["tz"])
        if base <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=30):
            sys.exit("REJECT: slot is in the past or too close")
        jitter = int(cfg.get("jitter_minutes", 0)) * 60
        when = base + dt.timedelta(seconds=random.randint(-jitter, jitter))
    if not getattr(a, "check", False):
        require_approval(a.entry, a.slot, manual=bool(a.at))
    if (QUEUE / f"{a.slot}.json").exists():
        sys.exit(f"REJECT: slot {a.slot} already filled")
    when_iso = when.isoformat(timespec="seconds").replace("+00:00", "Z")

    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    if re.search(r"(?im)^recitation:", caption):
        sys.exit("REJECT caption: leave out the Recitation line; it is added automatically")
    problems = check_caption(caption, entry, exclude_slot=a.slot)
    hook = caption.splitlines()[0].strip()
    if _opening(hook) and _opening(hook) in {_opening(h) for h in reel_hooks(exclude_slot=a.slot)}:
        problems.append(f"hook starts like one of the last 10 Reels hooks (\"{_opening(hook)} ...\"); "
                        "use another kind of opening")
    if problems:
        sys.exit("REJECT caption: " + "; ".join(problems))

    # The video shows the hook (first line) and the closing line of this caption.
    try:
        layout = RL.plan(a.entry, caption)
    except RL.TooLong as e:
        sys.exit(f"REJECT: {e}")
    bad = RL.issues(layout)
    if bad:
        sys.exit("REJECT reel: " + "; ".join(bad))

    # Verse Reels carry the recitation of exactly the verses on the frame.
    audio, status = recitation_plan(cfg, a.entry), "ready"
    if audio:
        caption = f"{caption}\n\nRecitation: {audio['reciter_name']}"
        status = "audio_pending"   # GitHub draws the final video with the recitation, then marks it ready

    img = QUEUE / f"{a.slot}.jpg"
    RL.still(layout, img)                     # the finished frame: panel card and cover
    cover = QUEUE / f"{a.slot}_cover.jpg"
    cover.write_bytes(img.read_bytes())
    video = QUEUE / f"{a.slot}.mp4"
    if not getattr(a, "check", False):
        RL.render_video(layout, video)        # preview timing; verse Reels are redrawn on GitHub
    item = {
        "entry_id": a.entry,
        "type": "reel",
        "content_type": entry["type"],
        "template": RL.TEMPLATE,
        "reference": entry["reference"],
        "slot": a.slot,
        "publish_at": when_iso,
        "local_slot": f"{date_str} {slot['time']} {slot['tz']} (±{cfg.get('jitter_minutes', 0)} min)",
        "image": f"queue/{a.slot}.jpg",
        "video": f"queue/{a.slot}.mp4",
        "cover": f"queue/{a.slot}_cover.jpg",
        "trial": bool((cfg.get("reels") or {}).get("trial", True)),
        "caption": caption,
        "alt_text": f"{entry['english'][:900]} ({entry['reference']})",
        "theme": a.theme,
        "review": a.review,
        "flags": flags,
        "integrity": "passed",
        "status": status,
        "reel_layout": layout,
        "layout_hash": RL.layout_hash(layout),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    if audio:
        item["audio"] = audio
    (QUEUE / f"{a.slot}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QUEUED REEL {a.slot} {a.entry} ({entry['type']}) at {when_iso} -> {video}")


def cmd_add_story(a):
    """Stand-alone recitation Story for a verse post (e.g. one that went out with no Story)."""
    cfg = config()
    src = json.loads((QUEUE / f"{a.source}.json").read_text(encoding="utf-8"))
    if not src["entry_id"].startswith("quran:"):
        sys.exit("REJECT: recitation Stories are for verse posts")
    require_integrity([src["entry_id"]])
    when = dt.datetime.fromisoformat(a.at.replace("Z", "+00:00")).astimezone(dt.timezone.utc).replace(microsecond=0)
    if when <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
        sys.exit("REJECT: time is in the past or too close")
    slot = f"{a.source}_story-{when.strftime('%H%M')}"
    if (QUEUE / f"{slot}.json").exists():
        sys.exit(f"REJECT: {slot} already exists")
    audio = recitation_plan(cfg, src["entry_id"])
    video = QUEUE / f"{slot}.mp4"
    render_reel(src["entry_id"], video, label="TODAY'S REMINDER")
    item = {
        "entry_id": src["entry_id"], "type": "story", "source_slot": a.source,
        "reference": src["reference"], "slot": slot,
        "publish_at": when.isoformat().replace("+00:00", "Z"),
        "local_slot": f"{when.strftime('%Y-%m-%d %H:%M')} UTC",
        "image": src.get("story_image") or src.get("story_image_skipped") or src["image"],
        "video": f"queue/{slot}.mp4", "caption": "", "theme": src.get("theme", ""),
        "review": src.get("review", ""), "integrity": "passed",
        "status": "audio_pending" if audio else "ready",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    if audio:
        item["audio"] = audio
    (QUEUE / f"{slot}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QUEUED STORY {slot} ({src['entry_id']}) at {item['publish_at']}")


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
    if not getattr(a, "check", False):
        require_approval(",".join(ids), a.slot)
    if (QUEUE / f"{a.slot}.json").exists():
        sys.exit(f"REJECT: slot {a.slot} already filled")
    recent = used_ids(cfg["repeat_days"]) | {i["entry_id"] for i in queued() if i.get("status") != "deleted"}
    entries = []
    for i in ids:
        e = get(i)
        if e["type"] == "hadith" and e["status"] not in ("sahih", "hasan"):
            sys.exit(f"REJECT: {i} grade not sahih/hasan")
        if i in recent:
            sys.exit(f"REJECT: {i} was posted or queued recently")
        entries.append(e)
    flags = require_integrity(ids)
    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    problems = []
    body = re.sub(r"#\w+", " ", caption)
    odd = [w for w in unknown_lowercase(body) if w not in CAPTION_TERMS]
    if odd:
        problems.append(f"possible spelling mistake in caption: {', '.join(odd)}")
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
    if re.search("[\u2014\u2013]", caption):
        problems.append("no long dashes (\u2014 or \u2013) in captions; use a comma, a full stop or a new line")
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
        "flags": flags,
        "integrity": "passed",
        "status": "ready",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (QUEUE / f"{stem}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QUEUED CAROUSEL {stem}: {len(images)} cards")


def cmd_recaption(a):
    """Replace the caption of a queued (not yet published) item, with all checks."""
    path = QUEUE / f"{a.slot}.json"
    item = json.loads(path.read_text(encoding="utf-8"))
    if item["status"] not in ("ready", "hold"):
        sys.exit(f"REJECT: {a.slot} is {item['status']}")
    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    problems = check_caption(caption, get(item["entry_id"]), exclude_slot=a.slot)
    if problems:
        sys.exit("REJECT caption: " + "; ".join(problems))
    if caption == item["caption"]:
        print(f"UNCHANGED {a.slot}")
        return
    # The approved text changed, so the item waits for a fresh verifier (approve puts it back).
    if item.get("type") == "reel" and item.get("template") == "v2":
        if re.search(r"(?im)^recitation:", caption):
            sys.exit("REJECT caption: leave out the Recitation line; it is added automatically")
        rec = re.search(r"(?m)^Recitation: .*$", item["caption"])
        item["caption"] = caption + (f"\n\n{rec.group(0)}" if rec else "")
        item["flags"] = redraw_reel_v2(item, a.slot)   # the video shows the hook and closing line
        caption = item["caption"]
    item["caption"] = caption
    item["status"] = "hold"
    item["hold_reason"] = "caption changed after approval; needs a fresh verifier"
    item["held_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RECAPTIONED {a.slot} -> hold until a fresh verifier approves (enqueue.py approve)")


def redraw_reel_v2(item, stem):
    """Plan and draw a template v2 Reel again from its current caption; the recitation is mixed
    again on GitHub after a fresh approval. Returns the integrity flags."""
    import reels as RL
    flags = require_integrity([item["entry_id"]])
    try:
        layout = RL.plan(item["entry_id"], item["caption"])
    except RL.TooLong as e:
        sys.exit(f"REJECT: {e}")
    bad = RL.issues(layout)
    if bad:
        sys.exit("REJECT reel: " + "; ".join(bad))
    RL.still(layout, QUEUE / f"{stem}.jpg")
    (ROOT / item["cover"]).write_bytes((QUEUE / f"{stem}.jpg").read_bytes())
    RL.render_video(layout, QUEUE / f"{stem}.mp4")
    item.update(reel_layout=layout, layout_hash=RL.layout_hash(layout))
    if item.get("audio"):
        for k in ("seconds", "video_seconds", "verse_seconds", "timing", "added_at", "tried", "silent"):
            item["audio"].pop(k, None)
        item["audio"].update(done=False, failed=False)
    return flags


def cmd_rerender(a):
    """Re-draw a queued item's images (and video) after a renderer fix. The item
    goes on hold: it is not published until a fresh verifier approves it."""
    path = QUEUE / f"{a.slot}.json"
    item = json.loads(path.read_text(encoding="utf-8"))
    if item["status"] not in ("ready", "hold"):
        sys.exit(f"REJECT: {a.slot} is {item['status']}")
    stem = a.slot
    if item["type"] == "carousel":
        ids = item["entry_ids"]
        flags = require_integrity(ids)
        for n, i in enumerate(ids, start=1):   # card 0 is the cover (no verse text)
            render(i, QUEUE / f"{stem}_{n}.jpg")
    elif item["type"] == "reel" and item.get("template") == "v2":
        flags = redraw_reel_v2(item, stem)
    elif item["type"] == "reel":
        flags = require_integrity([item["entry_id"]])
        if item.get("image") == f"queue/{stem}.jpg":   # Reels with their own content keep their own card
            render(item["entry_id"], QUEUE / f"{stem}.jpg")
        render_reel(item["entry_id"], QUEUE / f"{stem}.mp4")
        if item.get("cover"):
            reel_cover(QUEUE / f"{stem}.mp4", ROOT / item["cover"])
    else:
        flags = require_integrity([item["entry_id"]])
        render(item["entry_id"], QUEUE / f"{stem}.jpg")
        make_story(QUEUE / f"{stem}.jpg", QUEUE / f"{stem}_story.jpg")
        if item.get("story_video"):
            sl = story_video(item["entry_id"], ROOT / item["story_video"])
            item.pop("story_layout", None)
            item.pop("story_layout_hash", None)
            if sl:
                item["story_layout"], item["story_layout_hash"] = sl
            for k in ("seconds", "video_seconds", "verse_seconds", "timing", "added_at", "tried"):
                item["story_audio"].pop(k, None)
            item["story_audio"].update(done=False, failed=False)
    item.update(status="hold", flags=flags, integrity="passed",
                held_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                review="re-rendered; waiting for a fresh verifier",
                rerendered_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RERENDERED {stem} (on hold until approved)")


def cmd_hold(a):
    path = QUEUE / f"{a.slot}.json"
    item = json.loads(path.read_text(encoding="utf-8"))
    if item["status"] != "ready":
        sys.exit(f"REJECT: {a.slot} is {item['status']}")
    item.update(status="hold", review=a.reason,
                held_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"HELD {a.slot}")


def cmd_approve(a):
    """Put a held item back in the queue after a fresh verifier approved it."""
    path = QUEUE / f"{a.slot}.json"
    item = json.loads(path.read_text(encoding="utf-8"))
    if item["status"] != "hold":
        sys.exit(f"REJECT: {a.slot} is {item['status']}")
    ids = item.get("entry_ids") or [item["entry_id"]]
    require_approval(item["entry_id"], item["slot"], after=item.get("held_at"))
    item["flags"] = require_integrity(ids)
    if dt.datetime.fromisoformat(item["publish_at"].replace("Z", "+00:00")) <= dt.datetime.now(dt.timezone.utc):
        sys.exit("REJECT: publish time has passed; enqueue it in a new slot")
    status = "ready"
    au = item.get("audio")
    if item.get("template") == "v2" and au and not au.get("done"):
        status = "audio_pending"   # re-rendered verse Reel: GitHub adds the recitation again
    item.update(status=status, review=a.review)
    item.pop("hold_reason", None)
    item.pop("held_at", None)
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"APPROVED {a.slot}")


def cmd_list(_):
    for i in queued():
        print(f"{i['publish_at']}  {i.get('slot', ''):<28} {i['status']:<13} {i['entry_id']:<24} {i.get('theme', '')}")


def cmd_slots(a):
    cfg = config()
    filled = {i.get("slot") for i in queued()}
    for when, key, s in upcoming_slots(cfg, a.days):
        if key not in filled:
            kind = s.get("type", "any") + (f"/{s['content']}" if s.get("content") else "")
            print(f"EMPTY {key:<28} {kind:<12} base {when.isoformat().replace('+00:00', 'Z')}  ({s['time']} {s['tz']})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    ad = sub.add_parser("add")
    ad.add_argument("--entry", required=True)
    ad.add_argument("--slot", required=True, help="slot key printed by `slots` (e.g. 2026-10-21_us-evening), or 'now' for a one-off post in ~4 minutes")
    ad.add_argument("--caption-file", required=True)
    ad.add_argument("--theme", default="")
    ad.add_argument("--review", default="")
    ad.add_argument("--check", action="store_true",
                    help="run every code check (and the card fit) without queueing anything; run this before the verifier")
    st = sub.add_parser("add-story")
    st.add_argument("--source", required=True, help="slot of a verse post")
    st.add_argument("--at", required=True, help="UTC time, e.g. 2026-10-21T17:20:00Z")
    ar = sub.add_parser("add-reel")
    ar.add_argument("--entry", required=True, help="its own verse or hadith id, never a feed post's")
    ar.add_argument("--slot", help="reel slot key, e.g. 2026-10-21_reel")
    ar.add_argument("--at", help="one-off: UTC time instead of a slot, e.g. 2026-10-21T19:30:00Z")
    ar.add_argument("--caption-file", required=True)
    ar.add_argument("--theme", default="")
    ar.add_argument("--review", default="")
    ar.add_argument("--check", action="store_true",
                    help="run every code check (and the card fit) without queueing anything; run this before the verifier")
    ac = sub.add_parser("add-carousel")
    ac.add_argument("--entries", required=True, help="comma-separated ids, 3-7")
    ac.add_argument("--slot", required=True, help="carousel slot key, e.g. 2026-10-21_carousel")
    ac.add_argument("--title", required=True, help="cover title, e.g. '5 Hadith on Patience'")
    ac.add_argument("--subtitle", default="")
    ac.add_argument("--caption-file", required=True)
    ac.add_argument("--theme", default="")
    ac.add_argument("--review", default="")
    ac.add_argument("--check", action="store_true",
                    help="run every code check (and the card fit) without queueing anything; run this before the verifier")
    rc = sub.add_parser("recaption")
    rc.add_argument("--slot", required=True)
    rc.add_argument("--caption-file", required=True)
    rr = sub.add_parser("rerender")
    rr.add_argument("--slot", required=True)
    ho = sub.add_parser("hold")
    ho.add_argument("--slot", required=True)
    ho.add_argument("--reason", required=True)
    ap = sub.add_parser("approve")
    ap.add_argument("--slot", required=True)
    ap.add_argument("--review", required=True, help="the fresh verifier's verdict")
    sub.add_parser("list")
    sl = sub.add_parser("slots")
    sl.add_argument("--days", type=int, default=2)
    a = p.parse_args()
    run = {"add": cmd_add, "add-story": cmd_add_story, "add-reel": cmd_add_reel, "add-carousel": cmd_add_carousel,
           "recaption": cmd_recaption, "rerender": cmd_rerender, "hold": cmd_hold, "approve": cmd_approve,
           "list": cmd_list, "slots": cmd_slots}[a.cmd]
    if getattr(a, "check", False):
        # Same command, same checks, but against a throwaway copy of the queue: nothing is
        # queued, rendered into queue/ or committed. A REJECT here means: fix and check again.
        import shutil
        import tempfile
        real = QUEUE
        tmp = Path(tempfile.mkdtemp(prefix="enqueue-check-"))
        for f in real.glob("*.json"):
            shutil.copy(f, tmp / f.name)
        QUEUE = tmp
        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                run(a)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            for line in buf.getvalue().splitlines():
                if not line.startswith(("QUEUED", "queued")):
                    print(line)
        print("CHECK OK: every code check passed; nothing was queued. Now send exactly this text to the verifier.")
    else:
        run(a)
