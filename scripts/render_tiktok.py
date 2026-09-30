"""Render the TikTok cut: an AI creator "trying out" Funding Your American Dream.

Inputs (assets/v2): girl_hook.png, girl_reading.png, book_pov.png,
voiceover.mp3, words.json (word timestamps from faster-whisper).
Usage: python3 scripts/render_tiktok.py [--preview]
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import (F_BOLD, F_SEMI, FFMPEG, NAVY, ROOT, W, H, FPS, WHITE,  # noqa: E402
                    YELLOW, ease, font, pill)

V2 = lambda *p: os.path.join(ROOT, "assets", "v2", *p)  # noqa: E731
DURATION = 30.4
# TikTok overlays its UI on the top ~180px, the right ~150px and the bottom
# ~400px, so on-screen text stays inside this box.
SAFE_L, SAFE_R = 60, W - 160

WORDS = [tuple(w) for w in json.load(open(V2("words.json")))]
HIGHLIGHT = {"wait,", "fully", "funded?", "international", "tuition", "same.",
             "funding", "your", "american", "dream", "scholarships,",
             "assistantships,", "literally", "notes", "free", "kindle",
             "unlimited,", "paperback", "amazon.", "get", "this", "book."}


# ---------------------------------------------------------------- captions
def caption_chunks(max_words=3):
    chunks, cur = [], []
    for w in WORDS:
        cur.append(w)
        if len(cur) >= max_words or w[2][-1] in ",.?!":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        nxt = chunks[i + 1][0][0] if i + 1 < len(chunks) else c[-1][1] + 0.8
        out.append((c[0][0], min(nxt, c[-1][1] + 0.5), c))
    return out


CHUNKS = caption_chunks()


def draw_captions(img, t, y=1180):
    chunk = next((c for c in CHUNKS if c[0] <= t < c[1]), None)
    if not chunk:
        return
    start, _, words = chunk
    d = ImageDraw.Draw(img)
    size = 80
    texts = [w[2].upper().replace("US", "U.S.") if w[2].strip(",.?!") == "US" else w[2].upper()
             for w in words]
    f = font(F_BOLD, size)
    space = 22
    widths = [d.textlength(s, font=f) for s in texts]
    total = sum(widths) + space * (len(texts) - 1)
    maxw = SAFE_R - SAFE_L
    if total > maxw:
        f = font(F_BOLD, int(size * maxw / total))
        widths = [d.textlength(s, font=f) for s in texts]
        total = sum(widths) + space * (len(texts) - 1)
    pop = ease((t - start) / 0.1)
    x = SAFE_L + (maxw - total) / 2
    for (ws, _, raw), s, wd in zip(words, texts, widths):
        active = ws <= t + 0.02
        hot = active and raw.lower() in HIGHLIGHT
        color = YELLOW if hot else WHITE
        d.text((x, y + (1 - pop) * 16), s, font=f, fill=color, stroke_width=9,
               stroke_fill=(0, 0, 0), anchor="lm")
        x += wd + space


# ---------------------------------------------------------------- camera
RNG = np.random.default_rng(3)
_SHAKE = np.cumsum(RNG.normal(0, 1, (int(DURATION * FPS) + 10, 3)), axis=0)
_SHAKE -= np.convolve(_SHAKE[:, 0], np.ones(15) / 15, "same")[:, None] * 0  # keep drift
_SHAKE = (_SHAKE - _SHAKE.mean(0)) / (np.abs(_SHAKE).max(0) + 1e-9)


def handheld(t, amp=10.0):
    """Smooth pseudo-random phone-in-hand wobble (dx, dy, degrees)."""
    i = int(t * FPS)
    s = _SHAKE[min(i, len(_SHAKE) - 1)]
    wob = np.array([np.sin(t * 1.7), np.cos(t * 1.3), np.sin(t * 0.9)])
    return amp * (0.6 * s[0] + 0.4 * wob[0]), amp * (0.6 * s[1] + 0.4 * wob[1]), 0.35 * s[2]


def shot(src, t, c0, c1, p, amp=10.0):
    """Crop a moving window from `src`.

    c0/c1 are (cx, cy, h) in source fractions: centre and window height
    (as a fraction of source height) at the start/end of the shot. The
    window is always 9:16.
    """
    k = ease(p) if p < 1 else 1.0
    cx = c0[0] + (c1[0] - c0[0]) * k
    cy = c0[1] + (c1[1] - c0[1]) * k
    hh = (c0[2] + (c1[2] - c0[2]) * k) * src.height
    hh = min(hh, src.height - 1)
    ww = min(hh * W / H, src.width - 1)
    hh = ww * H / W
    dx, dy, rot = handheld(t, amp)
    scale = hh / H
    cxp = cx * src.width + dx * scale
    cyp = cy * src.height + dy * scale
    cxp = min(max(cxp, ww / 2), src.width - ww / 2)
    cyp = min(max(cyp, hh / 2), src.height - hh / 2)
    box = (max(cxp - ww / 2, 0), max(cyp - hh / 2, 0),
           min(cxp + ww / 2, src.width), min(cyp + hh / 2, src.height))
    out = src.resize((W + 40, H + 72), Image.BICUBIC, box=box)
    out = out.rotate(rot, resample=Image.BICUBIC)
    return out.crop((20, 36, 20 + W, 36 + H))


def punch(img, t, t_cut, strength=0.06, dur=0.18):
    """Quick zoom-in punch right after a cut."""
    if not (0 <= t - t_cut < dur):
        return img
    z = 1 + strength * (1 - (t - t_cut) / dur)
    w2, h2 = int(W / z), int(H / z)
    box = ((W - w2) // 2, (H - h2) // 2, (W + w2) // 2, (H + h2) // 2)
    return img.resize((W, H), Image.BILINEAR, box=box)


# ---------------------------------------------------------------- overlays
def hook_text(d, t):
    if t > 4.9:
        return
    a = ease(t / 0.15)
    lines = ["WAIT... A FULLY FUNDED", "U.S. DEGREE?!"]
    f = font(F_BOLD, 66)
    y = 250 - (1 - a) * 30
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=f)
        x = SAFE_L + (SAFE_R - SAFE_L - tw) / 2
        d.rounded_rectangle((x - 26, y + i * 100 - 8, x + tw + 26, y + i * 100 + 86), 18,
                            fill=WHITE)
        d.text((x, y + i * 100 + 39), ln, font=f, fill=(0, 0, 0), anchor="lm")


def label(d, t, t0, t1, text, y=300, fill=WHITE, fg=(0, 0, 0), size=54):
    if not (t0 <= t < t1):
        return
    a = ease((t - t0) / 0.2)
    f = font(F_BOLD, size)
    tw = d.textlength(text, font=f)
    x = SAFE_L + (SAFE_R - SAFE_L - tw) / 2
    yy = y - (1 - a) * 24
    d.rounded_rectangle((x - 30, yy, x + tw + 30, yy + size + 40), (size + 40) // 2,
                        fill=fill)
    d.text((x, yy + (size + 40) / 2), text, font=f, fill=fg, anchor="lm")


def checklist(d, t):
    items = [(15.16, "Scholarships"), (15.6, "Assistantships"), (16.98, "Real funding options")]
    f = font(F_SEMI, 50)
    for i, (ts, txt) in enumerate(items):
        if t < ts or t > 19.8:
            continue
        a = ease((t - ts) / 0.2)
        x = SAFE_L + 10 - (1 - a) * 120
        y = 260 + i * 104
        d.rounded_rectangle((x, y, x + 680, y + 86), 22, fill=(255, 255, 255, 240))
        d.ellipse((x + 16, y + 15, x + 72, y + 71), fill=(34, 170, 90))
        d.text((x + 44, y + 43), "✓",
               font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38),
               fill=WHITE, anchor="mm")
        d.text((x + 96, y + 43), txt, font=f, fill=NAVY, anchor="lm")


def cta(d, t):
    if t >= 24.5:
        a = ease((t - 24.5) / 0.2)
        f1, f2 = font(F_SEMI, 34), font(F_BOLD, 50)
        x, y = SAFE_L + 10, 205 - (1 - a) * 30
        d.rounded_rectangle((x, y, x + 400, y + 150), 26, fill=YELLOW)
        d.text((x + 200, y + 48), "KINDLE UNLIMITED", font=f1, fill=(0, 0, 0), anchor="mm")
        d.text((x + 200, y + 106), "$0 TO READ", font=f2, fill=(0, 0, 0), anchor="mm")
    if t >= 26.3:
        a = ease((t - 26.3) / 0.2)
        f1, f2 = font(F_SEMI, 34), font(F_BOLD, 50)
        x, y = SAFE_L + 430, 205 - (1 - a) * 30
        d.rounded_rectangle((x, y, x + 400, y + 150), 26, fill=WHITE)
        d.text((x + 200, y + 48), "PAPERBACK", font=f1, fill=NAVY, anchor="mm")
        d.text((x + 200, y + 106), "$15.99", font=f2, fill=NAVY, anchor="mm")
    if t >= 27.0:
        a = ease((t - 27.0) / 0.25)
        pulse = 1 + 0.025 * np.sin((t - 27.0) * 7)
        f = font(F_BOLD, int(40 * pulse))
        lines = ["SEARCH ON AMAZON:", "FUNDING YOUR AMERICAN DREAM"]
        y = 375 - (1 - a) * 20
        for i, ln in enumerate(lines):
            tw = d.textlength(ln, font=f)
            x = SAFE_L + (SAFE_R - SAFE_L - tw) / 2
            d.rounded_rectangle((x - 24, y + i * 70, x + tw + 24, y + i * 70 + 62), 16,
                                fill=(255, 153, 0))
            d.text((x, y + i * 70 + 31), ln, font=f, fill=(0, 0, 0), anchor="lm")


# ---------------------------------------------------------------- timeline
# (start, end, image key, crop start (cx, cy, h), crop end, overlay fn)
SHOTS = [
    # hook: she's talking to camera, whips to the book on "this book",
    # then back to her face for "fully funded?!"
    (0.00, 1.00, "hook", (0.47, 0.50, 1.00), (0.47, 0.47, 0.90)),
    (1.00, 3.90, "hook", (0.72, 0.52, 1.00), (0.72, 0.50, 0.86)),
    (3.90, 10.45, "hook", (0.50, 0.46, 1.00), (0.49, 0.45, 0.86)),
    # the book
    (10.45, 13.65, "pov", (0.50, 0.46, 1.00), (0.48, 0.40, 0.72)),
    # what's inside
    (13.65, 19.80, "reading", (0.40, 0.48, 0.70), (0.34, 0.50, 0.60)),
    # taking notes: tabs + highlighter
    (19.80, 21.95, "pov", (0.80, 0.52, 0.55), (0.72, 0.44, 0.62)),
    # CTA: talking to camera, prices over the book, then back to her face
    (21.95, 24.40, "hook", (0.49, 0.47, 1.00), (0.49, 0.46, 0.90)),
    (24.40, 27.95, "pov", (0.50, 0.50, 0.95), (0.50, 0.46, 0.85)),
    (27.95, DURATION, "hook", (0.50, 0.50, 1.00), (0.48, 0.46, 0.86)),
]


def load():
    def rgb(p):
        return Image.open(V2(p)).convert("RGB")
    return {"hook": rgb("girl_hook.png"), "talk": load_talk(),
            "reading": rgb("girl_reading.png"), "pov": rgb("book_pov.png")}


def load_talk():
    """Lip-synced frames of the hook photo (see scripts/lipsync_composite.py)."""
    w, h = 1280, 720
    raw = subprocess.run([FFMPEG, "-loglevel", "error", "-i", V2("hook_talk.mp4"),
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [raw[i * w * h * 3:(i + 1) * w * h * 3] for i in range(n)]


def hook_frame(S, t):
    talk = S["talk"]
    i = int(t * FPS)
    if i >= len(talk):
        return S["hook"]
    return Image.frombuffer("RGB", (1280, 720), talk[i])


GRAIN = [Image.fromarray(np.clip(128 + np.random.default_rng(i).normal(0, 9, (H // 2, W // 2)),
                                 0, 255).astype(np.uint8)).resize((W, H)) for i in range(6)]


def frame(S, t):
    for t0, t1, key, c0, c1 in SHOTS:
        if t0 <= t < t1:
            break
    src = hook_frame(S, t) if key == "hook" else S[key]
    img = shot(src, t, c0, c1, (t - t0) / (t1 - t0))
    img = punch(img, t, t0)
    # subtle film grain so upscaled stills read like phone footage
    g = GRAIN[int(t * FPS) % len(GRAIN)]
    img = Image.blend(img, Image.merge("RGB", (g, g, g)), 0.04)
    img = img.convert("RGBA")
    d = ImageDraw.Draw(img)
    hook_text(d, t)
    label(d, t, 5.72, 10.45, "INTERNATIONAL STUDENTS", y=260)
    label(d, t, 10.5, 13.65, "MY NEW FAVORITE BOOK", y=260, fill=YELLOW)
    checklist(d, t)
    label(d, t, 19.85, 21.95, "LITERALLY TAKING NOTES", y=260)
    cta(d, t)
    # keep captions off her mouth while she is talking on camera
    draw_captions(img, t, 1440 if key == "hook" else 1180)
    return img.convert("RGB")


def main():
    S = load()
    out_dir = os.path.join(ROOT, "output")
    os.makedirs(out_dir, exist_ok=True)
    if "--preview" in sys.argv:
        for t in [0.5, 2.5, 4.6, 7.5, 9.8, 12.0, 17.5, 20.8, 23.0, 26.8, 29.0]:
            frame(S, t).save(os.path.join(out_dir, f"tt_preview_{t:04.1f}.jpg"), quality=85)
        return
    silent = os.path.join(out_dir, "_tt_video.mp4")
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        proc.stdin.write(frame(S, i / FPS).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    final = os.path.join(out_dir, "funding_your_american_dream_tiktok.mp4")
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", silent,
         "-i", V2("voiceover.mp3"), "-i", os.path.join(ROOT, "assets", "music.wav"),
         "-filter_complex",
         "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[v][key];"
         "[2:a]volume=0.12,afade=t=out:st=28.9:d=1.5[m];"
         "[m][key]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400[duck];"
         "[duck][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", str(DURATION), "-movflags", "+faststart", final],
        check=True)
    os.remove(silent)
    print("wrote", final)


if __name__ == "__main__":
    main()
