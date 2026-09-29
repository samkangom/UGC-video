"""Synthesize a light, royalty-free background track (soft keys + pad + shaker).

Usage: python3 scripts/make_music.py <seconds> <out.wav>
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 92
BEAT = 60 / BPM


def note_hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def keys_tone(freq, dur):
    """Soft electric-piano-like tone with a decaying envelope."""
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 200))
    wave_ = (np.sin(2 * np.pi * freq * t)
             + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 4)
             + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 6))
    return wave_ * env


def pad_tone(freqs, dur):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for f in freqs:
        for detune in (-0.6, 0.6):
            out += np.sin(2 * np.pi * (f + detune) * t)
    attack = np.minimum(t / 0.8, 1)
    release = np.minimum((dur - t) / 0.8, 1)
    return out * attack * release / (2 * len(freqs))


def main(seconds, out_path):
    n = int(seconds * SR)
    mix = np.zeros(n + SR * 4)
    # I - V - vi - IV in C major (C, G, Am, F), two bars each chord = 4 beats
    progression = [
        [48, 60, 64, 67],  # C
        [43, 59, 62, 67],  # G
        [45, 60, 64, 69],  # Am
        [41, 60, 65, 69],  # F
    ]
    bar = 4 * BEAT
    rng = np.random.default_rng(7)
    t0 = 0.0
    i = 0
    while t0 < seconds:
        chord = progression[i % 4]
        start = int(t0 * SR)
        pad = pad_tone([note_hz(m) for m in chord[1:]], bar) * 0.10
        mix[start:start + len(pad)] += pad
        bass = keys_tone(note_hz(chord[0]), bar) * 0.22
        mix[start:start + len(bass)] += bass
        # gentle arpeggiated keys on eighth notes
        pattern = [1, 2, 3, 2, 1, 3, 2, 3]
        for k, idx in enumerate(pattern):
            s = int((t0 + k * BEAT / 2) * SR)
            tone = keys_tone(note_hz(chord[idx] + 12), BEAT * 2) * 0.09
            mix[s:s + len(tone)] += tone
        # soft shaker on off-beats
        for k in range(8):
            if k % 2 == 1:
                s = int((t0 + k * BEAT / 2) * SR)
                ln = int(0.06 * SR)
                noise = rng.standard_normal(ln) * np.exp(-np.arange(ln) / (0.012 * SR))
                noise = np.diff(noise, prepend=0)  # crude high-pass
                mix[s:s + ln] += noise * 0.02
        t0 += bar
        i += 1

    mix = mix[:n]
    fade = int(2.0 * SR)
    mix[:int(0.5 * SR)] *= np.linspace(0, 1, int(0.5 * SR))
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.8
    pcm = (mix * 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm]).ravel()
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])
