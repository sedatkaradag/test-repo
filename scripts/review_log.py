"""Record every verifier decision (approve or reject) in history/reviews.jsonl.

    python scripts/review_log.py --entry hadith:muslim:6927 --slot 2026-10-21_us-evening \
        --verdict reject --round 1 --reasons "English narrator differs from the Arabic chain"

The timestamp comes from the clock. Several reasons can be separated with " | ".
"""
import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "history" / "reviews.jsonl"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entry", required=True)
    p.add_argument("--slot", default="")
    p.add_argument("--verdict", required=True, choices=["approve", "reject"])
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--reasons", default="")
    p.add_argument("--note", default="", help="e.g. 'backfilled'")
    a = p.parse_args()
    row = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "entry_id": a.entry,
        "slot": a.slot,
        "verdict": a.verdict,
        "round": a.round,
        "reasons": [r.strip() for r in a.reasons.split("|") if r.strip()],
    }
    if a.note:
        row["note"] = a.note
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"logged {a.verdict} {a.entry}")


if __name__ == "__main__":
    main()
