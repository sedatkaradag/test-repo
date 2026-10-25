"""Shared helpers: load the verified database, look up and search entries.

Text always comes from data/*.jsonl.gz. Nothing in the pipeline may write
hadith or verse text by hand; only these helpers return it.
"""
import gzip
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HISTORY = ROOT / "history" / "posted.jsonl"


@lru_cache(maxsize=None)
def _load(kind):
    with gzip.open(DATA / f"{kind}.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


@lru_cache(maxsize=None)
def _index():
    return {r["id"]: r for kind in ("hadith", "quran") for r in _load(kind)}


def get(entry_id):
    """Return one entry. Quran ranges like quran:94:5-6 are joined verse by verse."""
    m = re.fullmatch(r"quran:(\d+):(\d+)-(\d+)", entry_id)
    if m:
        s, a, b = map(int, m.groups())
        if b < a or b - a > 4:
            raise KeyError(f"bad range {entry_id}")
        verses = [_index()[f"quran:{s}:{v}"] for v in range(a, b + 1)]
        first = verses[0]
        return {
            **first,
            "id": entry_id,
            "verse": f"{a}-{b}",
            "arabic": " ".join(f"{v['arabic']} ﴿{_arabic_num(v['verse'])}﴾" for v in verses),
            "arabic_display": " ".join(v["arabic_display"] for v in verses),
            "english": _join_verses([v["english"] for v in verses]),
            "length": sum(v["length"] for v in verses),
            "reference": f"Surah {first['surah_name']} {s}:{a}-{b}",
        }
    return _index()[entry_id]


def _join_verses(parts):
    """Join consecutive verses, adding only punctuation between them."""
    out = parts[0].rstrip()
    for nxt in parts[1:]:
        nxt = nxt.strip()
        if out and out[-1].isalnum():
            out += ";" if nxt[:1].islower() else "."
        out += " " + nxt
    return out


def _arabic_num(n):
    return str(n).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def used_ids(days=None):
    """IDs already posted (optionally only within the last `days`)."""
    if not HISTORY.exists():
        return set()
    import datetime as dt
    cutoff = None
    if days:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    ids = set()
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if cutoff and dt.datetime.fromisoformat(row["posted_at"]) < cutoff:
            continue
        for i in row.get("entry_ids") or [row["entry_id"]]:
            ids.add(i)
    return ids


def search(kind, query, max_len=None, min_len=25, collections=None, limit=25, exclude=()):
    """Keyword search. `query` is a regex matched case-insensitively against
    the English text (and chapter/book name)."""
    pat = re.compile(query, re.I)
    out = []
    for r in _load(kind):
        if r["id"] in exclude:
            continue
        if max_len and r["length"] > max_len:
            continue
        if r["length"] < min_len:
            continue
        if collections and r.get("collection") not in collections:
            continue
        if any(isinstance(v, str) and "\ufffd" in v for v in r.values()):
            continue   # broken character in the source (see integrity.py); never offered
        hay = r["english"] + " " + r.get("book", "") + " " + r.get("surah_english", "")
        if pat.search(hay):
            out.append(r)
    # Prefer the most authoritative and the shortest (they read best on an image).
    # Prefer the two Sahih collections, then lengths that read well on one image.
    rank = {"bukhari": 0, "muslim": 0}
    out.sort(key=lambda r: (rank.get(r.get("collection"), 1), abs(r["length"] - 200)))
    return out[:limit]


def display_text(text):
    """Typographic cleanup only — never changes words."""
    t = re.sub(r"([:,;])(?=[\"“‘'A-Za-z(])", r"\1 ", text)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" ,", ",")
    # Close an unbalanced quote left open by the source.
    if t.count('"') % 2 == 1:
        t += '"'
    if t.count("“") > t.count("”"):
        t += "”"
    # End with a full stop if the source stops mid-air.
    if t and t[-1].isalnum():
        t += "."
    elif len(t) > 1 and t[-1] in "\"”" and t[-2].isalnum():
        t = t[:-1] + "." + t[-1]
    return smart_quotes(t)


def smart_quotes(t):
    out, open_, single_open = [], True, False
    for i, ch in enumerate(t):
        if ch == '"':
            out.append("“" if open_ else "”")
            open_ = not open_
        elif ch == "`":
            out.append("‘")  # transliteration mark for ʿayn (`Aisha), not a quote
        elif ch == "'":
            prev = t[i - 1] if i else " "
            nxt = t[i + 1] if i + 1 < len(t) else " "
            if prev.isalnum() or prev in ".,!?":
                out.append("’")
                if not nxt.isalnum():
                    single_open = False  # a closing quote, not an apostrophe
            else:
                out.append("‘")
                # Only a quote after "said, " / ": " opens a quotation; a mark before
                # a name ('Umar, 'Abdullah) is a transliterated ʿayn.
                if i >= 2 and t[i - 2] in ",:;":
                    single_open = True
        else:
            out.append(ch)
    if single_open and len(out) > 2:
        # The source left a single quotation open. It is nested inside the double one,
        # so it closes first: …running.’” and not …running.”’
        if out[-1] == "”":
            out.insert(len(out) - 1, "’")
        else:
            out.append("’")
    return "".join(out)


def split_narrator(text):
    """'Narrated Abu Huraira: ...' -> ('Narrated Abu Huraira', '...'). Layout only."""
    m = re.match(r"^(Narrated [^:]{2,70}):\s*(.+)$", text)
    if not m:
        return None, text
    narrator, body = m.group(1), m.group(2)
    # "(the wife of the Prophet) Allah's Messenger said..." -> the aside belongs to the narrator.
    p = re.match(r"^(\([^)]{2,60}\))\s*(.+)$", body)
    if p:
        narrator, body = f"{narrator} {p.group(1)}", p.group(2)
    return narrator, body
