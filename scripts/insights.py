"""Nightly: pull performance numbers for recent posts into history/insights.json
so the analyst run can learn which themes and times work. No AI here.

Metric names change between API versions, so each metric is requested on its
own and missing ones are skipped instead of failing the whole run.
"""
import datetime as dt
import json
import os
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "history" / "posted.jsonl"
OUT = ROOT / "history" / "insights.json"
MEDIA_METRICS = ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions",
                 "follows", "profile_visits"]
# Reels only: average watch time and total watch time (milliseconds).
REEL_METRICS = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]


def get(base, path, token, **params):
    params["access_token"] = token
    r = requests.get(base + path, params=params, timeout=60)
    return r.json()


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    token, user = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    v = cfg.get("api_version", "")
    base = f"https://graph.instagram.com/{v + '/' if v else ''}"
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=45)

    posts = []
    if HISTORY.exists():
        for line in HISTORY.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if dt.datetime.fromisoformat(row["posted_at"]) >= cutoff:
                    posts.append(row)

    unavailable = {}   # metric -> how many posts Instagram gave no value for (shown in the run's log)
    for row in posts:
        stats = {}
        metrics = MEDIA_METRICS + (REEL_METRICS if row.get("type") == "reel" else [])
        for m in metrics:
            data = get(base, f"{row['media_id']}/insights", token, metric=m)
            try:
                stats[m] = data["data"][0]["values"][0]["value"]
            except (KeyError, IndexError, TypeError):
                unavailable[m] = unavailable.get(m, 0) + 1
        row["stats"] = stats

    account = {}
    data = get(base, f"{user}", token, fields="followers_count,media_count")
    account.update({k: data.get(k) for k in ("followers_count", "media_count")})
    data = get(base, f"{user}/insights", token, metric="online_followers", period="lifetime")
    try:
        account["online_followers_by_utc_hour"] = data["data"][0]["values"][0]["value"]
    except (KeyError, IndexError):
        account["online_followers_by_utc_hour"] = None

    OUT.write_text(json.dumps({
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "account": account,
        "unavailable_metrics": unavailable,
        "posts": posts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"insights for {len(posts)} posts")
    print(f"::notice::insights for {len(posts)} posts; no value from Instagram: {unavailable or 'none'}")


if __name__ == "__main__":
    main()
