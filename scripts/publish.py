"""Publisher: runs every 15 minutes from GitHub Actions.

Finds queue items due in the next 15 minutes, waits for the exact minute and
publishes them through the Instagram API (or, in dry-run mode, sends a preview
to Telegram). No AI here — plain API calls.

Environment (GitHub Secrets):
    IG_USER_ID, IG_ACCESS_TOKEN          Instagram API with Instagram Login
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID optional instant alerts; without them,
                                         statuses are written to queue/*.json and
                                         the daily Claude run reports problems
    GITHUB_REPOSITORY                    set automatically by Actions
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
HISTORY = ROOT / "history" / "posted.jsonl"
WINDOW = dt.timedelta(minutes=15)
LATE_LIMIT = dt.timedelta(minutes=45)  # still publish if the runner was this late


def now():
    return dt.datetime.now(dt.timezone.utc)


def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def telegram(text, photo=None):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[telegram skipped]", text[:200])
        return
    base = f"https://api.telegram.org/bot{token}"
    try:
        if photo:
            with open(photo, "rb") as f:
                requests.post(f"{base}/sendPhoto", data={"chat_id": chat, "caption": text[:1024]},
                              files={"photo": f}, timeout=60)
        else:
            requests.post(f"{base}/sendMessage", data={"chat_id": chat, "text": text[:4000]}, timeout=30)
    except requests.RequestException as e:
        print("telegram error:", e)


def git_commit(msg):
    subprocess.run(["git", "add", "queue", "history"], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
    for _ in range(3):
        if subprocess.run(["git", "push"], cwd=ROOT).returncode == 0:
            return
        subprocess.run(["git", "pull", "--rebase"], cwd=ROOT)
    raise RuntimeError("git push failed")


class Instagram:
    def __init__(self, user_id, token, version):
        self.user_id, self.token = user_id, token
        self.base = f"https://graph.instagram.com/{version + '/' if version else ''}"

    def _call(self, method, path, **params):
        params["access_token"] = self.token
        r = requests.request(method, self.base + path, params=params, timeout=60)
        data = r.json() if r.content else {}
        if r.status_code >= 400 or "error" in data:
            raise RuntimeError(f"{path}: {data.get('error', r.text)}")
        return data

    def publish(self, image_url, caption, alt_text):
        c = self._call("POST", f"{self.user_id}/media", image_url=image_url,
                       caption=caption, alt_text=alt_text[:1000])["id"]
        return self._finish(c)

    def publish_carousel(self, image_urls, caption):
        children = []
        for u in image_urls:
            c = self._call("POST", f"{self.user_id}/media", image_url=u, is_carousel_item="true")["id"]
            self._wait(c)
            children.append(c)
        parent = self._call("POST", f"{self.user_id}/media", media_type="CAROUSEL",
                            children=",".join(children), caption=caption)["id"]
        return self._finish(parent)

    def publish_story(self, image_url):
        c = self._call("POST", f"{self.user_id}/media", image_url=image_url, media_type="STORIES")["id"]
        return self._finish(c)

    def publish_reel(self, video_url, caption, trial=True):
        params = dict(media_type="REELS", video_url=video_url, caption=caption)
        if trial:
            # Trial reels are shown to non-followers first; Instagram shares them
            # with followers automatically if they perform well.
            params["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})
        c = self._call("POST", f"{self.user_id}/media", **params)["id"]
        return self._finish(c, tries=120)

    def _finish(self, c, tries=30):
        self._wait(c, tries)
        return self._call("POST", f"{self.user_id}/media_publish", creation_id=c)["id"]

    def _wait(self, c, tries=30):
        for _ in range(tries):
            status = self._call("GET", c, fields="status_code").get("status_code")
            if status == "FINISHED":
                break
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {c} status {status}")
            time.sleep(5)
        else:
            raise RuntimeError(f"container {c} never finished")


def due_items():
    items = []
    for p in sorted(QUEUE.glob("*.json")):
        item = json.loads(p.read_text(encoding="utf-8"))
        if item["status"] != "ready":
            continue
        t = parse(item["publish_at"])
        if now() - LATE_LIMIT <= t <= now() + WINDOW:
            items.append((p, item))
        elif t < now() - LATE_LIMIT:
            item["status"] = "missed"
            p.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            telegram(f"⚠️ Missed slot {item['publish_at']} ({item['entry_id']}). It was not posted.")
    return items


def health_check(cfg):
    """Alert if nothing has been posted for 26h while live, or the queue is empty."""
    if cfg.get("dry_run"):
        return
    last = None
    if HISTORY.exists():
        lines = [l for l in HISTORY.read_text(encoding="utf-8").splitlines() if l.strip()]
        if lines:
            last = parse(json.loads(lines[-1])["posted_at"])
    ready = [p for p in QUEUE.glob("*.json") if json.loads(p.read_text())["status"] == "ready"]
    hour = now().hour
    if minute_bucket() and hour == 12:
        if last and now() - last > dt.timedelta(hours=26):
            telegram(f"⚠️ No post for {(now() - last).total_seconds() / 3600:.0f}h.")
        if not ready:
            telegram("⚠️ Queue is empty — the content run may have failed.")


def minute_bucket():
    return now().minute < 15  # run the daily checks only once an hour-slot


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if cfg.get("paused"):
        print("paused in config.yaml — nothing published")
        return
    items = due_items()
    health_check(cfg)
    if not items:
        git_commit("publisher: housekeeping")
        print("nothing due")
        return
    ig = None
    if not cfg.get("dry_run"):
        ig = Instagram(os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"], cfg.get("api_version", ""))

    for path, item in items:
        wait = (parse(item["publish_at"]) - now()).total_seconds()
        if wait > 0:
            print(f"waiting {wait:.0f}s for {item['publish_at']}")
            time.sleep(wait)
        item["status"] = "publishing"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        git_commit(f"publishing {item['entry_id']}")  # guard against double posting
        try:
            if cfg.get("dry_run"):
                telegram(f"🧪 DRY RUN — would post now\n\n{item['caption']}", photo=ROOT / item["image"])
                print(f"DRY RUN: would post {item['entry_id']} now")
                media_id = "dry-run"
            else:
                url = f"https://raw.githubusercontent.com/{repo}/main/{item['image']}"
                media_id = None
                for attempt in range(3):
                    try:
                        if item.get("images"):
                            urls = [f"https://raw.githubusercontent.com/{repo}/main/{x}" for x in item["images"]]
                            media_id = ig.publish_carousel(urls, item["caption"])
                        elif item.get("video"):
                            vurl = f"https://raw.githubusercontent.com/{repo}/main/{item['video']}"
                            media_id = ig.publish_reel(vurl, item["caption"], item.get("trial", True))
                        else:
                            media_id = ig.publish(url, item["caption"], item["alt_text"])
                        break
                    except Exception as e:  # noqa: BLE001
                        print(f"attempt {attempt + 1} failed: {e}")
                        if attempt == 2:
                            raise
                        time.sleep(30 * (attempt + 1))
                telegram(f"✅ Posted {item['reference']} ({item['entry_id']})")
                # Same post as a Story; a failed Story never fails the feed post.
                if cfg.get("stories", True) and item.get("story_image") and not item.get("video") and not item.get("images"):
                    try:
                        surl = f"https://raw.githubusercontent.com/{repo}/main/{item['story_image']}"
                        item["story_media_id"] = ig.publish_story(surl)
                    except Exception as e:  # noqa: BLE001
                        item["story_error"] = str(e)[:300]
                        print(f"story failed: {e}")
            item["status"] = "published" if media_id != "dry-run" else "dry_run_sent"
            item["media_id"] = media_id
            item["posted_at"] = now().isoformat(timespec="seconds")
            if media_id != "dry-run":
                HISTORY.parent.mkdir(exist_ok=True)
                with HISTORY.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"entry_id": item["entry_id"], "entry_ids": item.get("entry_ids"),
                                        "media_id": media_id,
                                        "posted_at": item["posted_at"], "theme": item.get("theme", ""),
                                        "slot": item.get("slot", ""), "type": item["type"]},
                                       ensure_ascii=False) + "\n")
        except Exception as e:  # noqa: BLE001
            item["status"] = "failed"
            item["error"] = str(e)[:500]
            telegram(f"❌ Failed to post {item['entry_id']}: {str(e)[:300]}")
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        git_commit(f"{item['status']}: {item['entry_id']}")


if __name__ == "__main__":
    sys.exit(main())
