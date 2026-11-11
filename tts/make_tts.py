"""Branch tts-work only: English narration with Kokoro-82M (Apache-2.0), with word timings.
Input tts/script.json {hook, outro, words:[{d: shown word, s: spoken form}]}; output out/<part>.wav + out/<part>.json."""
import json, re, sys, numpy as np, soundfile as sf
from kokoro import KPipeline
VOICE, SPEED, SR = sys.argv[1], float(sys.argv[2]), 24000
S = json.load(open("tts/script.json"))
pipe = KPipeline(lang_code="b" if VOICE.startswith("b") else "a")
def lines_of_body():
    spoken = [w["s"] for w in S["words"] if w["s"]]
    text, out, cur = " ".join(spoken), [], ""
    # one line per sentence (the pipeline splits on newlines; a short pause goes between lines)
    for part in re.split(r'(?<=[.?!]"?)\s+', text):
        out.append(part)
    return out
def render(name, lines, gap=0.28):
    audio, toks, t0 = [], [], 0.0
    for line in lines:
        for r in pipe(line, voice=VOICE, speed=SPEED, split_pattern=None):
            a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
            for tk in (r.tokens or []):
                toks.append({"text": tk.text, "ws": tk.whitespace, "start": None if tk.start_ts is None else round(t0 + tk.start_ts, 3),
                             "end": None if tk.end_ts is None else round(t0 + tk.end_ts, 3)})
            audio.append(a); t0 += len(a) / SR
        toks.append({"text": "<line>", "start": round(t0, 3), "end": round(t0, 3)})
        audio.append(np.zeros(int(gap * SR), dtype=np.float32)); t0 += gap
    sf.write(f"out/{name}.wav", np.concatenate(audio), SR)
    json.dump({"lines": lines, "tokens": toks, "duration": round(t0, 3)}, open(f"out/{name}.json", "w"), indent=0)
    print(name, round(t0, 2), "s", len(toks), "tokens")
import os; os.makedirs("out", exist_ok=True)
render("hook", [S["hook"]]); render("body", lines_of_body()); render("outro", [S["outro"]])
