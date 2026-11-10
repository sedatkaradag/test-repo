"""Nightly (twice a day): pull performance numbers so the analyst run can learn what works. No AI here.

Writes:
  history/insights.json        latest snapshot: every post of the last 45 days with its numbers,
                               plus the account block (followers, demographics, online hours)
  history/account_daily.jsonl  one row per Instagram day (midnight to midnight, Pacific time, as Instagram
                               counts days), every day from FIRST_DAY to yesterday, each measured on its own:
                               follows / unfollows, reach (total, followers / non-followers), views,
                               accounts engaged. Instagram fills the last days in late, so each run measures
                               the last 7 days again; older rows are kept as they are.
  history/followers.jsonl      one row per run: the followers count and when it was read.
  (insights.json "followers_check": every followers count, minus the follows and plus the unfollows
   since FIRST_DAY, must give the same number of followers before FIRST_DAY; and every day's reach and
   new follows must equal Instagram's own day-by-day series. A failed check opens an issue.)
  (insights.json also has "manual_posts": posts on the account that this system did not publish, i.e.
   the owner's hand-made Reels such as quizzes; found by listing the account's media, same numbers.)
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
# (reposts is not offered for accounts connected with Instagram Login, so it is not requested.)
MEDIA_METRICS = ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions",
                 "follows", "profile_visits"]
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


def manual_posts(base, token, user, known, cutoff):
    """The account's own posts of the last 45 days that are not in posted.jsonl (made by hand)."""
    out, path, params = [], f"{user}/media", {"fields": "id,caption,media_type,media_product_type,permalink,timestamp",
                                               "limit": 50}
    for _ in range(10):                                  # at most 500 posts back
        data = get(base, path, token, **params)
        if not isinstance(data, dict) or "data" not in data:
            miss("media_list", data)
            break
        older = False
        for m in data["data"]:
            ts = dt.datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            if ts < cutoff:
                older = True
                break
            if m["id"] in known:
                continue
            reel = m.get("media_product_type") == "REELS"
            out.append({"media_id": m["id"], "posted_at": ts.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
                        "type": "reel" if reel else m.get("media_type", "").lower(), "source": "manual",
                        "permalink": m.get("permalink", ""),
                        "caption_first_line": (m.get("caption") or "").strip().split("\n")[0][:120]})
        nxt = (data.get("paging") or {}).get("cursors", {}).get("after")
        if older or not nxt or not (data.get("paging") or {}).get("next"):
            break
        params["after"] = nxt
    media_stats(base, token, out)
    return out


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


def breakdown_or_zero(data):
    """Like breakdown(), but a reply that has the breakdown with no results means zero for every value."""
    res = breakdown(data)
    if res is not None:
        return res
    try:
        data["data"][0]["total_value"]["breakdowns"][0]
        return {}
    except (KeyError, IndexError, TypeError):
        return None


# Account numbers per Instagram day. Instagram counts days midnight to midnight, Pacific time, and reads
# `since` / `until` as whole days with the day of `until` INCLUDED: until = next midnight would add the
# next day too (that was the bug fixed on 2026-11-10, when every day also held the following day's numbers).
# So a day is asked for with until = one second before the next midnight. Checked against Instagram's own
# daily series (reach and follower_count, period=day): equal for every day from the first one.
PT = "America/Los_Angeles"
FIRST_DAY = dt.date(2026, 10, 20)   # the first day Instagram has account numbers for (earlier days are all zero)
WINDOW = "pt-day-v2"                 # rows measured with the window above; rows without it are measured again
REFRESH_DAYS = 7                     # Instagram fills the last days in late, so these are measured on every run
FOLLOWERS = ROOT / "history" / "followers.jsonl"
DAY_FIELDS = ("follows", "unfollows", "reach_total", "reach_followers", "reach_non_followers", "views_total", "accounts_engaged")


def day_span(d, end=None):
    """since / until for Instagram day `d` (or from its midnight to `end`, for today so far)."""
    from zoneinfo import ZoneInfo
    pt = ZoneInfo(PT)
    since = dt.datetime.combine(d, dt.time(), pt)
    until = end if end is not None else dt.datetime.combine(d + dt.timedelta(days=1), dt.time(), pt) - dt.timedelta(seconds=1)
    return {"period": "day", "metric_type": "total_value", "since": int(since.timestamp()), "until": int(until.timestamp())}


