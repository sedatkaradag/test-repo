# Hand-made Reels (not part of the publishing pipeline)

Formats the owner posts by hand. Nothing here is read by the daily agent, the workflows or the
queue: these scripts only write a video to the folder you give them. Verse text and meanings always come
from `scripts/find.py` / `scripts/content.py` (never typed by hand); the questions, options and surah
names in the set files are ours.

| Format | Script | Length |
|---|---|---|
| **Qur'an Quiz (trivia)**: logo intro (drawn) -> 3 questions, 3 options, 5 s timer -> answer -> the verse that answers it, recited and lit word by word, answer word in light green in the Arabic and the meaning -> closing screen with the logo drawn again and the answers | `trivia/make_trivia.py` | ~55-65 s |
| **Guess the Surah**: 4 rounds (MEDIUM, EASY, MEDIUM, HARD): the verse is recited and lit -> 4 s think bar -> answer + meaning -> score screen. Top line: "Can you name all 4 Surahs?", "Wait for the hard one" from the first answer, the challenge again at the last round | `guess_surah/make_guess_surah.py` | ~75-95 s |
| **99 Names (tasbih)**: a ring of 99 beads, one name every 1.5 s (Arabic, transliteration, meaning, count, bar), Bismillah written into the ring at the start, Alhamdulillah at the end; bead click per name, bell at 33 and 66 | `tasbih/make_tasbih.py` | ~156 s |

## Making one

1. **Write a set file** (copy one from `trivia/sets/` or `guess_surah/sets/`).
   - trivia: `q`, `entry` (e.g. `quran:19:25`), `verses` (`["019025"]`), `options` (3), `answer` (0-based),
     `highlight` (the answer words exactly as they appear in the meaning, e.g. `["palm", "tree"]`),
     `ar_answer` (0-based word numbers of the answer in the Arabic; see below).
   - guess the surah: `level`, `entry`, `verses`, `options` (4 x `[english, arabic]`), `answer` (0-3).
   - Guess the Surah: the verse must not give the answer away. No word of the surah's name (or of the
     name people know it by: Al-Mulk is "Tabarak") in the verse, so not 67:1 or 87:1; and not the
     surah's famous opening (e.g. Ad-Duha starting "wa'd-duha"). A later verse of the same surah is fine.
   - Check the verse is not already in a quiz set below. Having been posted as a regular Reel does not matter.
2. **Get the recitation and word timings** (runs on GitHub, writes only the `drafts-audio` branch):
   ```
   gh api -X POST repos/sedatkaradag/test-repo/actions/workflows/audio-fetch.yml/dispatches -f ref=main \
     -f "inputs[reciter]=Alafasy_128kbps" -f "inputs[ayahs]=019025,020020,050038"
   # wait ~30 s, then
   git clone -q --depth 1 -b drafts-audio https://github.com/sedatkaradag/test-repo /tmp/aud
   ```
   Word timings (quran-align) exist for Alafasy, Sudais, Abdul Basit, Husary, Minshawi, Shuraym, Shatri,
   Hani Rifai, Tablawi; not for Dosari or Maher (those would light evenly, not with the voice).
   Check `align.json` has one entry per verse.
3. **Render** (from the repo root; about 3 min):
   ```
   python3 samples/trivia/make_trivia.py . /tmp/aud /tmp/out samples/trivia/sets/<set>.json
   python3 samples/guess_surah/make_guess_surah.py . /tmp/aud /tmp/out samples/guess_surah/sets/<set>.json
   ```
   Check frames (`t_*.jpg` / `g_*.jpg` are written next to the video) before sending.

Arabic word numbers for `ar_answer`:
```
python3 -c "import sys; sys.path.insert(0,'scripts'); import render as R; from content import get; print(list(enumerate(R._arabic_words(get('quran:50:38')['arabic_display']))))"
```

## 99 Names (tasbih)

`python3 samples/tasbih/make_tasbih.py . /tmp/out [seconds_per_name]` (default 1.5; about 8 min). No audio
fetch needed. The names come only from `tasbih/names_tirmidhi_3507.json`: the commonly recited list
(Tirmidhi 3507) as on sunnah.com, Arabic from the hadith text, transliterations and meanings from its
English translation (Darussalam), copied by script and checked character for character; name 1 is
"Allah". Do not edit the names, spellings or meanings by hand. The list itself is graded weak (the sahih
hadith is only that Allah has 99 names, Bukhari 2736), so captions call it "the 99 Names" and do not
attribute the list to the Prophet. Stills of every name are written to `<out>/frames/` for checking.

## Logo drawing

The drawing is computed by `make_trivia.py` from `assets/logo.png` (each stroke its own layer, then the
original image takes over at 1.72 s). Ready transparent frames (30 fps, 2.0 s) for other uses:
`logo_draw/frames_800/` (intro size) and `logo_draw/frames_478/` (closing size). For .mov files with alpha:
`python3 samples/logo_draw/export_logo.py . <out_dir>`.

## Used verses

- Guess the Surah, Sudais: 36:82, 112:1-2, 94:5-6, 29:2 | 3:8, 108:1-3, 93:6-8, 25:63
- Guess the Surah, Alafasy: 95:4-6, 1:5, 2:152, 33:56 | 67:2, 55:13, 87:16-17, 13:28 (Nov 8)
- Trivia, Alafasy: 37:142, 21:69, 97:3 (Nov 7) | 20:20, 19:25, 50:38 (Nov 8)

## Caption (the one that was posted)

```
3 questions from the Qur'an. 5 seconds each.

Lock in your answer before the timer runs out, then hear the verse that answers it.

Comment your score below (?/3) and send this to a friend to compare.

Verses: <Surah> <s:v> · <Surah> <s:v> · <Surah> <s:v>
Recitation: Mishary Rashid Alafasy

Follow @thehalalalgorithm for more.

#quran #quranquiz #islamicquiz #quranverses #islam #muslim #alafasy #learnquran
```
