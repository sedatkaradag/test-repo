"""Print how many seconds the publisher should wait before starting its next run.

Used by the self-chaining publish workflow: GitHub's scheduled (cron) runs can be
delayed or skipped, so every publish run ends by waiting until shortly before
the next queued post and then starting the next run itself.
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAD = 120          # start the next run this many seconds before the post
MAX_WAIT = 5 * 3600  # GitHub jobs may run 6h; stay well under it


def main():
    now = dt.datetime.now(dt.timezone.utc)
    upcoming = []
    for p in (ROOT / "queue").glob("*.json"):
        item = json.loads(p.read_text(encoding="utf-8"))
        if item.get("status") == "ready":
            t = dt.datetime.fromisoformat(item["publish_at"].replace("Z", "+00:00"))
            upcoming.append(t)
    future = [t for t in upcoming if t > now]
    if not future:
        print(MAX_WAIT)
        return
    wait = (min(future) - now).total_seconds() - LEAD
    print(int(max(0, min(wait, MAX_WAIT))))


if __name__ == "__main__":
    main()
