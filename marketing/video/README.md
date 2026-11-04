# Demo videos (HyperFrames)

Sales demo films for Dictate, built with [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML to MP4) from real screens of
the app running the psychiatry demo clinic (`python scripts/seed_demo.py`). Invented people only.

- `main/`: the main film, 16:9, about 66 s. `build_main.py` writes its `index.html` and `compositions/` from the script
  (`main/script.txt`), the voice-over clip lengths (`main/assets/audio/vo-N.mp3`) and the measured button positions.
- Voice-over: Kokoro (open-source text-to-speech, run locally), a 50/50 blend of its `hf_alpha` and `bf_emma` voices, speed 0.95.
  Music: a slow ambient pad synthesised for this film (no licence needed).

Rebuild and render (Node 22+, FFmpeg):

    python marketing/video/build_main.py
    cd marketing/video/main
    npx hyperframes check
    npx hyperframes render --quality delivery -o dictate-main.mp4
