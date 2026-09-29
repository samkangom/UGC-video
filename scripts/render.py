"""Render the 9:16 UGC ad for "Funding Your American Dream".

Frames are drawn with Pillow and piped to ffmpeg, then mixed with the
voiceover and background music.

Usage: python3 scripts/render.py [--preview]
"""
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda *p: os.path.join(ROOT, "assets", *p)  # noqa: E731
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1080, 1920, 30
DURATION = 38.6
NAVY = (14, 27, 51)
GOLD = (232, 190, 92)
YELLOW = (255, 214, 10)
WHITE = (255, 255, 255)

F_BOLD = os.path.join(ROOT, "fonts", "Montserrat-ExtraBold.ttf")
F_SEMI = os.path.join(ROOT, "fonts", "Montserrat-SemiBold.ttf")


def font(path, size, _cache={}):
    key = (path, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, size)
    return _cache[key]


# ---------------------------------------------------------------- captions
# Speech spans (seconds) measured from the voiceover with silencedetect,
# paired with the words spoken inside each span.
SPANS = [
    (0.00, 0.36, "Okay,"),
    (0.87, 4.12, "if you're an international student dreaming of studying in the U.S."),
    (4.63, 5.56, "you need to hear this."),
    (5.99, 6.54, "Tuition,"),
    (6.68, 7.16, "housing,"),
    (7.48, 8.20, "visa fees..."),
    (9.30, 10.60, "it feels impossible, right?"),
    (11.22, 13.56, "That's exactly why this book is on my radar."),
    (14.13, 15.74, "Funding Your American Dream,"),
    (16.22, 16.92, "by Finn Carter."),
    (17.45, 21.19, "It's a step-by-step guide for international students on how"),
    (21.36, 23.15, "to find scholarships, assistantships,"),
    (23.53, 26.39, "and real funding, so you can aim for a fully funded U.S. education."),
    (26.76, 27.27, "Honestly?"),
    (27.82, 30.03, "It's the roadmap I wish someone had handed me."),
    (30.48, 33.75, "It's free on Kindle Unlimited, or grab the paperback on Amazon."),
    (33.95, 35.56, "Your American dream starts here."),
    (35.90, 36.45, "Go get it!"),
]
HIGHLIGHT = {"international", "U.S.", "impossible,", "Funding", "American",
             "Dream,", "step-by-step", "scholarships,", "assistantships,",
             "funding,", "fully", "funded", "roadmap", "free", "Kindle",
             "Unlimited,", "paperback", "dream", "Go", "get", "it!",
             "Tuition,", "housing,", "visa", "fees...", "Finn", "Carter."}


def build_words():
    """Distribute each span's duration across its words by character count."""
    words = []
    for start, end, text in SPANS:
        toks = text.split()
        weights = np.array([len(t) + 2 for t in toks], dtype=float)
        edges = start + np.concatenate([[0], np.cumsum(weights)]) / weights.sum() * (end - start)
        for i, tok in enumerate(toks):
            words.append((edges[i], edges[i + 1], tok))
    return words


def build_chunks(words, max_words=3):
    """Group words into short caption chunks, breaking on punctuation."""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w[2][-1] in ",.?!":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        end = chunks[i + 1][0][0] if i + 1 < len(chunks) else c[-1][1] + 0.6
        end = min(end, c[-1][1] + 0.6)
        out.append((c[0][0], end, c))
    return out


WORDS = build_words()
CHUNKS = build_chunks(WORDS)


def draw_captions(img, t, y=1480):
    chunk = next((c for c in CHUNKS if c[0] <= t < c[1]), None)
    if not chunk:
        return
    start, _, words = chunk
    f = font(F_BOLD, 84)
    d = ImageDraw.Draw(img)
    texts = [w[2].upper() for w in words]
    space = 24
    widths = [d.textlength(s, font=f) for s in texts]
    total = sum(widths) + space * (len(texts) - 1)
    if total > W - 100:  # shrink long chunks to fit
        f = font(F_BOLD, int(84 * (W - 100) / total))
        widths = [d.textlength(s, font=f) for s in texts]
        total = sum(widths) + space * (len(texts) - 1)
    # pop-in scale on chunk start
    pop = min(1.0, (t - start) / 0.12)
    x = (W - total) / 2
    yy = y + (1 - pop) * 20
    for (ws, we, raw), s, wd in zip(words, texts, widths):
        active = ws <= t
        color = YELLOW if (raw in HIGHLIGHT and active) else WHITE
        if not active:
            color = (255, 255, 255)
        d.text((x, yy), s, font=f, fill=color, stroke_width=9, stroke_fill=(0, 0, 0),
               anchor="lm")
        x += wd + space


