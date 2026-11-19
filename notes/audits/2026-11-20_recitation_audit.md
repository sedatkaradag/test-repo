# Recitation audit, 20 Nov 2026 (after the 7:199 Reel)

Trigger: owner, 20 Nov 01:30: the 7:199 Reel (2026-11-19_reel-eu, posted 19 Nov 18:01 UTC) has strong echo and recites more than the verse on screen.

## Finding
- everyayah's `MaherAlMuaiqly128kbps/007199.mp3` (17.76 s) holds 7:199 (0-4.4 s) **and all of 7:200** (4.4-17.1 s).
  Speech-to-text (faster-whisper large-v3 on branch asr-work) heard: "خذ العفو ... عن الجاهلين" then
  "وإما ينزغنك من الشيطان نزغ فاستعذ بالله إنه سميع عليم".
- The pipeline adds no effect (scripts/reel_audio.py: concat + loudnorm only). The echo is in the recording itself:
  Muaiqly's 128 kbps set is a mosque recording; its pauses never get quiet (10th-percentile level about -15 dB
  under the peak; Alafasy -20, Abdul Basit -32, Husary -46). Sudais, Dussary and Ajmi sets are similar.

## Why it was not caught
- reel_audio.py trusts the per-verse file; it never checks what is recited. The duration (2.8x this reciter's
  usual seconds per word) passed silently.
- The independent review checks the Arabic/English text on the card and Reel, not the sound.
- The earlier case (3 Nov, Dussary 108:1 ending with the next verse's "fa") was fixed by hand with a config trim,
  but no automatic check was added.

## Audit of everything in the queue (88 videos, 127 verse files, Reels and Stories, 27 Oct - 21 Nov)
Every verse segment was transcribed and compared with the verse and the verses around it (recitation_check.py).
- Only 7:199 recites a different verse.
- Three files the long run skipped (17:23 Muaiqly, 57:22 Muaiqly, 49:12 Abdul Basit) were checked one by one: correct.
- Other flags were the reciter repeating a phrase of the same verse (e.g. Sudais 103:3, Dussary 10:57 queued for
  20 Nov 07:10 UTC) or speech-to-text noise on very short verses. No other wrong or extra verse.
