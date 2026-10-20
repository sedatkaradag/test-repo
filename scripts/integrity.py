"""Integrity checks that must pass before anything is queued.

    python scripts/integrity.py <entry_id> [<entry_id> ...]   # prints a report, exit 1 on hard issues

Hard issues (the entry may not be posted):
  - Qur'an Arabic not verified letter-for-letter against the King Fahd Complex text
  - English words that are not real words in the Qur'an translation (typos in the source)
  - broken words ("say- ing"), stray spacing or empty brackets in the English
  - after rendering: a word split across lines, a line starting with a loose mark,
    a glyph missing from the font, a line wider than the text box, or the drawn
    text differing from the source text
Flags (the verifier must look at each one): unusual lowercase words in hadith
English (transliterations are common there, so a person-level judgement is needed).
"""
import json
import re
import sys
import tempfile
import unicodedata
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from spellchecker import SpellChecker

import render as R
from content import ROOT, display_text, get, smart_quotes, split_narrator

# Real words of the Rowwad translation that a general dictionary does not know.
QURAN_ALLOW = {
    "zakah", "ayb", "lih", "warners", "prophethood", "ghoot", "dreamt", "miri", "fisted",
    "lote", "misleaders", "withholder", "illiyy", "circumambulation", "ibah", "lah", "zar",
    "untrellised", "attaches", "istawa", "qiblah", "ignorants", "moulded", "lik", "thornless",
    "zaqq", "similitudes",
}


@lru_cache(maxsize=None)
def _speller():
    return SpellChecker()


def _words(text):
    return re.findall(r"[A-Za-z][A-Za-z'’\-]*[A-Za-z]|[A-Za-z]", text)


CONTRACTION = re.compile(r"(?i)(n[’']t|[’'](s|re|ve|ll|d|m))$")


def unknown_lowercase(text):
    """Lowercase words a dictionary does not know. Names (capitalised parts, as in
    'al-Bukhari') and contractions ('doesn't') are not counted."""
    sp, out = _speller(), []
    for w in _words(text):
        w = CONTRACTION.sub("", w)
        for part in re.split(r"[-’']", w):
            if not part or part[0].isupper():
                continue
            part = part.lower()
            if len(part) > 2 and part not in sp:
                out.append(part)
    return sorted(set(out))


def text_issues(entry):
    hard, flags = [], []
    en = entry["english"]
    if re.search(r"[a-z]- [a-z]", en):
        hard.append("broken word in English (e.g. 'say- ing')")
    if re.search(r"\(\s*\)|\[\s*\]", en):
        hard.append("empty brackets in English")
    if re.search(r"\s[,.;:!?]", en):
        hard.append("space before punctuation in English")
    unknown = unknown_lowercase(en)
    if entry["type"] == "quran":
        bad = [w for w in unknown if w not in QURAN_ALLOW]
        if bad:
            hard.append(f"possible typo in the translation: {', '.join(bad)}")
        if not entry.get("arabic_verified"):
            hard.append("Arabic not verified against the Madinah Mushaf text")
        if not entry.get("arabic_display_source"):
            hard.append("no checked King Fahd Complex display text for this verse")
    elif unknown:
        flags.append(f"check these words are correct transliterations, not typos: {', '.join(unknown)}")
    return hard, flags


@lru_cache(maxsize=None)
def _hb_font(path):
    blob = hb.Blob.from_file_path(str(path))
    return hb.Font(hb.Face(blob))


def _missing_glyphs(text, path, rtl=False):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    if rtl:
        buf.direction = "rtl"
    hb.shape(_hb_font(path), buf)
    return sum(1 for i in buf.glyph_infos if i.codepoint == 0)


def _english_missing(line, size):
    n = 0
    for t, f in R._runs(line, size):
        path = R.F_BODY if f.path == str(R.F_BODY) else R.F_ARABIC
        n += _missing_glyphs(t, path)
    return n


def render_issues(entry_id):
    """Render to a temp file and check exactly what was drawn."""
    issues = []
    with tempfile.TemporaryDirectory() as tmp:
        try:
            R.render(entry_id, Path(tmp) / "x.jpg")
        except R.TooLong:
            return ["text does not fit on one card"]
    L = R.LAST_LAYOUT
    e = get(entry_id)
    if e["type"] == "quran":
        expected = R._arabic_words(e["arabic_display"])
        drawn = [w for line in L["arabic_lines"] for w in line.split(" ") if w]
        if " ".join(drawn) != " ".join(expected):
            issues.append("drawn Arabic differs from the source text")
        f = R._font(R.F_QURAN, L["arabic_size"])
        for n, line in enumerate(L["arabic_lines"], 1):
            first = line[:1]
            if first and (unicodedata.category(first).startswith("M") or first == "⁠"):
                issues.append(f"Arabic line {n} starts with a loose mark (a word was split)")
            if _missing_glyphs(line, R.F_QURAN, rtl=True):
                issues.append(f"Arabic line {n} has a character the font cannot draw")
            if f.getlength(line, direction="rtl", language="ar") > L["max_w"] + 1:
                issues.append(f"Arabic line {n} is wider than the text box")
            if line.split(" ")[0].startswith("﴿"):
                issues.append(f"Arabic line {n} starts with a verse number")
        # Pause marks sit high above the letters; they must stay clearly inside
        # their own line, never reach into (or near) the line above.
        if re.search(r"[\u06de\u06e9]", " ".join(L["arabic_lines"])):
            issues.append("a rub el hizb or sajdah sign was drawn (cards leave them out)")
        if "\u06dc" in e["arabic"]:
            issues.append("contains the small high seen (saktah / seen reading); choose another entry")
        boxes = L.get("arabic_boxes") or []
        min_gap = 0.2 * L["arabic_size"]
        for n in range(1, len(boxes)):
            gap = boxes[n][1] - boxes[n - 1][3]
            if gap < min_gap:
                issues.append(f"Arabic line {n + 1} comes too close to line {n} "
                              f"({gap:.0f}px gap; marks may read as the wrong word's)")
    english = L["english_text"]
    if " ".join(L["english_lines"]) != english:
        issues.append("drawn English differs from the source text")
    for n, line in enumerate(L["english_lines"], 1):
        if _english_missing(line, L["english_size"]):
            issues.append(f"English line {n} has a character the font cannot draw")
        if R._width_ltr(line, L["english_size"]) > L["max_w"] + 1:
            issues.append(f"English line {n} is wider than the text box")
    # Only typography may change between source and card: same letters and digits.
    src = e["english"]
    if e["type"] == "hadith":
        nar, body = split_narrator(src)
        src = body
        if nar and L["narrator"] and re.sub(r"\W", "", nar) != re.sub(r"\W", "", L["narrator"]).replace("’", "").replace("‘", ""):
            pass
    if re.sub(r"[^A-Za-z0-9]", "", src) != re.sub(r"[^A-Za-z0-9]", "", english):
        issues.append("letters on the card differ from the source text")
    return issues


def check(entry_id):
    e = get(entry_id)
    hard, flags = text_issues(e)
    hard += render_issues(entry_id)
    return hard, flags


def main():
    bad = False
    for i in sys.argv[1:]:
        hard, flags = check(i)
        print(json.dumps({"id": i, "ok": not hard, "hard": hard, "flags": flags}, ensure_ascii=False))
        bad = bad or bool(hard)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
