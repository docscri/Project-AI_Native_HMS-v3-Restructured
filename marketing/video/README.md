# Demo videos (HyperFrames)

Two sales films built with [HyperFrames](https://hyperframes.heygen.com) (HTML → MP4) from real screens of the psychiatry demo clinic.
- `main/`: 16:9, about 1:21. `short/`: 9:16, about 0:29, with the contact numbers.
- `build_main.py` / `build_short.py` write each project's `index.html` and `compositions/` from `script.txt`, the
  voice clip lengths (`assets/audio/vo-N.mp3`) and measured button positions.
- Voice: Gemini TTS (voice Kore), one request per script, split at pauses. Music ducks under the voice, mixed to about −16 LUFS.
  GSAP is vendored in `assets/vendor/` (the CDN may be blocked).

Rebuild and render (Node 22+, FFmpeg):
```bash
python marketing/video/build_main.py      # or build_short.py
cd marketing/video/main && npx hyperframes check && npx hyperframes render --quality delivery -o dictate-main.mp4
```
