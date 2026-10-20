"""Search or fetch verified content.

Examples:
    python scripts/find.py search hadith "patien|sabr" --max-len 300
    python scripts/find.py search quran "mercy" --max-len 250
    python scripts/find.py get hadith:bukhari:6018
    python scripts/find.py get quran:94:5-6
"""
import argparse
import json

from content import get, search, used_ids


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("kind", choices=["hadith", "quran"])
    s.add_argument("query", help="regex, case-insensitive")
    s.add_argument("--max-len", type=int, default=320)
    s.add_argument("--collections", nargs="*")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--repeat-days", type=int, default=365,
                   help="exclude anything posted within this many days")
    g = sub.add_parser("get")
    g.add_argument("id")
    a = p.parse_args()

    if a.cmd == "get":
        print(json.dumps(get(a.id), ensure_ascii=False, indent=2))
        return
    rows = search(a.kind, a.query, max_len=a.max_len, collections=a.collections,
                  limit=a.limit, exclude=used_ids(a.repeat_days))
    for r in rows:
        extra = r.get("book") or r.get("surah_english", "")
        print(json.dumps({"id": r["id"], "len": r["length"], "status": r.get("status", "quran"),
                          "topic": extra, "english": r["english"]}, ensure_ascii=False))
    print(f"# {len(rows)} result(s)")


if __name__ == "__main__":
    main()
