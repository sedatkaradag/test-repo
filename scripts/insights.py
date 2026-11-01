"""Nightly (twice a day): pull performance numbers so the analyst run can learn what works. No AI here.

Writes:
  history/insights.json        latest snapshot: every post of the last 45 days with its numbers,
                               plus the account block (followers, demographics, online hours)
  history/account_daily.jsonl  one row per UTC day: followers, follows / unfollows, reach split into
                               followers and non-followers, accounts engaged (kept, never overwritten)
  history/story_insights.jsonl one row per Story: reach, views, navigation (forward, back, exit,
                               next), replies, shares, follows, profile visits. Instagram only gives
                               Story numbers for 24 hours, so each run updates the Stories still live
                               and the last reading is kept.

Metric names change between API versions, so each metric is requested on its own and a missing one
is counted (unavailable_metrics) instead of failing the whole run.
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
DAILY = ROOT / "history" / "account_daily.jsonl"
STORIES = ROOT / "history" / "story_insights.jsonl"
MEDIA_METRICS = ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions",
                 "follows", "profile_visits", "reposts"]
# Reels only: average and total watch time (milliseconds), and the skip rate (share of views
# that left within the first 3 seconds).
REEL_METRICS = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "reels_skip_rate"]
STORY_METRICS = ["reach", "views", "replies", "shares", "follows", "profile_visits", "total_interactions"]
DEMOGRAPHICS = ["follower_demographics", "engaged_audience_demographics"]
BREAKDOWNS = ["country", "city", "age", "gender"]

unavailable = {}   # metric -> count of requests that returned no value (shown in the run's log)
errors = {}        # metric -> first error message, to tell "not enough data" from a wrong request


def get(base, path, token, **params):
    params["access_token"] = token
    r = requests.get(base + path, params=params, timeout=60)
    try:
        return r.json()
    except ValueError:
        return {"error": {"message": r.text[:200]}}


def miss(name, data):
    unavailable[name] = unavailable.get(name, 0) + 1
    if name not in errors and isinstance(data, dict) and data.get("error"):
        errors[name] = str(data["error"].get("message", ""))[:160]


def value(data):
    """The plain value of a single-metric insights response, or None."""
    try:
        return data["data"][0]["values"][0]["value"]
    except (KeyError, IndexError, TypeError):
        try:
            return data["data"][0]["total_value"]["value"]
        except (KeyError, IndexError, TypeError):
            return None


def breakdown(data):
    """{dimension value: number} of a total_value response with one breakdown, or None."""
    try:
        results = data["data"][0]["total_value"]["breakdowns"][0]["results"]
    except (KeyError, IndexError, TypeError):
        return None
    return {"/".join(r["dimension_values"]): r["value"] for r in results}


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def media_stats(base, token, posts):
    for row in posts:
        stats = {}
        metrics = MEDIA_METRICS + (REEL_METRICS if row.get("type") == "reel" else [])
        for m in metrics:
            data = get(base, f"{row['media_id']}/insights", token, metric=m)
            v = value(data)
            if v is None:
                miss(m, data)
            else:
                stats[m] = v
        row["stats"] = stats


def story_stats(base, token, rows, now):
    """Update the Story file for every Story still inside Instagram's 24-hour window."""
    kept = {r["story_media_id"]: r for r in read_jsonl(STORIES)}
    for row in rows:
        sid = row.get("story_media_id")
        if not sid:
            continue
        posted = dt.datetime.fromisoformat(row["posted_at"])
        rec = kept.get(sid) or {"story_media_id": sid, "source_slot": row.get("slot", ""),
                                "entry_id": row["entry_id"], "type": row.get("type", ""),
                                "story_kind": row.get("story_kind", ""), "posted_at": row["posted_at"]}
        age = (now - posted).total_seconds() / 3600
        if age > 24.5:
            kept[sid] = rec   # numbers are no longer available; keep the last reading
            continue
        stats = {}
        for m in STORY_METRICS:
            data = get(base, f"{sid}/insights", token, metric=m)
            v = value(data)
            if v is None:
                miss("story_" + m, data)
            else:
                stats[m] = v
        data = get(base, f"{sid}/insights", token, metric="navigation",
                   breakdown="story_navigation_action_type")
        nav = breakdown(data)
        if nav is None:
            miss("story_navigation", data)
        else:
            stats["navigation"] = {k.lower(): v for k, v in nav.items()}
        if stats:
            rec.update(stats=stats, measured_at=now.isoformat(timespec="seconds"), age_hours=round(age, 1))
        kept[sid] = rec
    write_jsonl(STORIES, sorted(kept.values(), key=lambda r: r["posted_at"]))
    return sum(1 for r in kept.values() if r.get("measured_at", "")[:13] == now.isoformat()[:13])


