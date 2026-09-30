"""Blend Wav2Lip's mouth region back onto the sharp source photo.

Wav2Lip regenerates the whole face at 96px, which softens the eyes and skin.
This keeps the original photo and swaps in only a feathered mouth/chin
ellipse from each lip-synced frame.

Usage: python3 scripts/lipsync_composite.py <wav2lip.mp4> <source.png> <out.mp4>
"""
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
# Mouth/chin ellipse in source-image pixels (girl_hook.png is 1280x720).
MOUTH_BOX = (530, 318, 730, 470)


def main(src_video, src_image, out):
    base = Image.open(src_image).convert("RGB")
    w, h = base.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse(MOUTH_BOX, fill=255)
    mask = np.asarray(mask.filter(ImageFilter.GaussianBlur(18)), dtype=np.float32)[..., None] / 255
    base_np = np.asarray(base, dtype=np.float32)

    reader = subprocess.Popen([FFMPEG, "-loglevel", "error", "-i", src_video, "-f", "rawvideo",
                               "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    writer = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo",
                               "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", "30", "-i", "-",
                               "-c:v", "libx264", "-crf", "12", "-preset", "fast",
                               "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n = 0
    while True:
        buf = reader.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        fr = Image.frombuffer("RGB", (w, h), buf)
        # restore a little crispness to the generated mouth
        fr = fr.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
        fr_np = np.asarray(fr, dtype=np.float32)
        out_np = base_np * (1 - mask) + fr_np * mask
        writer.stdin.write(out_np.astype(np.uint8).tobytes())
        n += 1
    writer.stdin.close()
    writer.wait()
    print(f"composited {n} frames -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
