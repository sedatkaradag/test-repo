"""Temporary probe (branch insights-probe only): how does Instagram read since/until for account insights?
Prints one JSON line per test to the log. Never prints the token."""
import datetime as dt, json, os, requests
from zoneinfo import ZoneInfo
TOK, USER = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
B = "https://graph.instagram.com/v26.0/"
PT = ZoneInfo("America/Los_Angeles")
def get(path, **p):
    p["access_token"] = TOK
    r = requests.get(B + path, params=p, timeout=60)
    try: j = r.json()
    except ValueError: return {"error": r.text[:200]}
    if "error" in j: return {"error": str(j["error"].get("message"))[:200]}
    for k in ("paging",): j.pop(k, None)
    return j
def out(tag, **kw): print("PROBE " + json.dumps({"tag": tag, **kw}, ensure_ascii=False), flush=True)
def tv(metric, since, until, breakdown=None):
    p = {"metric": metric, "period": "day", "metric_type": "total_value", "since": since, "until": until}
    if breakdown: p["breakdown"] = breakdown
    j = get(f"{USER}/insights", **p)
    if "error" in j: return {"error": j["error"]}
    try:
        t = j["data"][0]["total_value"]
        if breakdown:
            bs = t.get("breakdowns") or []
            return {r["dimension_values"][0]: r["value"] for b in bs for r in b.get("results", [])}
        return t.get("value")
    except Exception as e: return {"raw": json.dumps(j)[:300]}
def mid(d): return int(dt.datetime.combine(d, dt.time(), PT).timestamp())
acct = get(USER, fields="followers_count,media_count,username")
out("account", followers=acct.get("followers_count"), media=acct.get("media_count"))
# first media date
med = get(f"{USER}/media", fields="timestamp", limit=100)
ts = sorted(m["timestamp"] for m in med.get("data", []))
out("media_first", first=ts[:1], n=len(ts))
today = dt.datetime.now(PT).date()
days = [today - dt.timedelta(days=k) for k in range(28, 0, -1)]
METRICS = [("follows_and_unfollows", "follow_type"), ("reach", "follow_type"), ("reach", None), ("views", None), ("accounts_engaged", None)]
for d in days:
    s, e = mid(d), mid(d + dt.timedelta(days=1))
    for m, bd in METRICS:
        out("day", d=str(d), metric=m, bd=bd,
            v_next_midnight=tv(m, s, e, bd),          # current code
            v_minus1=tv(m, s, e - 1, bd),             # until one second before next midnight
            v_same=tv(m, s, s, bd),                   # since == until
            v_noon=tv(m, s, s + 12 * 3600, bd))       # until noon of the same day
# two-day windows for additivity
for d in days[-10:-1]:
    s, e = mid(d), mid(d + dt.timedelta(days=2))
    out("two", d=str(d), f=tv("follows_and_unfollows", s, e - 1, "follow_type"), f_next=tv("follows_and_unfollows", s, e, "follow_type"))
# time series that Instagram buckets itself
for m in ("reach", "follower_count", "views", "accounts_engaged", "follows_and_unfollows"):
    j = get(f"{USER}/insights", metric=m, period="day", since=mid(days[0]), until=mid(today))
    if "error" in j: out("series", metric=m, error=j["error"]); continue
    try: out("series", metric=m, values=[(v.get("end_time"), v.get("value")) for v in j["data"][0].get("values", [])], keys=list(j["data"][0].keys()))
    except Exception: out("series", metric=m, raw=json.dumps(j)[:400])
