"""Arabic speech to text with word times (faster-whisper large-v3, CPU). Used on branch asr-work.
python asr/transcribe.py <audio> <out.json> [language]"""
import json, sys
from faster_whisper import WhisperModel

audio, out = sys.argv[1], sys.argv[2]
lang = sys.argv[3] if len(sys.argv) > 3 else "ar"
model = WhisperModel("large-v3", device="cpu", compute_type="int8")
segs, info = model.transcribe(audio, language=lang, word_timestamps=True, vad_filter=False,
                              beam_size=5, condition_on_previous_text=False)
data = {"language": info.language, "duration": info.duration, "segments": []}
for s in segs:
    data["segments"].append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                             "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2),
                                        "p": round(w.probability, 3)} for w in (s.words or [])]})
    print(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text.strip()}", flush=True)
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
