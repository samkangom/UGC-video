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
