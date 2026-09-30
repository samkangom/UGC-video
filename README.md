# UGC video: *Funding Your American Dream* by Finn Carter

A 38-second vertical (1080×1920, 9:16) UGC-style ad for
[the book on Amazon](https://www.amazon.com/dp/B0HLB5JFPZ). It is ready for TikTok, Reels and Shorts.

**Final video:** `output/funding_your_american_dream_ugc.mp4`

## Storyboard

| Time | Visual | Voiceover |
|------|--------|-----------|
| 0–5.7s | Selfie-style creator shot, "WANT TO STUDY IN THE U.S.?" | "Okay, if you're an international student dreaming of studying in the U.S.... you need to hear this." |
| 5.7–11s | Stressed student at a desk; Tuition / Housing / Visa fees cards, then "IMPOSSIBLE?" | "Tuition, housing, visa fees... it feels impossible, right?" |
| 11–17.3s | Book cover reveal | "That's exactly why this book is on my radar. Funding Your American Dream, by Finn Carter." |
| 17.3–27.5s | Cover plus an animated checklist (step-by-step, scholarships, assistantships, funding, fully funded) | "It's a step-by-step guide for international students on how to find scholarships, assistantships, and real funding, so you can aim for a fully funded U.S. education." |
| 27.5–30.3s | Students on an autumn campus, "THE ROADMAP I WISH I HAD" | "Honestly? It's the roadmap I wish someone had handed me." |
| 30.3–38.6s | CTA: cover, Kindle Unlimited $0 / Paperback $15.99, "AVAILABLE NOW ON AMAZON" | "It's free on Kindle Unlimited, or grab the paperback on Amazon. Your American dream starts here. Go get it!" |

Burned-in, word-by-word captions run the whole time, with keywords highlighted in yellow.

## Assets
- `assets/voiceover.mp3`: ElevenLabs TTS, voice "Lyan" (a natural, young American female voice for UGC).
- `assets/music.wav`: a soft keys, pad and shaker loop. `scripts/make_music.py` synthesizes it, so it is royalty-free. It is ducked under the voice.
- `assets/broll_*.png`: AI-generated B-roll made with ElevenLabs Seedream 5 Pro.
- `assets/cover.png`: the book cover, cropped from the Amazon listing screenshot.
- `fonts/`: Montserrat, under the SIL Open Font License.

## Rebuild
```bash
pip install pillow numpy imageio-ffmpeg
python3 scripts/make_music.py 39 assets/music.wav
python3 scripts/render.py --preview   # still frames in output/
python3 scripts/render.py             # full video
```

---

# TikTok cut: an AI creator trying out the book

**Final video:** `output/funding_your_american_dream_tiktok.mp4` (30.4s, 1080×1920, 30 fps)

A realistic AI-generated creator reacts to the book, reads it, takes notes and recommends it.
All text stays inside TikTok's safe zone, clear of the app's top bar, right-hand buttons and bottom caption area.

| Time | Shot | Voiceover / on-screen text |
|------|------|----------------------------|
| 0–5.6s | **Hook.** Selfie shot that whips from her face to the book, then punches back in on her face | "Wait… this book actually shows you how to study in the U.S. fully funded?!" / **WAIT… A FULLY FUNDED U.S. DEGREE?!** |
| 5.6–10.4s | Reading on her bed, then a close-up for "same." | "If you're an international student and U.S. tuition scares you… same." |
| 10.4–13.7s | Top-down shot of her hands holding the book, with sticky tabs | "So I picked up Funding Your American Dream by Finn Carter." |
| 13.7–19.8s | Reading, with a checklist popping in | Scholarships ✓ Assistantships ✓ Real funding options ✓ |
| 19.8–22s | Sticky tabs and highlighter | "I'm literally taking notes right now." |
| 22–30.4s | Call to action: book, then back to her face | Kindle Unlimited $0 / Paperback $15.99 / "Search on Amazon: Funding Your American Dream" |

- **Creator images** (`assets/v2/girl_*.png`, `book_pov.png`): ElevenLabs gpt-image-2 and Nano Banana Pro, with the real cover as a reference image.
- **Voice** (`assets/v2/voiceover.mp3`): ElevenLabs v3, voice "Lara".
- **Captions:** word timings come from faster-whisper and are saved in `assets/v2/words.json`.
- **Rebuild:** `python3 scripts/render_tiktok.py` (add `--preview` for still frames only).
