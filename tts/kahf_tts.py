"""Branch tts-work only: each line of tts/kahf_lines.json -> out/<id>.wav + out/<id>.json (word times)."""
import json, os, sys, numpy as np, soundfile as sf
from kokoro import KPipeline
VOICE, SPEED, SR = sys.argv[1], float(sys.argv[2]), 24000
pipe = KPipeline(lang_code="b" if VOICE.startswith("b") else "a")
os.makedirs("out", exist_ok=True)
for L in json.load(open("tts/kahf_lines.json")):
    audio, toks, t0 = [], [], 0.0
    for r in pipe(L["text"], voice=VOICE, speed=SPEED, split_pattern=None):
        a = np.asarray(r.audio)
        for tk in (r.tokens or []):
            toks.append({"text": tk.text, "ws": tk.whitespace,
                         "start": None if tk.start_ts is None else round(t0 + tk.start_ts, 3),
                         "end": None if tk.end_ts is None else round(t0 + tk.end_ts, 3)})
        audio.append(a); t0 += len(a) / SR
    sf.write(f"out/{L['id']}.wav", np.concatenate(audio), SR)
    json.dump({"text": L["text"], "tokens": toks, "duration": round(t0, 3)}, open(f"out/{L['id']}.json", "w"), indent=0)
    print(L["id"], round(t0, 2))
