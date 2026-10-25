"""Open issues: problems any run noticed, kept until someone resolves them.

    python3 scripts/issues.py add --kind code --title "..." --detail "..." [--ref <slot or id>] [--source "Günlük içerik"]
    python3 scripts/issues.py close <id> --resolution "..."
    python3 scripts/issues.py list [--all]

Kinds: code (a bug in the scripts), rule (a rule was bent or skipped), content (an item was left
out or changed because of a problem), publish (posting, Story, audio or panel failures), other.
Every run that reports a problem also records it here; the main agent (owner chat) reads the open
list first and closes items with a short resolution. Stored in notes/issues.json and shown in the
control panel ("Açık sorunlar").
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "notes" / "issues.json"
KINDS = ("code", "rule", "content", "publish", "other")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load():
    return json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else []


def save(items):
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--kind", choices=KINDS, required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--detail", default="")
    a.add_argument("--ref", default="")
    a.add_argument("--source", default="")
    c = sub.add_parser("close")
    c.add_argument("id")
    c.add_argument("--resolution", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--all", action="store_true")
    args = ap.parse_args()

    items = load()
    if args.cmd == "add":
        same = [i for i in items if i["status"] == "open" and i["title"].strip().lower() == args.title.strip().lower()]
        if same:
            print(f"EXISTS {same[0]['id']} (already open)")
            return
        n = max([int(i["id"].split("-")[1]) for i in items] or [0]) + 1
        item = {"id": f"S-{n:03d}", "kind": args.kind, "title": args.title.strip(), "detail": args.detail.strip(),
                "ref": args.ref, "source": args.source, "status": "open", "opened_at": now()}
        items.append(item)
        save(items)
        print(f"ADDED {item['id']}")
    elif args.cmd == "close":
        for i in items:
            if i["id"] == args.id:
                if i["status"] == "closed":
                    sys.exit(f"{args.id} is already closed")
                i.update(status="closed", closed_at=now(), resolution=args.resolution.strip())
                save(items)
                print(f"CLOSED {args.id}")
                return
        sys.exit(f"no issue {args.id}")
    else:
        for i in items:
            if args.all or i["status"] == "open":
                print(f"{i['id']} [{i['status']}] ({i['kind']}) {i['title']}" + (f"  · {i['ref']}" if i["ref"] else ""))


if __name__ == "__main__":
    main()
