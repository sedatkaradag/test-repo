"""Not part of the publishing pipeline: "Guess the Surah" quiz Reel, 4 questions, our own look.

    python3 make_guess_surah.py <repo> <audio_dir> <out_dir> <rounds.json>

<audio_dir> is the drafts-audio checkout made by the audio-fetch helper: audio/SSSAAA.mp3 and
align.json (measured word timings, cpfair/quran-align, CC BY 4.0).
Each round: the verse is recited and lights up word by word; a 4 s "think" bar; the answer is
revealed with the verse's meaning. At the end: score + comment + share call.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO, AUD, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(REPO / "scripts"))
import reels as RL  # noqa: E402
import render as R  # noqa: E402
from content import display_text, get  # noqa: E402

SW, SH, FPS = RL.SW, RL.SH, RL.FPS
OUT.mkdir(parents=True, exist_ok=True)
SR = 44100
GREEN = (118, 196, 146)
LEVEL = {"EASY": (118, 196, 146), "MEDIUM": (214, 178, 104), "HARD": (222, 128, 96)}
THINK, REVEAL, GAP, XFADE, FINAL = 4.0, 3.0, 0.35, 0.35, 4.0

# the questions come from a JSON file (4th argument), 4 rounds: level (EASY/MEDIUM/HARD), entry, verses,
# options ([english, arabic] x4), answer (0-3)
ROUNDS = json.loads(Path(sys.argv[4]).read_text())
for _rk in ROUNDS:
    _rk["options"] = [tuple(o) for o in _rk["options"]]
ALIGN = json.loads((AUD / "align.json").read_text())
CHALLENGE = f"Can you name all {len(ROUNDS)} Surahs?"

# layout (y)
Y_CHAL, Y_DOTS, Y_PILL = 300, 400, 432
V_TOP, V_H = 520, 380            # verse block
Y_MID = 915                      # think text / meaning block (to 1060)
GRID = [(115, 1080), (555, 1080), (115, 1300), (555, 1300)]
CW, CH = 410, 200
Y_HANDLE = 1535


def font(path, size):
    return R._font(path, size)


def text_center(d, text, cx, y, f, color):
    d.text((cx - f.getlength(text) / 2, y), text, font=f, fill=color)


def pcm_of(ayah):
    tmp = OUT / "seg.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(AUD / "audio" / f"{ayah}.mp3"),
                    "-ac", "2", "-ar", str(SR), str(tmp)], check=True)
    with wave.open(str(tmp)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32)


def word_starts(ayah, n_words):
    """Measured start of each word (quran-align segments: [first, after_last, start_ms, end_ms])."""
    starts = [None] * n_words
    for a, b, s, e in ALIGN[ayah]:
        for k in range(a, b):                  # a segment of several words: spread them evenly
            starts[k] = (s + (e - s) * (k - a) / (b - a)) / 1000
    for k in range(n_words):                   # a word the aligner could not place: just after the one before
        if starts[k] is None:
            starts[k] = (starts[k - 1] + 0.3) if k else 0.0
    return starts


def card(d, j, en, ar, state="normal"):
    x, y = GRID[j]
    if state == "normal":
        d.rounded_rectangle([x, y, x + CW, y + CH], radius=24, fill=(255, 255, 255, 16), outline=RL.GOLD + (110,), width=2)
        num, arc, enc = RL.GOLD, RL.VERSE_ON, RL.IVORY
    else:
        d.rounded_rectangle([x, y, x + CW, y + CH], radius=24, fill=GREEN + (52,), outline=GREEN + (255,), width=4)
        num, arc, enc = GREEN, (236, 246, 238), (236, 246, 238)
        cx, cy = x + CW - 44, y + 40
        d.line([(cx - 14, cy), (cx - 4, cy + 11), (cx + 15, cy - 12)], fill=GREEN + (255,), width=5, joint="curve")
    d.text((x + 24, y + 16), "ABCD"[j], font=font(R.F_LABEL, 34), fill=num + (255,))
    fa = font(R.F_ARABIC, 66)
    w = fa.getlength(ar, direction="rtl", language="ar")
    d.text((x + (CW - w) / 2, y + 24), ar, font=fa, fill=arc + (255,), direction="rtl", language="ar")
    text_center(d, en, x + CW / 2, y + 134, font(R.F_LABEL, 36), enc + (255,))


def header(img, d, k, level):
    RL.draw_label(img, "GUESS THE SURAH", RL.TOP_LABEL, RL.GOLD)
    for i in range(len(ROUNDS)):
        cx, cy = SW / 2 + (i - (len(ROUNDS) - 1) / 2) * 48, Y_DOTS
        col = GREEN if i < k else (RL.GOLD if i == k else (90, 96, 84))
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=col + (255,))
    if level:
        f = font(R.F_LABEL, 34)
        tw = f.getlength(" ".join(level)) + 70
        d.rounded_rectangle([(SW - tw) / 2, Y_PILL, (SW + tw) / 2, Y_PILL + 58], radius=29,
                            outline=LEVEL[level] + (255,), width=3)
        text_center(d, " ".join(level), SW / 2, Y_PILL + 10, f, LEVEL[level] + (255,))


def static_layer(rk, k):
    img = RL.layer()
    d = ImageDraw.Draw(img)
    header(img, d, k, rk["level"])
    for j, (en, ar) in enumerate(rk["options"]):
        card(d, j, en, ar)
    text_center(d, R.HANDLE, SW / 2, Y_HANDLE, font(R.F_LABEL, 28), RL.MUTED + (255,))
    return img


def think_layer():
    img = RL.layer()
    d = ImageDraw.Draw(img)
    text_center(d, "PAUSE IF YOU NEED MORE TIME", SW / 2, Y_MID + 45, font(R.F_LABEL, 30), RL.MUTED + (255,))
    d.rounded_rectangle([140, Y_MID + 95, SW - 140, Y_MID + 103], radius=4, fill=(255, 255, 255, 34))
    return img


def meaning_layer(rk):
    img = RL.layer()
    txt = RL.verse_meanings(rk["entry"])[1]   # the card text (dangling quotes handled as on the card)
    for size in (40, 38, 36, 34, 32):
        lines = RL.en_lines(txt, size, 900)
        if len(lines) * RL.en_lh(size) <= 140:
            break
    RL.draw_en(img, lines, size, Y_MID + (145 - len(lines) * RL.en_lh(size)) / 2, RL.MEAL)
    return img


def reveal_layers(rk):
    dim, right = RL.layer(), RL.layer()
    d1, d2 = ImageDraw.Draw(dim), ImageDraw.Draw(right)
    for j in range(4):
        x, y = GRID[j]
        if j != rk["answer"]:
            d1.rounded_rectangle([x - 2, y - 2, x + CW + 2, y + CH + 2], radius=26, fill=tuple(RL.BG) + (175,))
    x, y = GRID[rk["answer"]]
    d2.rounded_rectangle([x - 2, y - 2, x + CW + 2, y + CH + 2], radius=26, fill=tuple(RL.BG) + (255,))
    en, ar = rk["options"][rk["answer"]]
    card(d2, rk["answer"], en, ar, "right")
    return dim, right


def verse_layers(rk):
    words = []
    for a in rk["verses"]:
        words += R._arabic_words(get(f"quran:{int(a[:3])}:{int(a[3:])}")["arabic_display"])
    size = 84
    while True:
        lines = R._wrap(words, 900, lambda s: font(R.F_QURAN, size).getlength(s, direction="rtl", language="ar"))
        if (len(lines) * RL.ar_lh(size) <= V_H and len(lines) <= 3) or size <= 56:
            break
        size -= 2
    f = font(R.F_QURAN, size)
    lh = RL.ar_lh(size)
    y = V_TOP + (V_H - len(lines) * lh) / 2
    dim = RL.layer()
    RL.draw_ar(dim, lines, size, y, RL.VERSE_DIM)
    per_word = []
    for n, line in enumerate(lines):
        # each line drawn on its own, so a mark hanging below the line above never lights with a word here
        lit = RL.layer()
        RL.draw_ar(lit, [line], size, y + n * lh, RL.VERSE_ON)
        lit_a = np.asarray(lit).copy()
        lw = line.split(" ")
        total = f.getlength(line, direction="rtl", language="ar")
        right = (SW + total) / 2
        y0, y1 = int(y + n * lh - lh * 0.6), int(y + (n + 1) * lh + lh * 0.3)
        sp = f.getlength(" ", direction="rtl", language="ar")
        for i in range(len(lw)):
            r_edge = right - (f.getlength(" ".join(lw[:i]), direction="rtl", language="ar") + sp / 2 if i else -8)
            l_edge = right - f.getlength(" ".join(lw[:i + 1]), direction="rtl", language="ar") - (sp / 2 if i < len(lw) - 1 else 8)
            m = np.zeros_like(lit_a)
            xa, xb = max(0, int(l_edge)), min(SW, int(r_edge) + 1)
            m[max(0, y0):min(SH, y1), xa:xb] = lit_a[max(0, y0):min(SH, y1), xa:xb]
            per_word.append(RL._Layer(Image.fromarray(m, "RGBA")))
    assert len(per_word) == len(words)
    return RL._Layer(dim), per_word, words


def final_layer():
    img = RL.layer()
    d = ImageDraw.Draw(img)
    f = font(R.F_LABEL, 46)
    t = f"YOUR SCORE:  ? / {len(ROUNDS)}"
    tw = f.getlength(t) + 84
    y = 640
    d.rounded_rectangle([(SW - tw) / 2, y, (SW + tw) / 2, y + 82], radius=41, fill=RL.GOLD + (255,))
    text_center(d, t, SW / 2, y + 14, f, (20, 34, 28, 255))
    text_center(d, "Comment your score below", SW / 2, y + 130, font(R.F_BODY, 50), RL.IVORY + (255,))
    text_center(d, "Send this to a friend and compare scores", SW / 2, y + 205, font(R.F_BODY, 42), RL.MEAL + (255,))
    # the four answers, so viewers can check their score
    RL.draw_label(img, "ANSWERS", y + 330, RL.GOLD)
    fa, fe = font(R.F_ARABIC, 52), font(R.F_LABEL, 34)
    for i, rk in enumerate(ROUNDS):
        en, ar = rk["options"][rk["answer"]]
        x, yy = (310 if i % 2 == 0 else 770), y + 400 + (i // 2) * 165
        d.rounded_rectangle([x - 200, yy, x + 200, yy + 145], radius=22, fill=GREEN + (40,), outline=GREEN + (200,), width=2)
        d.text((x - 182, yy + 12), str(i + 1), font=font(R.F_LABEL, 30), fill=GREEN + (255,))
        w = fa.getlength(ar, direction="rtl", language="ar")
        d.text((x - w / 2, yy + 4), ar, font=fa, fill=(236, 246, 238, 255), direction="rtl", language="ar")
        text_center(d, en, x, yy + 92, fe, (236, 246, 238, 255))
    return img


def build():
    t, parts = 0.0, []
    for k, rk in enumerate(ROUNDS):
        rk["static"] = RL._Layer(static_layer(rk, k))
        rk["dim"], rk["lit"], rk["words"] = verse_layers(rk)
        o, r = reveal_layers(rk)
        rk["others"], rk["right"] = RL._Layer(o), RL._Layer(r)
        rk["meaning"] = RL._Layer(meaning_layer(rk))
        starts, offset, pcms = [], 0.0, []
        for a in rk["verses"]:
            pcm = pcm_of(a)
            n = len(R._arabic_words(get(f"quran:{int(a[:3])}:{int(a[3:])}")["arabic_display"]))
            starts += [offset + s for s in word_starts(a, n)]
            offset += len(pcm) / SR
            pcms.append(pcm)
        pcm = np.concatenate(pcms)
        rk["t0"] = t
        rk["word_t"] = [t + s for s in starts]
        rk["rec_end"] = t + len(pcm) / SR
        rk["think0"] = rk["rec_end"] + GAP
        rk["reveal"] = rk["think0"] + THINK
        rk["t1"] = rk["reveal"] + REVEAL
        parts.append((t, pcm))
        t = rk["t1"]
    end = t + FINAL
    total = np.zeros((int(end * SR) + SR, 2), np.float32)
    for t0, pcm in parts:
        i = int(t0 * SR)
        total[i:i + len(pcm)] += pcm
    peak = np.abs(total).max() or 1
    total *= min(1.0, 0.89 * 32767 / peak)
    with wave.open(str(OUT / "guess_surah_audio.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(total[:int(end * SR)].clip(-32768, 32767).astype(np.int16).tobytes())
    return end


THINK_L = RL._Layer(think_layer())


def line_layer(text):
    img = RL.layer()
    text_center(ImageDraw.Draw(img), text, SW / 2, Y_CHAL, font(R.F_BODY, 58), RL.IVORY + (255,))
    return RL._Layer(img)


# the line under the label: the challenge, "Wait for the hard one" from the first answer, the challenge
# again from the fourth question on
CHAL_L, WAIT_L = line_layer(CHALLENGE), line_layer("Wait for the hard one")


def wait_share(t):
    up = min(1.0, max(0.0, (t - ROUNDS[0]["reveal"]) / 0.35))
    down = min(1.0, max(0.0, (t - (ROUNDS[-1]["t0"] - XFADE)) / 0.35))
    return up * (1 - down)
FINAL_L = RL._Layer(final_layer())
_fin = RL.layer()
_d = ImageDraw.Draw(_fin)
header(_fin, _d, len(ROUNDS), None)
text_center(_d, R.HANDLE, SW / 2, Y_HANDLE, font(R.F_LABEL, 28), RL.MUTED + (255,))
FINAL_HEAD = RL._Layer(_fin)


def draw_round(frame, rk, t, a=1.0):
    rk["static"].over(frame, a)
    rk["dim"].over(frame, a)
    for s, lw in zip(rk["word_t"], rk["lit"]):
        on = 1.0 if t >= rk["rec_end"] else min(1.0, max(0.0, (t - s) / 0.12))
        if on > 0:
            lw.over(frame, on * a)
    r = min(1.0, max(0.0, (t - rk["reveal"]) / 0.3))
    THINK_L.over(frame, a * (1 - r))
    share = min(1.0, max(0.0, (t - rk["think0"]) / THINK))
    if share > 0 and r < 1:
        x1 = 140 + int((SW - 280) * share)
        k = a * (1 - r)
        frame[Y_MID + 95:Y_MID + 103, 140:x1] = frame[Y_MID + 95:Y_MID + 103, 140:x1] * (1 - k) + np.array(RL.GOLD, np.float32) * k
    if r > 0:
        rk["others"].over(frame, r * a)
        rk["right"].over(frame, r * a)
        rk["meaning"].over(frame, r * a)


def frames(end):
    bg = RL.background()
    last = ROUNDS[-1]
    for i in range(int(round(end * FPS))):
        t = i / FPS
        frame = RL._ground(bg, t, end)
        if t >= last["t1"] - XFADE:                       # final screen
            x = min(1.0, (t - (last["t1"] - XFADE)) / XFADE)
            if x < 1:
                draw_round(frame, last, t, 1 - x)
            FINAL_HEAD.over(frame, x)
            FINAL_L.over(frame, x)
        else:
            k = max(j for j, rk in enumerate(ROUNDS) if t >= rk["t0"])
            rk, nxt = ROUNDS[k], (ROUNDS[k + 1] if k + 1 < len(ROUNDS) else None)
            if nxt and t > nxt["t0"] - XFADE:
                x = (t - (nxt["t0"] - XFADE)) / XFADE
                draw_round(frame, rk, t, 1 - x)
                draw_round(frame, nxt, nxt["t0"], x)
            else:
                draw_round(frame, rk, t)
        w = wait_share(t)
        CHAL_L.over(frame, 1 - w)
        WAIT_L.over(frame, w)
        yield t, frame.clip(0, 255).astype(np.uint8)


def main():
    end = build()
    video = OUT / "guess_surah.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}",
           "-r", str(FPS), "-i", "-", "-i", str(OUT / "guess_surah_audio.wav"), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{end:.2f}", "-movflags", "+faststart", str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    marks = {}
    marks[round(ROUNDS[0]["reveal"] + 0.6, 2)] = "wait"
    marks[round(ROUNDS[-1]["t0"] + 0.6, 2)] = "back"
    for rk in ROUNDS:
        marks[round(rk["t0"] + 0.4, 2)] = "start"
        marks[round((rk["t0"] + rk["rec_end"]) / 2, 2)] = "mid"
        marks[round(rk["think0"] + 2.0, 2)] = "think"
        marks[round(rk["reveal"] + 1.5, 2)] = "reveal"
    marks[round(end - 0.1, 2)] = "end"
    for t, f in frames(end):
        proc.stdin.write(f.tobytes())
        for m, name in list(marks.items()):
            if abs(t - m) < 0.5 / FPS:
                Image.fromarray(f).resize((432, 768)).save(OUT / f"g_{m:05.2f}_{name}.jpg", quality=85)
                marks.pop(m)
    proc.stdin.close()
    proc.wait()
    print("ok", video, f"{end:.1f}s", [(r["level"], round(r["t0"], 1), round(r["rec_end"] - r["t0"], 1)) for r in ROUNDS])


if __name__ == "__main__":
    main()
