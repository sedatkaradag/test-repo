"""Write one JSON file per queue item (and the config state) for the control
panel, so the agent can push them with ArtifactData using `file_path`.

    python scripts/panel_rows.py <out_dir>

Output: <out_dir>/queue/<slot>.json and <out_dir>/meta/state.json.
image_url is not included: the agent uploads the JPEG as a panel asset and
adds the returned url.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["slot", "entry_id", "type", "reference", "publish_at", "local_slot", "status",
          "theme", "caption", "review", "error", "media_id", "posted_at", "audio", "story_audio", "story_kind"]


def main(out):
    out = Path(out)
    (out / "queue").mkdir(parents=True, exist_ok=True)
    (out / "meta").mkdir(parents=True, exist_ok=True)
    for p in sorted((ROOT / "queue").glob("*.json")):
        item = json.loads(p.read_text(encoding="utf-8"))
        if item.get("type") == "story" and item.get("source_slot"):
            continue   # shown as the Story of its post (source row: story_video_url, story_audio)
        row = {k: item[k] for k in FIELDS if k in item}
        (out / "queue" / f"{p.stem}.json").write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    state = {k: cfg.get(k) for k in ("dry_run", "paused", "slots", "jitter_minutes")}
    # Stamped from the clock, never typed by hand.
    state["last_content_run"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    (out / "meta" / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    # Verifier decisions, one panel document per day (newest 14 days).
    reviews = ROOT / "history" / "reviews.jsonl"
    if reviews.exists():
        (out / "reviews").mkdir(parents=True, exist_ok=True)
        days = {}
        for line in reviews.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                days.setdefault(r["ts"][:10], []).append(r)
        for day in sorted(days)[-14:]:
            doc = {"day": day, "entries": days[day]}
            (out / "reviews" / f"{day}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    # Open issues (notes/issues.json): one panel document per issue; closed ones for 30 days.
    issues = ROOT / "notes" / "issues.json"
    if issues.exists():
        (out / "issues").mkdir(parents=True, exist_ok=True)
        cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()
        for i in json.loads(issues.read_text(encoding="utf-8")):
            if i["status"] == "open" or i.get("closed_at", "") >= cut[:19]:
                (out / "issues" / f"{i['id']}.json").write_text(json.dumps(i, ensure_ascii=False), encoding="utf-8")
    print(f"rows written to {out}")


if __name__ == "__main__":
    main(sys.argv[1])
