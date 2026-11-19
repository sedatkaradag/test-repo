"""Compare each recitation segment's speech-to-text with the verse it should be (and the verses around it)."""
import json, re, subprocess, sys, difflib
MAN = json.load(open("/tmp/aud/manifest.json"))
TR = {k: json.load(open(f"/tmp/aud/tr_{k}.json")) for k in range(4) if __import__("os").path.exists(f"/tmp/aud/tr_{k}.json")}
DIAC = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
def norm(s):
    s = DIAC.sub("", s)
    s = re.sub("[إأآٱا]", "ا", s); s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[^ء-ي ]", " ", s)
    return s.split()
cache = {}
def verse(s, v):
    k = (s, v)
    if k not in cache:
        r = subprocess.run(["python3", "/home/claude/test-repo/scripts/find.py", "get", f"quran:{s}:{v}"], capture_output=True, text=True)
        try: cache[k] = norm(json.loads(r.stdout)["arabic_display"])
        except Exception: cache[k] = []
    return cache[k]
def match(a, b):   # share of words of b found (in order) in a
    if not b: return 0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(t.size for t in sm.get_matching_blocks()) / len(b)
out = []
for m in MAN:
    if m["chunk"] not in TR: continue
    words = [w for s in TR[m["chunk"]]["segments"] for w in s["words"] if m["start"] - .3 <= (w["s"] + w["e"]) / 2 <= m["end"] + .3]
    heard = norm(" ".join(w["w"] for w in words))
    s, v = int(m["ayah"][:3]), int(m["ayah"][3:])
    exp, nxt, prv = verse(s, v), verse(s, v + 1), verse(s, v - 1) if v > 1 else []
    cov = match(heard, exp)
    # words heard that are not explained by the expected verse
    sm = difflib.SequenceMatcher(None, heard, exp, autojunk=False)
    used = sum(t.size for t in sm.get_matching_blocks())
    extra = len(heard) - used
    nx = match(heard, nxt[:6]) if nxt else 0      # does it run into the start of the next verse?
    pv = match(heard, prv[-6:]) if prv else 0
    flag = []
    if cov < .7: flag.append(f"only {cov:.0%} of the verse heard")
    if extra >= 3 and nx >= .5: flag.append(f"runs into the next verse ({nx:.0%} of its first words)")
    elif extra >= 4: flag.append(f"{extra} extra words")
    if extra >= 3 and pv >= .5: flag.append("previous verse heard")
    out.append({**m, "heard": " ".join(heard), "coverage": round(cov, 2), "extra": extra, "next": round(nx, 2), "flag": flag})
json.dump(out, open("/tmp/aud/result.json", "w"), ensure_ascii=False, indent=1)
for r in out:
    if r["flag"]: print(r["item"], r["key"], r["reciter"], r["ayah"], r["sec"], r["status"], r["posted"], "|", "; ".join(r["flag"]), "|", r["heard"][:160])
print(len(out), "segments checked,", sum(1 for r in out if r["flag"]), "flagged")