def follows_for(base, token, user, span):
    """(follows, unfollows) for a span, or None. FOLLOWER = accounts that started following,
    NON_FOLLOWER = accounts that unfollowed or left Instagram."""
    data = get(base, f"{user}/insights", token, metric="follows_and_unfollows", breakdown="follow_type", **span)
    fu = breakdown_or_zero(data)
    if fu is None:
        miss("follows_and_unfollows", data)
        return None
    return fu.get("FOLLOWER", 0), fu.get("NON_FOLLOWER", 0)


def day_row(base, token, user, d, now):
    span = day_span(d)
    row = {"date": d.isoformat(), "measured_at": now.isoformat(timespec="seconds"), "window": WINDOW}
    fu = follows_for(base, token, user, span)
    if fu is not None:
        row.update(follows=fu[0], unfollows=fu[1])
    data = get(base, f"{user}/insights", token, metric="reach", breakdown="follow_type", **span)
    rb = breakdown_or_zero(data)
    if rb is None:
        miss("reach_by_follow_type", data)
    else:
        row.update(reach_followers=rb.get("FOLLOWER", 0), reach_non_followers=rb.get("NON_FOLLOWER", 0))
    for m in ("reach", "accounts_engaged", "views"):
        data = get(base, f"{user}/insights", token, metric=m, **span)
        v = value(data)
        if v is None:
            miss(f"account_{m}", data)
        else:
            row[f"{m}_total" if m != "accounts_engaged" else m] = v
    return row


def series_check(base, token, user, rows, today):
    """Instagram's own day-by-day series (reach, new followers) for the last 28 days, compared with the rows."""
    from zoneinfo import ZoneInfo
    start = max(FIRST_DAY, today - dt.timedelta(days=28))
    span = {"period": "day", "since": int(dt.datetime.combine(start, dt.time(), ZoneInfo(PT)).timestamp()),
            "until": int(dt.datetime.combine(today, dt.time(), ZoneInfo(PT)).timestamp())}
    by_date = {r["date"]: r for r in rows}
    diffs, n = [], 0
    for metric, key in (("reach", "reach_total"), ("follower_count", "follows")):
        data = get(base, f"{user}/insights", token, metric=metric, **span)
        try:
            values = data["data"][0]["values"]
        except (KeyError, IndexError, TypeError):
            miss(f"series_{metric}", data)
            continue
        for v in values:
            # Instagram labels each day of these series with the UTC time of its Pacific midnight (start of the day).
            d = dt.datetime.strptime(v["end_time"], "%Y-%m-%dT%H:%M:%S%z").astimezone(ZoneInfo(PT)).date().isoformat()
            r = by_date.get(d)
            if r is None or key not in r or d >= today.isoformat():
                continue
            n += 1
            if r[key] != v.get("value"):
                diffs.append({"date": d, "metric": key, "row": r[key], "instagram_series": v.get("value")})
    return {"days_compared": n, "differences": diffs}