# ---------------------------------------------------------------- helpers
def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def cover_fit(im, w=W, h=H, fx=0.5):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    left = int(min(max(im.width * fx - w / 2, 0), im.width - w))
    top = (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def ken_burns(im, p, z0=1.0, z1=1.12, dx=0, dy=0):
    """Slow zoom/pan over a pre-fitted (slightly oversized) image."""
    z = z0 + (z1 - z0) * p
    cw, ch = W / z, H / z
    cx = im.width / 2 + dx * p
    cy = im.height / 2 + dy * p
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return im.resize((W, H), Image.BILINEAR, box=box)


def shadowed(im, radius=18, offset=(0, 24), blur=30, alpha=150):
    pad = blur * 2 + max(abs(offset[0]), abs(offset[1]))
    base = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, alpha))
    base.paste(sh, (pad + offset[0], pad + offset[1]))
    base = base.filter(ImageFilter.GaussianBlur(blur))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width, im.height), radius, fill=255)
    base.paste(im, (pad, pad), mask)
    return base, pad


def paste_center(bg, fg, cx, cy):
    bg.alpha_composite(fg, (int(cx - fg.width / 2), int(cy - fg.height / 2)))


def gradient_overlay(strength=200, start=0.55):
    g = np.zeros((H, W, 4), dtype=np.uint8)
    ys = np.linspace(0, 1, H)
    a = np.clip((ys - start) / (1 - start), 0, 1) ** 1.3 * strength
    g[..., 3] = a[:, None]
    return Image.fromarray(g, "RGBA")


