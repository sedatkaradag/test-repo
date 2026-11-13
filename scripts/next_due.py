"""Print how many seconds the publisher should wait before starting its next run.

Used by the self-chaining publish workflow: GitHub's scheduled (cron) runs can be
delayed or skipped, so every publish run ends by waiting until shortly before
the next queued post and then starting the next run itself.

A ready post whose time has already passed (for example one queued from the panel
while this run was waiting) is still published if it is less than LATE_LIMIT late,
so it counts as due: the next run starts after PAST_DUE_WAIT. That short pause keeps
a post that crashes the publisher before it is marked from restarting runs nonstop.
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAD = 120          # start the next run this many seconds before the post
MAX_WAIT = 5 * 3600  # GitHub jobs may run 6h; stay well under it
LATE_LIMIT = 45 * 60  # same as publish.py: older ready posts are marked missed, not published
PAST_DUE_WAIT = 300  # a past-due post: start the next run in 5 minutes


def main():
    now = dt.datetime.now(dt.timezone.utc)
    upcoming = []
    for p in (ROOT / "queue").glob("*.json"):
        item = json.loads(p.read_text(encoding="utf-8"))
        if item.get("status") == "ready":
            t = dt.datetime.fromisoformat(item["publish_at"].replace("Z", "+00:00"))
            upcoming.append(t)
    waits = []
    for t in upcoming:
        ahead = (t - now).total_seconds()
        if ahead > 0:
            waits.append(max(0, ahead - LEAD))
        elif -ahead <= LATE_LIMIT:
            waits.append(PAST_DUE_WAIT)
    if not waits:
        print(MAX_WAIT)
        return
    print(int(min(min(waits), MAX_WAIT)))


if __name__ == "__main__":
    main()