def daily_rows(base, token, user, now, account):
    """account_daily.jsonl: every Instagram day from FIRST_DAY to yesterday, each measured on its own.
    Also returns the follower check (followers now vs. the sum of follows - unfollows)."""
    from zoneinfo import ZoneInfo
    today = now.astimezone(ZoneInfo(PT)).date()
    kept = {r["date"]: r for r in read_jsonl(DAILY) if r.get("window") == WINDOW}
    d, rows = FIRST_DAY, []
    while d < today:
        old = kept.get(d.isoformat())
        if old is None or not all(k in old for k in DAY_FIELDS) or (today - d).days <= REFRESH_DAYS:
            new = day_row(base, token, user, d, now)
            # a complete new reading replaces the row; an incomplete one never overwrites a complete row
            if old is None or all(k in new for k in DAY_FIELDS) or not all(k in old for k in DAY_FIELDS):
                old = {**(old or {}), **new}
        rows.append(old)
        d += dt.timedelta(days=1)
    write_jsonl(DAILY, rows)

    # Follower check. Instagram gives a day's follows only after the day (today reads 0), so a follower count
    # taken during day D lies between (followers before FIRST_DAY + net follows up to D-1) and (... up to D).
    # Every count whose day is already measured gives such a range for "followers before FIRST_DAY"; all the
    # ranges must share one number. A count is checked from the run after its day closes.
    snaps = read_jsonl(FOLLOWERS)
    snaps.append({"at": now.isoformat(timespec="seconds"), "followers_count": account.get("followers_count")})
    write_jsonl(FOLLOWERS, snaps)
    net_to, total = {}, 0
    for r in rows:
        if "follows" not in r:
            break
        total += r["follows"] - r["unfollows"]
        net_to[r["date"]] = total
    lo, hi, n, bad = -10 ** 9, 10 ** 9, 0, []
    for s in snaps:
        if s.get("followers_count") is None:
            continue
        d = dt.datetime.fromisoformat(s["at"]).astimezone(ZoneInfo(PT)).date()
        if d < FIRST_DAY or d.isoformat() not in net_to:
            continue
        before = net_to.get((d - dt.timedelta(days=1)).isoformat(), 0)
        s_lo, s_hi = s["followers_count"] - net_to[d.isoformat()], s["followers_count"] - before
        n += 1
        if max(lo, s_lo) > min(hi, s_hi) + 2:    # 2 people of slack (Instagram's late corrections)
            bad.append({"at": s["at"], "followers_count": s["followers_count"], "range": [s_lo, s_hi], "common_so_far": [lo, hi]})
            continue
        lo, hi = max(lo, s_lo), min(hi, s_hi)
        if lo > hi:                               # within the slack: keep one number, not an inverted range
            lo = hi = (lo + hi) // 2
    check = {"at": now.isoformat(timespec="seconds"), "followers_count": account.get("followers_count"),
             "net_follows_through": {"date": max(net_to), "net": total} if net_to else None,
             "counts_checked": n, "followers_before_first_day": [lo, hi] if n else None, "conflicts": bad,
             "series": series_check(base, token, user, rows, today)}
    check["ok"] = len(net_to) == len(rows) and n > 0 and not bad and not check["series"]["differences"]
    return rows, check


def report_check(check):
    """Record a failed follower check as an open issue (the panel shows it; the owner's chat fixes it)."""
    import subprocess, sys
    detail = (f"followers {check.get('followers_count')}; counts that do not fit the daily follows: "
              f"{check['conflicts'][:3]}; differences from Instagram's daily series: {check['series']['differences'][:5]}")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "issues.py"), "add", "--kind", "code",
                    "--title", "Hesap istatistikleri tutarsız (takipçi kontrolü)", "--detail", detail,
                    "--source", "Gece istatistik"], check=False)
    print(f"::warning::follower check failed: {detail}")


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
    known = {str(r.get(k)) for r in rows for k in ("media_id", "story_media_id") if r.get(k)}
    manual = manual_posts(base, token, user, known, cutoff)

    account = account_block(base, token, user)
    rows, check = daily_rows(base, token, user, now, account)
    daily = rows[-1]
    if not check["ok"]:
        report_check(check)

    OUT.write_text(json.dumps({
        "fetched_at": now.isoformat(timespec="seconds"),
        "account": account,
        "unavailable_metrics": unavailable,
        "errors": errors,
        "posts": posts,
        "manual_posts": manual,
        "followers_check": check,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"insights for {len(posts)} posts, {len(manual)} hand-made posts, {n_stories} live stories, day {daily['date']}")
    print(f"::notice::insights for {len(posts)} posts, {n_stories} live stories; day {daily['date']}: "
          f"{ {k: daily.get(k) for k in ('follows', 'unfollows', 'reach_followers', 'reach_non_followers', 'accounts_engaged')} }")
    print(f"::notice::no value from Instagram: {unavailable or 'none'}")
    if errors:
        print(f"::notice::first errors: {errors}")


if __name__ == "__main__":
    main()
