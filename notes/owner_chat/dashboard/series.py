"""Rebuild series.json for build.py: every reading of every post over time, from the git history of
history/insights.json (each nightly commit is one reading).

    python3 notes/owner_chat/dashboard/series.py <repo> <work_dir>
    python3 notes/owner_chat/dashboard/build.py <work_dir> <repo>      # -> <work_dir>/rows.json
    python3 notes/owner_chat/dashboard/analyze.py <work_dir>             # -> the dashboard data files
"""
import json, subprocess, sys
from pathlib import Path

repo, work = Path(sys.argv[1]), Path(sys.argv[2])
work.mkdir(parents=True, exist_ok=True)
commits = subprocess.run(["git", "-C", str(repo), "log", "--format=%H", "--", "history/insights.json"],
                         capture_output=True, text=True, check=True).stdout.split()
ser, meta = {}, {}
for c in reversed(commits):
    txt = subprocess.run(["git", "-C", str(repo), "show", f"{c}:history/insights.json"], capture_output=True, text=True).stdout
    try:
        d = json.loads(txt)
    except ValueError:
        continue
    for p in d.get("posts", []) + d.get("manual_posts", []):
        if not p.get("stats"):
            continue
        mid = p["media_id"]
        ser.setdefault(mid, []).append([d["fetched_at"], p["posted_at"], p["stats"]])
        meta[mid] = {k: p.get(k) for k in ("entry_id", "media_id", "posted_at", "theme", "slot", "type", "source", "caption_first_line")}
json.dump({"ser": ser, "meta": meta}, open(work / "series.json", "w"), ensure_ascii=False)
print(len(commits), "readings,", len(ser), "posts")
