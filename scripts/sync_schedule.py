"""Panel sync schedule, derived from config.yaml so it follows any slot change.

    python3 scripts/sync_schedule.py          # JSON: the scheduled tasks that should exist

One scheduled task per time zone that has slots (posts, Reels, carousel). Each runs at a
single minute past the hour, picked so that every slot in that zone is synced at least
MIN_DELAY minutes after its nominal time (covers the ±jitter and a late publisher) and as
soon as possible after that. Cron is written in the slot's own zone, so DST is automatic.
The agent compares this list with the existing scheduled tasks named NAME_PREFIX and
creates, updates or deletes so they match (AGENT.md, "Panel senkronu").
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NAME_PREFIX = "Halal Algorithm – panel senkronu · "
MIN_DELAY = 17  # minutes after the nominal slot time (jitter 5 + publisher slack; avoids :00/:30)

PROMPT = """You are the panel sync run for the Instagram page @thehalalalgorithm. Nobody is watching this run: do not ask questions, decide and report. Keep it short; this is a light run.

1. Make sure the GitHub repository sedatkaradag/test-repo is available (use the add_repo tool with owner "sedatkaradag", repo "test-repo", access "push" if it is not already attached), then clone it: `git clone --depth 1 https://github.com/sedatkaradag/test-repo /home/claude/test-repo` (or `git pull` if it already exists).
2. Read /home/claude/test-repo/AGENT.md and follow its "Panel senkronu (her slottan sonra)" section exactly, including the schedule check. The control panel URL is in its "Kontrol paneli" section. Do not generate post content and do not change the queue, config or images; the only commits allowed are approved comment replies in comments/outbox, as AGENT.md describes. Never send a comment reply the owner has not approved in the panel.
3. Finish with a report in Turkish: first the number of comment replies waiting for the owner's approval and any comment left to the owner, then problems (a post past its time still ready/publishing, failed or missed, panel write errors, schedule changes made). If everything is fine, a single line."""


def all_slots(cfg):
    slots = list(cfg.get("slots") or [])
    for key in ("reels", "carousel"):
        sec = cfg.get(key) or {}
        if sec.get("enabled") and sec.get("slot"):
            slots.append(sec["slot"])
    return slots


def plan(cfg):
    by_tz = {}
    for s in all_slots(cfg):
        h, m = map(int, str(s["time"]).split(":"))
        by_tz.setdefault(s["tz"], []).append((h, m, s["name"]))
    tasks = []
    for tz, items in sorted(by_tz.items()):
        best = None
        for minute in range(60):
            delays = [(minute - m) % 60 for _, m, _ in items]
            delays = [d if d >= MIN_DELAY else d + 60 for d in delays]
            if max(delays) >= 75:
                continue
            key = (max(delays), sum(delays), minute)
            if best is None or key < best[0]:
                best = (key, minute, delays)
        _, minute, delays = best
        hours = sorted({((h * 60 + m + d) // 60) % 24 for (h, m, _), d in zip(items, delays)})
        tasks.append({
            "name": NAME_PREFIX + tz,
            "cron_expression": f"CRON_TZ={tz} {minute} {','.join(map(str, hours))} * * *",
            "slots": [f"{n} {h:02d}:{m:02d}" for h, m, n in items],
        })
    return tasks


if __name__ == "__main__":
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    print(json.dumps({"tasks": plan(cfg), "prompt": PROMPT}, ensure_ascii=False, indent=2))