def pill(d, y, text, f, fill, fg, pad=(34, 18)):
    """Rounded label horizontally centred on the frame."""
    tw = d.textlength(text, font=f)
    x = (W - tw) / 2 - pad[0]
    h = f.size + pad[1] * 2
    d.rounded_rectangle((x, y, x + tw + pad[0] * 2, y + h), h // 2, fill=fill)
    d.text((x + pad[0], y + h / 2), text, font=f, fill=fg, anchor="lm")
    return tw + pad[0] * 2, h


# ---------------------------------------------------------------- assets
def load_assets():
    cover = Image.open(A("cover.png")).convert("RGBA")
    def oversize(p, fx):
        return cover_fit(Image.open(A(p)).convert("RGB"), int(W * 1.15), int(H * 1.15), fx)

    bg_blur = cover_fit(cover.convert("RGB")).filter(ImageFilter.GaussianBlur(40))
    bg_blur = Image.blend(bg_blur, Image.new("RGB", (W, H), NAVY), 0.55)
    return {
        "cover": cover,
        "hook": oversize("broll_hook.png", 0.5),
        "stress": oversize("broll_stress.png", 0.63),
        "campus": oversize("broll_campus.png", 0.52),
        "bg": bg_blur.convert("RGBA"),
        "shade": gradient_overlay(),
        "shade_top": gradient_overlay(170, 0.0).transpose(Image.FLIP_TOP_BOTTOM),
    }


# ---------------------------------------------------------------- scenes
def scene_hook(S, t, t0, t1):
    p = (t - t0) / (t1 - t0)
    img = ken_burns(S["hook"], p, 1.0, 1.10, dy=-40).convert("RGBA")
    img.alpha_composite(S["shade"])
    d = ImageDraw.Draw(img)
    # "recording" UGC badge
    d.ellipse((60, 90, 90, 120), fill=(255, 59, 48) if int(t * 2) % 2 == 0 else (120, 20, 20))
    d.text((106, 105), "INTERNATIONAL STUDENTS", font=font(F_BOLD, 38), fill=WHITE,
           anchor="lm", stroke_width=5, stroke_fill=(0, 0, 0))
    if t > 0.2:
        a = ease((t - 0.2) / 0.3)
        f = font(F_BOLD, 64)
        y = 330 - (1 - a) * 40
        pill(d, y, "WANT TO STUDY IN THE U.S.?", f, (255, 214, 10), (0, 0, 0))
    return img


def scene_stress(S, t, t0, t1):
    p = (t - t0) / (t1 - t0)
    img = ken_burns(S["stress"], p, 1.12, 1.0, dx=30).convert("RGBA")
    img.alpha_composite(S["shade"])
    d = ImageDraw.Draw(img)
    items = [(5.99, "TUITION"), (6.68, "HOUSING"), (7.48, "VISA FEES")]
    for i, (ts, label) in enumerate(items):
        if t >= ts:
            a = ease((t - ts) / 0.2)
            x = 90 + (1 - a) * -200
            y = 260 + i * 150
            f = font(F_BOLD, 60)
            d.rounded_rectangle((x, y, x + 520, y + 110), 26, fill=(255, 255, 255, 235))
            d.text((x + 40, y + 55), "$", font=f, fill=(220, 40, 40), anchor="lm")
            d.text((x + 100, y + 55), label, font=f, fill=(20, 20, 20), anchor="lm")
    if t >= 9.3:
        a = ease((t - 9.3) / 0.25)
        f = font(F_BOLD, 76)
        txt = "IMPOSSIBLE?"
        tw = d.textlength(txt, font=f)
        y = 780
        d.rounded_rectangle(((W - tw) / 2 - 40, y, (W + tw) / 2 + 40, y + 120), 20,
                            fill=(220, 40, 40, int(255 * a)))
        d.text((W / 2, y + 60), txt, font=f, fill=(255, 255, 255, int(255 * a)), anchor="mm")
    return img


def cover_sprite(S, width):
    c = S["cover"]
    h = int(c.height * width / c.width)
    return shadowed(c.resize((width, h), Image.LANCZOS))[0]


def scene_reveal(S, t, t0, t1):
    img = S["bg"].copy()
    k = t - t0
    a = ease(k / 0.6)
    width = int(560 + 60 * a)
    sprite = cover_sprite(S, width)
    float_y = np.sin(k * 2.2) * 10
    paste_center(img, sprite, W / 2, 780 + (1 - a) * 300 + float_y)
    d = ImageDraw.Draw(img)
    f = font(F_BOLD, 50)
    tx = "THE BOOK ON MY RADAR"
    d.text((W / 2, 160), tx, font=f, fill=GOLD, anchor="mm", stroke_width=4,
           stroke_fill=(0, 0, 0))
    return img


def scene_features(S, t, t0, t1):
    img = S["bg"].copy()
    k = t - t0
    sprite = cover_sprite(S, 400)
    paste_center(img, sprite, W / 2, 470 + np.sin(k * 2) * 6)
    d = ImageDraw.Draw(img)
    items = [
        (17.6, "Step-by-step guide"),
        (21.6, "Scholarships"),
        (22.3, "Assistantships"),
        (23.6, "Real funding options"),
        (24.9, "Fully funded U.S. education"),
    ]
    f = font(F_SEMI, 50)
    for i, (ts, label) in enumerate(items):
        if t < ts:
            continue
        a = ease((t - ts) / 0.25)
        y = 880 + i * 108
        x = 110 + (1 - a) * 80
        d.rounded_rectangle((x, y, x + 860, y + 90), 22, fill=(255, 255, 255, int(235 * a)))
        d.ellipse((x + 18, y + 17, x + 74, y + 73), fill=(34, 170, 90, int(255 * a)))
        d.text((x + 46, y + 45), "✓", font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40),
               fill=(255, 255, 255, int(255 * a)), anchor="mm")
        d.text((x + 100, y + 45), label, font=f, fill=(14, 27, 51, int(255 * a)), anchor="lm")
    return img


def scene_campus(S, t, t0, t1):
    p = (t - t0) / (t1 - t0)
    img = ken_burns(S["campus"], p, 1.0, 1.12, dy=-30).convert("RGBA")
    img.alpha_composite(S["shade"])
    d = ImageDraw.Draw(img)
    if t > t0 + 0.8:
        a = ease((t - t0 - 0.8) / 0.3)
        f = font(F_BOLD, 58)
        pill(d, 300 - (1 - a) * 30, "THE ROADMAP I WISH I HAD",
             f, (255, 255, 255), NAVY)
    return img


