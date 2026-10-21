"""Comments on our own posts: fetch new ones, send approved replies. Runs in GitHub Actions.

    python scripts/comments.py fetch   # hourly: new comments -> comments/inbox.json
    python scripts/comments.py send    # on push: comments/outbox/*.json -> Instagram replies

No AI here. Drafting and approval happen elsewhere: the panel sync run (Claude) drafts a
reply for each new comment into the control panel, the owner approves it there, and the next
sync run writes the approved text to comments/outbox/<comment_id>.json. Only files in the
outbox are ever sent, one reply per comment, and never twice.

Environment: IG_USER_ID, IG_ACCESS_TOKEN (needs instagram_business_manage_comments),
TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (optional alerts).
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish import Instagram, now, parse, telegram  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "comments"
INBOX = DIR / "inbox.json"
SENT = DIR / "sent.jsonl"
OUTBOX = DIR / "outbox"
LOOKBACK = dt.timedelta(days=30)   # only posts from the last 30 days are checked
MAX_SENDS = 10                     # per run
SEND_GAP = 20                      # seconds between replies


def ig():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    return Instagram(os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"], cfg.get("api_version", ""))


def load_json(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def sent_records():
    if not SENT.exists():
        return {}
    out = {}
    for line in SENT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["comment_id"]] = r
    return out


def post_refs():
    """media_id -> reference and slot, from the queue files (published items carry media_id)."""
    refs = {}
    for p in (ROOT / "queue").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("media_id"):
            refs[d["media_id"]] = {"post_ref": d.get("reference", ""), "slot": d.get("slot", p.stem)}
    return refs


def commit(msg):
    subprocess.run(["git", "add", "comments"], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return False
    subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
    for _ in range(3):
        if subprocess.run(["git", "push"], cwd=ROOT).returncode == 0:
            return True
        subprocess.run(["git", "pull", "--rebase"], cwd=ROOT)
    raise RuntimeError("git push failed")


def fetch():
    api = ig()
    me = api._call("GET", "me", fields="username")["username"]
    inbox = load_json(INBOX, {})
    refs = post_refs()
    media = api._call("GET", f"{api.user_id}/media",
                      fields="id,timestamp,permalink,comments_count", limit=50).get("data", [])
    cutoff = now() - LOOKBACK
    new = []
    for m in media:
        if parse(m["timestamp"]) < cutoff or not m.get("comments_count"):
            continue
        rows = api._call("GET", f"{m['id']}/comments", limit=50,
                         fields="id,text,username,timestamp,replies{id,text,username,timestamp}").get("data", [])
        for c in rows:
            if c.get("username") == me:
                continue
            replies = (c.get("replies") or {}).get("data", [])
            ours = [r for r in replies if r.get("username") == me]
            rec = inbox.get(c["id"], {})
            if not rec:
                new.append(c)
            rec.update({
                "comment_id": c["id"],
                "media_id": m["id"],
                "permalink": m.get("permalink", ""),
                **refs.get(m["id"], {"post_ref": "", "slot": ""}),
                "username": c.get("username", ""),
                "text": c.get("text", ""),
                "ts": c.get("timestamp", ""),
                "answered": bool(ours),
                "our_replies": [{"id": r["id"], "text": r.get("text", ""), "ts": r.get("timestamp", "")} for r in ours],
                "other_replies": len(replies) - len(ours),
            })
            inbox[c["id"]] = rec
    DIR.mkdir(exist_ok=True)
    INBOX.write_text(json.dumps(inbox, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(new)} new comment(s), {len(inbox)} in inbox")
    if commit(f"comments: {len(new)} new") and new:
        lines = [f"@{c.get('username')}: {c.get('text', '')[:200]}" for c in new[:5]]
        telegram("💬 New comment(s) — a reply draft will be in the panel after the next sync run:\n\n" + "\n".join(lines))


def send():
    files = sorted(OUTBOX.glob("*.json")) if OUTBOX.exists() else []
    if not files:
        print("outbox empty")
        return
    api = ig()
    me = api._call("GET", "me", fields="username")["username"]
    done = sent_records()
    log = []
    for i, p in enumerate(files[:MAX_SENDS]):
        item = json.loads(p.read_text(encoding="utf-8"))
        cid, msg = item["comment_id"], item["message"].strip()
        rec = {"comment_id": cid, "message": msg, "approved_at": item.get("approved_at"),
               "at": now().isoformat(timespec="seconds")}
        try:
            if cid in done and done[cid].get("status") == "sent":
                rec.update(status="skipped", error="already sent")
            elif not msg:
                rec.update(status="failed", error="empty message")
            else:
                live = api._call("GET", f"{cid}/replies", fields="id,username").get("data", [])
                if any(r.get("username") == me for r in live):
                    rec.update(status="skipped", error="already answered on Instagram")
                else:
                    if i:
                        time.sleep(SEND_GAP)
                    rid = api._call("POST", f"{cid}/replies", message=msg)["id"]
                    rec.update(status="sent", reply_id=rid)
        except Exception as e:  # noqa: BLE001 — record and continue with the next reply
            rec.update(status="failed", error=str(e)[:300])
        with SENT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        p.unlink()
        log.append(rec)
        print(rec["status"], cid, rec.get("error", ""))
    commit("comments: " + ", ".join(f"{r['status']} {r['comment_id']}" for r in log))
    for r in log:
        if r["status"] == "failed":
            telegram(f"❌ Reply to comment {r['comment_id']} failed: {r.get('error', '')}")
        elif r["status"] == "sent":
            telegram(f"✅ Reply sent: {r['message'][:200]}")


if __name__ == "__main__":
    {"fetch": fetch, "send": send}[sys.argv[1]]()
