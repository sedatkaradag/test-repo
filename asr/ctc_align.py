"""Forced alignment of a known Arabic text to its recitation (CTC, wav2vec2 Arabic model): one [start, end] per word.
python asr/ctc_align.py <audio> <words.json> <out.json>     (words.json: the words exactly as displayed)
"""
import json, re, sys
import numpy as np, soundfile as sf, torch, torchaudio
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
M = "jonatasgrosman/wav2vec2-large-xlsr-53-arabic"
audio, wj, out = sys.argv[1:4]
words = json.load(open(wj))
proc = Wav2Vec2Processor.from_pretrained(M); model = Wav2Vec2ForCTC.from_pretrained(M).eval()
x, sr = sf.read(audio, dtype='float32'); x = x.mean(1) if x.ndim > 1 else x
wav = torchaudio.functional.resample(torch.from_numpy(np.ascontiguousarray(x))[None], sr, 16000)[0]
with torch.inference_mode():
    em = torch.log_softmax(model(proc(wav.numpy(), sampling_rate=16000, return_tensors="pt").input_values).logits, -1)
vocab = proc.tokenizer.get_vocab(); blank = proc.tokenizer.pad_token_id; sep = vocab.get("|")
def norm(w):
    w = w.replace("ٰ", "ا").replace("ٱ", "ا")                       # dagger alif is a spoken long a
    w = re.sub(r"[ؐ-ًؚ-ٟۖ-ۭـ]", "", w)
    return [vocab[c] for c in w if c in vocab]
toks, owner = [], []
for i, w in enumerate(words):
    t = norm(w)
    if not t: raise SystemExit(f"no tokens for {w!r}")
    if toks and sep is not None: toks.append(sep); owner.append(-1)
    toks += t; owner += [i] * len(t)
ali, sc = torchaudio.functional.forced_align(em, torch.tensor([toks], dtype=torch.int32), blank=blank)
spans = torchaudio.functional.merge_tokens(ali[0], sc[0])
fr = len(wav) / 16000 / em.shape[1]
res = [[None, None] for _ in words]
for sp, o in zip(spans, owner):
    if o < 0: continue
    s, e = sp.start * fr, sp.end * fr
    res[o][0] = s if res[o][0] is None else min(res[o][0], s); res[o][1] = e if res[o][1] is None else max(res[o][1], e)
json.dump({"words": words, "times": [[round(a, 3), round(b, 3)] for a, b in res], "vocab_size": len(vocab), "sep": sep}, open(out, "w"), ensure_ascii=False)
print(json.dumps(res))