def scene_cta(S, t, t0, t1):
    img = S["bg"].copy()
    k = t - t0
    a = ease(k / 0.5)
    sprite = cover_sprite(S, 470)
    paste_center(img, sprite, W / 2, 560 + (1 - a) * -200 + np.sin(k * 2) * 6)
    d = ImageDraw.Draw(img)
    # format chips (prices from the Amazon listing)
    f_big = font(F_BOLD, 54)
    f_small = font(F_SEMI, 34)
    chips = [
        (30.9, "KINDLE UNLIMITED", "$0 TO READ", (255, 214, 10), (0, 0, 0)),
        (32.2, "PAPERBACK", "$15.99", (255, 255, 255), NAVY),
    ]
    for i, (ts, top, bottom, bg, fg) in enumerate(chips):
        if t < ts:
            continue
        b = ease((t - ts) / 0.25)
        x = 70 + i * 480
        y = 1020 + (1 - b) * 40
        d.rounded_rectangle((x, y, x + 460, y + 170), 28, fill=bg + (int(255 * b),))
        d.text((x + 230, y + 58), top, font=f_small, fill=fg, anchor="mm")
        d.text((x + 230, y + 118), bottom, font=f_big, fill=fg, anchor="mm")
    if t >= 33.9:
        b = ease((t - 33.9) / 0.3)
        pulse = 1 + 0.03 * np.sin((t - 33.9) * 8)
        f = font(F_BOLD, int(52 * pulse))
        txt = "AVAILABLE NOW ON AMAZON"
        tw = d.textlength(txt, font=f)
        y = 1260
        d.rounded_rectangle(((W - tw) / 2 - 44, y, (W + tw) / 2 + 44, y + 110), 55,
                            fill=(255, 153, 0, int(255 * b)))
        d.text((W / 2, y + 55), txt, font=f, fill=(0, 0, 0, int(255 * b)), anchor="mm")
    return img


SCENES = [
    (0.0, 5.75, scene_hook),
    (5.75, 11.0, scene_stress),
    (11.0, 17.3, scene_reveal),
    (17.3, 27.5, scene_features),
    (27.5, 30.3, scene_campus),
    (30.3, DURATION, scene_cta),
]
XFADE = 0.25


def render_frame(S, t):
    for i, (t0, t1, fn) in enumerate(SCENES):
        if t0 <= t < t1:
            img = fn(S, t, t0, t1)
            # quick crossfade from the previous scene
            if i > 0 and t - t0 < XFADE:
                pt0, pt1, pfn = SCENES[i - 1]
                prev = pfn(S, t, pt0, pt1)
                img = Image.blend(prev, img, (t - t0) / XFADE)
            break
    # captions sit in the lower third, clear of scene graphics
    cap_y = 1690 if fn in (scene_features, scene_cta) else 1480
    draw_captions(img, t, cap_y)
    # end card fade
    if t > DURATION - 0.6:
        img = Image.blend(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)),
                          (t - (DURATION - 0.6)) / 0.6 * 0.6)
    return img.convert("RGB")


def main():
    S = load_assets()
    out_dir = os.path.join(ROOT, "output")
    os.makedirs(out_dir, exist_ok=True)
    if "--preview" in sys.argv:
        for t in [0.5, 3.0, 7.9, 10.0, 13.0, 16.5, 25.5, 29.0, 32.8, 35.0]:
            render_frame(S, t).save(os.path.join(out_dir, f"preview_{t:05.1f}.jpg"), quality=85)
        return

    silent = os.path.join(out_dir, "_video.mp4")
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        proc.stdin.write(render_frame(S, i / FPS).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()

    final = os.path.join(out_dir, "funding_your_american_dream_ugc.mp4")
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", silent,
         "-i", A("voiceover.mp3"), "-i", A("music.wav"),
         "-filter_complex",
         "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[v][key];"
         "[2:a]volume=0.12[m];"
         "[m][key]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400[duck];"
         "[duck][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", str(DURATION), "-movflags", "+faststart", final],
        check=True)
    os.remove(silent)
    print("wrote", final)


if __name__ == "__main__":
    main()