def account_block(base, token, user):
    account = {}
    data = get(base, f"{user}", token, fields="followers_count,media_count")
    account.update({k: data.get(k) for k in ("followers_count", "media_count")})
    data = get(base, f"{user}/insights", token, metric="online_followers", period="lifetime")
    account["online_followers_by_utc_hour"] = value(data)
    if account["online_followers_by_utc_hour"] is None:
        miss("online_followers", data)
    for metric in DEMOGRAPHICS:
        account[metric] = {}
        for b in BREAKDOWNS:
            data = get(base, f"{user}/insights", token, metric=metric, period="lifetime",
                       timeframe="this_month", metric_type="total_value", breakdown=b)
            res = breakdown(data)
            if res is None:
                miss(f"{metric}:{b}", data)
            else:
                top = dict(sorted(res.items(), key=lambda kv: -kv[1])[:25]) if b in ("country", "city") else res
                account[metric][b] = top
    return account


def daily_row(base, token, user, account, now):
    """Numbers for the previous UTC day (Instagram's day metrics need a closed day)."""
    day_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day = day_end - dt.timedelta(days=1)
    span = {"period": "day", "metric_type": "total_value",
            "since": int(day.timestamp()), "until": int(day_end.timestamp())}
    row = {"date": day.date().isoformat(), "measured_at": now.isoformat(timespec="seconds"),
           "followers_count": account.get("followers_count"), "media_count": account.get("media_count")}
    data = get(base, f"{user}/insights", token, metric="follows_and_unfollows", breakdown="follow_type", **span)
    fu = breakdown(data)
    if fu is None:
        miss("follows_and_unfollows", data)
    else:
        # FOLLOWER = accounts that started following that day, NON_FOLLOWER = accounts that unfollowed.
        row.update(follows=fu.get("FOLLOWER", 0), unfollows=fu.get("NON_FOLLOWER", 0), follows_raw=fu)
    data = get(base, f"{user}/insights", token, metric="reach", breakdown="follow_type", **span)
    rb = breakdown(data)
    if rb is None:
        miss("reach_by_follow_type", data)
    else:
        row.update(reach_followers=rb.get("FOLLOWER", 0), reach_non_followers=rb.get("NON_FOLLOWER", 0),
                   reach_raw=rb)
    for m in ("reach", "accounts_engaged", "views"):
        data = get(base, f"{user}/insights", token, metric=m, **span)
        v = value(data)
        if v is None:
            miss(f"account_{m}", data)
        else:
            row[f"{m}_total" if m != "accounts_engaged" else m] = v
    return row


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    token, user = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    v = cfg.get("api_version", "")
    base = f"https://graph.instagram.com/{v + '/' if v else ''}"
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=45)

    rows = read_jsonl(HISTORY)
    posts = [dict(r) for r in rows if dt.datetime.fromisoformat(r["posted_at"]) >= cutoff]
    media_stats(base, token, posts)
    n_stories = story_stats(base, token, rows, now)

    account = account_block(base, token, user)
    daily = daily_row(base, token, user, account, now)
    days = [r for r in read_jsonl(DAILY) if r["date"] != daily["date"]] + [daily]
    write_jsonl(DAILY, sorted(days, key=lambda r: r["date"]))

    OUT.write_text(json.dumps({
        "fetched_at": now.isoformat(timespec="seconds"),
        "account": account,
        "unavailable_metrics": unavailable,
        "errors": errors,
        "posts": posts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"insights for {len(posts)} posts, {n_stories} live stories, day {daily['date']}")
    print(f"::notice::insights for {len(posts)} posts, {n_stories} live stories; day {daily['date']}: "
          f"{ {k: daily.get(k) for k in ('follows', 'unfollows', 'reach_followers', 'reach_non_followers', 'accounts_engaged')} }")
    print(f"::notice::no value from Instagram: {unavailable or 'none'}")
    if errors:
        print(f"::notice::first errors: {errors}")


if __name__ == "__main__":
    main()
