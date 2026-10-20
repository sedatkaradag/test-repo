"""Build the verified content database from the open fawazahmed0 datasets.

Usage:
    python scripts/build_data.py <hadith_dir> <quran_dir>

<hadith_dir> holds eng-<collection>.json and ara-<collection>.json files from
https://github.com/fawazahmed0/hadith-api (editions/*.min.json).
<quran_dir> holds ara-qurankhaledhosn.json, eng-rowwadtranslati.json and
info.json from https://github.com/fawazahmed0/quran-api.

Output (committed to the repo, read-only at runtime):
    data/hadith.jsonl.gz   only hadith graded sahih or hasan
    data/quran.jsonl.gz    every verse, Arabic + English
"""
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Kutub al-Sittah (the six canonical collections) only.
COLLECTIONS = {
    # key: (display name, always-sahih?)
    "bukhari": ("Sahih al-Bukhari", True),
    "muslim": ("Sahih Muslim", True),
    "abudawud": ("Sunan Abi Dawud", False),
    "tirmidhi": ("Jami` at-Tirmidhi", False),
    "nasai": ("Sunan an-Nasa'i", False),
    "ibnmajah": ("Sunan Ibn Majah", False),
}

# Grader priority: the first one present decides; any "fabricated" verdict excludes.
GRADER_PRIORITY = [
    "Al-Albani",
    "Zubair Ali Zai",
    "Salim al-Hilali",
    "Shuaib Al Arnaut",
    "Ahmad Muhammad Shakir",
    "Bashar Awad Maarouf",
]
WEAK = re.compile(r"da.?if|daeef|weak|munkar|shadh|maudu|mawdu|fabricat|batil|no basis|munqati", re.I)
FABRICATED = re.compile(r"maudu|mawdu|fabricat|batil|no basis", re.I)
GOOD = re.compile(r"sahih|hasan", re.I)


def classify(collection, grades):
    """Return 'sahih', 'hasan' or None (rejected)."""
    if COLLECTIONS[collection][1]:
        return "sahih"
    if not grades:
        return None
    by_name = {g["name"]: g["grade"] for g in grades}
    if any(FABRICATED.search(g) for g in by_name.values()):
        return None
    primary = next((by_name[n] for n in GRADER_PRIORITY if n in by_name), None)
    if primary is None or WEAK.search(primary) or not GOOD.search(primary):
        return None
    # Both major modern graders must agree when both are present.
    for n in ("Al-Albani", "Zubair Ali Zai"):
        g = by_name.get(n)
        if g and (WEAK.search(g) or not GOOD.search(g)):
            return None
    return "sahih" if re.search(r"sahih", primary, re.I) else "hasan"


def clean(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def build_hadith(src):
    out = []
    for key, (name, _) in COLLECTIONS.items():
        eng = json.loads((src / f"eng-{key}.json").read_text(encoding="utf-8"))
        ara = json.loads((src / f"ara-{key}.json").read_text(encoding="utf-8"))
        ara_by_num = {h["hadithnumber"]: clean(h["text"]) for h in ara["hadiths"]}
        sections = eng["metadata"].get("sections", {})
        kept = 0
        for h in eng["hadiths"]:
            text = clean(h["text"])
            if len(text) < 25:
                continue
            status = classify(key, h.get("grades", []))
            if not status:
                continue
            num = h["hadithnumber"]
            num_str = str(int(num)) if float(num).is_integer() else str(num)
            book = h.get("reference", {}).get("book")
            out.append({
                "id": f"hadith:{key}:{num_str}",
                "type": "hadith",
                "collection": key,
                "collection_name": name,
                "number": num_str,
                "book": sections.get(str(book), ""),
                "status": status,
                "grades": h.get("grades", []),
                "english": text,
                "arabic": ara_by_num.get(num, ""),
                "length": len(text),
                "reference": f"{name} {num_str}",
            })
            kept += 1
        print(f"{key}: kept {kept} of {len(eng['hadiths'])}")
    return out


def build_quran(src):
    ara = json.loads((src / "ara-qurankhaledhosn.json").read_text(encoding="utf-8"))["quran"]
    eng = json.loads((src / "eng-rowwadtranslati.json").read_text(encoding="utf-8"))["quran"]
    info = json.loads((src / "info.json").read_text(encoding="utf-8"))
    names = {c["chapter"]: c for c in info["chapters"]}
    eng_by = {(v["chapter"], v["verse"]): clean(v["text"]) for v in eng}
    out = []
    for v in ara:
        c, n = v["chapter"], v["verse"]
        ch = names[c]
        en = eng_by[(c, n)]
        out.append({
            "id": f"quran:{c}:{n}",
            "type": "quran",
            "surah": c,
            "verse": n,
            "surah_name": ch["name"],
            "surah_english": ch["englishname"],
            "arabic": clean(v["text"]),
            "english": en,
            "length": len(en),
            "reference": f"Surah {ch['name']} {c}:{n}",
        })
    print(f"quran: {len(out)} verses")
    return out


def write(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    hadith_dir, quran_dir = Path(sys.argv[1]), Path(sys.argv[2])
    write(ROOT / "data" / "hadith.jsonl.gz", build_hadith(hadith_dir))
    write(ROOT / "data" / "quran.jsonl.gz", build_quran(quran_dir))
