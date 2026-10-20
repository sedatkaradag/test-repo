"""Add the King Fahd Complex (KFGQPC) Uthmani Hafs text to data/quran.jsonl.gz as
`arabic_display`, the text the cards draw with the Complex's own font.

    python3 -I scripts/add_mushaf_display.py <hafsData_v18.json>

hafsData_v18.json is the Complex's developer data (Uthmanic Hafs Ver18) that
matches KFGQPC-UthmanicHafs-v18.ttf. Every verse is compared letter by letter
with the stored `arabic` (itself checked against the Complex's text at build);
a single mismatch stops the script and nothing is written.
"""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_data import skeleton  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "quran.jsonl.gz"


def main(src):
    kf = json.loads(Path(src).read_text(encoding="utf-8-sig"))
    by = {(r["sora"], r["aya_no"]): r["aya_text"].strip() for r in kf}
    with gzip.open(DB, "rt", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f]
    bad = []
    for r in rows:
        t = by[(r["surah"], r["verse"])]
        if skeleton(t) != skeleton(r["arabic"]):
            bad.append(r["id"])
        r["arabic_display"] = t
        r["arabic_display_source"] = "KFGQPC Uthmanic Hafs data v18 (letters checked)"
    if bad or len(by) != len(rows):
        sys.exit(f"MISMATCH in {len(bad)} verses, e.g. {bad[:10]}; nothing written")
    with gzip.open(DB, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"ok: {len(rows)} verses, all letters match")


if __name__ == "__main__":
    main(sys.argv[1])
