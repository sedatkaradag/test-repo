"""Branch tts-work only: one sample line in every English Kokoro voice -> out/<voice>.wav (voice comparison page)."""
import os, json, numpy as np, soundfile as sf
from kokoro import KPipeline
TEXT = ("Leave a person lying still for days, and their own weight starts to cut off the blood flow. "
        "Today, nurses turn such patients every few hours. Now look at what the Quran describes in Surah Al-Kahf.")
VOICES = ["af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore", "af_nicole", "af_nova", "af_river",
          "af_sarah", "af_sky", "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx",
          "am_puck", "am_santa", "bf_alice", "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable",
          "bm_george", "bm_lewis"]
os.makedirs("out", exist_ok=True)
pipes = {"a": KPipeline(lang_code="a"), "b": KPipeline(lang_code="b")}
done = {}
for v in VOICES:
    try:
        audio = [np.asarray(r.audio) for r in pipes[v[0]](TEXT, voice=v, speed=0.95, split_pattern=None)]
        a = np.concatenate(audio); sf.write(f"out/{v}.wav", a, 24000); done[v] = round(len(a) / 24000, 2)
        print(v, done[v], "s")
    except Exception as e:
        print(v, "FAILED", e)
json.dump({"text": TEXT, "speed": 0.95, "voices": done}, open("out/voices.json", "w"), indent=1)
