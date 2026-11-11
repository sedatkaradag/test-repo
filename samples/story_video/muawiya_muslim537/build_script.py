import json, re, sys, unicodedata
sys.path.insert(0, "/home/claude/test-repo/scripts")
from content import get
h = get("hadith:muslim:1199")
E, A = h["english"], h["arabic"]
end = E.index("or words to that effect.") + len("or words to that effect.")
ex = E[:end]
toks = []
for t in ex.split(" "):
    if t == "said:While": toks += ["said:", "While"]
    elif t: toks.append(t)
assert " ".join(toks).replace("said: While", "said:While") == ex
def spoken(i, t):
    if t in ("(ﷺ)", "(ﷺ),"): return "peace be upon him,"
    if t == "b.": return "ibn"
    if t == "Mu'awiya": return "Muawiya"
    if t == "al-Hakam": return "al Hakam"
    if t == "said:" and toks[i + 1] == "While": return "said."
    if t == "Greatness.": return "Greatness,"
    if t == "Qur'an": return "Quran"
    return t.replace("(", "").replace(")", "")
words = [{"d": t, "s": spoken(i, t)} for i, t in enumerate(toks)]
def find_seq(seq):
    ss = seq.split(" ")
    for i in range(len(toks)):
        if toks[i:i + len(ss)] == ss: return [i, i + len(ss) - 1]
    raise SystemExit("not found: " + seq)
# Arabic is cut out of the source text word by word (letters compared without vowel marks), never typed
AW = A.split(" ")
def skel(w): return "".join(ch for ch in unicodedata.normalize("NFD", w) if unicodedata.category(ch)[0] == "L")
def ar(target):
    tw = [skel(x) for x in target.split()]
    for i in range(len(AW)):
        if [skel(x) for x in AW[i:i + len(tw)]] == tw:
            out = " ".join(AW[i:i + len(tw)])
            assert out in A
            return out
    raise SystemExit("arabic not found: " + target)
cards = [
  {"id": "teacher", "range": find_seq("neither before him nor after him have I seen a leader who gave better instruction than he"),
   "arabic": ar("ما رأيت معلما قبله ولا بعده أحسن تعليما منه")},
  {"id": "three", "range": find_seq("he did not scold, beat or revile me"),
   "arabic_lines": [ar("ما كهرني"), ar("ولا ضربني"), ar("ولا شتمني")], "line_words": ["scold,", "beat", "revile"]},
  {"id": "words", "range": find_seq("Talking to persons is not fitting during the prayer, for it consists of glorifying Allah, declaring his Greatness. and recitation of the Qur'an"),
   "arabic": ar("إن هذه الصلاة لا يصلح فيها شىء من كلام الناس إنما هو التسبيح والتكبير وقراءة القرآن")},
]
yar = {"arabic": ar("يرحمك الله"), "range": find_seq("Allah have mercy on you!")}
S = {"ref": "Sahih Muslim 537", "hook": "He spoke in the middle of the prayer. What did the Prophet ﷺ do next?",
     "hook_spoken": "He spoke in the middle of the prayer. What did the Prophet, peace be upon him, do next?",
     "note": "Look at the three things he did not do.",
     "outro": "When you correct someone's mistake, how will they remember that moment?",
     "words": words, "cards": cards, "yar": yar}
json.dump(S, open("script.json", "w"), ensure_ascii=False, indent=0)
print(len(words)); print(" ".join(w["s"] for w in words))
for c in cards: print(c["id"], c["range"], c.get("arabic") or c["arabic_lines"])
print(yar)
