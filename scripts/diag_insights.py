"""DIAG branch only: raw responses for follows_and_unfollows variants (never merged)."""
import datetime as dt, json, os, requests
token, user = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
base = "https://graph.instagram.com/v26.0/"
now = dt.datetime.now(dt.timezone.utc); end = now.replace(hour=0, minute=0, second=0, microsecond=0); start = end - dt.timedelta(days=1)
variants = {
    "day_breakdown_since": dict(metric="follows_and_unfollows", period="day", metric_type="total_value", breakdown="follow_type", since=int(start.timestamp()), until=int(end.timestamp())),
    "day_breakdown_nosince": dict(metric="follows_and_unfollows", period="day", metric_type="total_value", breakdown="follow_type"),
    "day_total_nobreakdown": dict(metric="follows_and_unfollows", period="day", metric_type="total_value"),
    "week_since": dict(metric="follows_and_unfollows", period="day", metric_type="total_value", breakdown="follow_type", since=int((end - dt.timedelta(days=7)).timestamp()), until=int(end.timestamp())),
    "follower_count_ts": dict(metric="follower_count", period="day", since=int((end - dt.timedelta(days=7)).timestamp()), until=int(end.timestamp())),
}
for k, p in variants.items():
    p["access_token"] = token
    r = requests.get(base + f"{user}/insights", params=p, timeout=60).json()
    print(f"::notice::DIAG {k}: {json.dumps(r)[:700]}")
