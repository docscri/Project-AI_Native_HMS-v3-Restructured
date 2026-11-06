"""Writes the 30-second vertical film (9:16) as a HyperFrames project in short/, in the main film's design.

    python marketing/video/build_short.py

The clinic's contact numbers stay at the top of the frame throughout, just below the band phone apps cover.
Timings come from the voice clips (short/assets/audio/vo-N.mp3, one per line of short/script.txt).
"""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent / "short"
W, H = 1080, 1920
LEAD, HOLD, END_HOLD = 0.35, 0.8, 3.0
CONTACT = ("+91 62387 83592", "+91 98462 52339")
CSS_VARS = "--ground:#0B1411;--ground-2:#121D19;--ink:#E8F1EC;--muted:#8FA39A;--lime:#B6F36B;--amber:#FFB04D"
PHONE = dict(x=290, y=372, w=500, h=1083)        # the phone on the canvas (screens are 390x844 captures at 3x)
PHONE_ICON = ('<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#0B1411" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8'
              'a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg>')
PLANE = ('<svg viewBox="0 0 120 60" width="190" height="95" fill="none" stroke="#B6F36B" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">'
         '<path d="M6 34 C 20 30, 70 28, 104 27 C 114 27, 118 31, 112 35 C 100 40, 40 42, 14 40 Z"/>'
         '<path d="M50 30 L 34 10 L 44 10 L 70 29"/><path d="M52 39 L 40 54 L 49 54 L 70 39"/>'
         '<path d="M10 33 L 4 20 L 12 20 L 22 31"/><circle cx="96" cy="30" r="1.6" fill="#B6F36B"/><circle cx="88" cy="30" r="1.6" fill="#B6F36B"/>'
         '<circle cx="80" cy="30" r="1.6" fill="#B6F36B"/></svg>')


def dur(path: Path) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


BASE_CSS = f"""
#root {{ position:absolute; inset:0; {CSS_VARS}; background:transparent; font-family:'Manrope', sans-serif; color:var(--ink); overflow:hidden; }}
.w {{ display:inline-block; }}
.phone {{ position:absolute; left:{PHONE['x']}px; top:{PHONE['y']}px; width:{PHONE['w']}px; height:{PHONE['h']}px; border-radius:58px; overflow:hidden;
  border:12px solid #1d2925; background:#0B1411; box-shadow:0 50px 100px -30px #000, 0 0 0 1px #ffffff1a; }}
.phone img {{ position:absolute; left:0; top:0; width:100%; height:100%; object-fit:cover; object-position:top; }}
.chap {{ position:absolute; left:0; right:0; top:300px; display:flex; justify-content:center; }}
.chap > div {{ position:absolute; display:flex; align-items:center; gap:14px; opacity:0; }}
.chap b {{ width:44px; height:44px; border-radius:12px; background:var(--lime); color:#0B1411; display:grid; place-items:center; font-size:22px; font-weight:800; }}
.chap span {{ font-size:36px; font-weight:800; letter-spacing:-.01em; }}
"""


def scene(sid, d, css, html, js):
    return f"""<template>
  <style>
    @font-face {{ font-family:'Manrope'; src:url('assets/fonts/manrope-latin.woff2') format('woff2'); font-weight:400 800; }}
    {BASE_CSS}
    {css}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
    {html}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {js}
    tl.to({{}}, {{ duration: {d:.2f} }}, 0);
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""


def words(text, cls=""):
    return " ".join(f'<span class="w {cls}">{w}</span>' for w in text.split())


def words_in(sel, t, gap=0.1):
    return (f'tl.fromTo("{sel}", {{ opacity:0, filter:"blur(6px)" }}, '
            f'{{ opacity:1, filter:"blur(0px)", duration:0.16, ease:"power2.out", stagger:{gap} }}, {t:.2f});\n')


def rise(sel, t, d=0.7):
    return f'tl.fromTo("{sel}", {{ y:80, opacity:0, filter:"blur(8px)" }}, {{ y:0, opacity:1, filter:"blur(0px)", duration:{d}, ease:"expo.out" }}, {t:.2f});\n'


def phone(sid, shots):
    imgs = "".join(f'<img id="{sid}-{n}" src="assets/shots/{f}.jpg" style="opacity:{1 if i == 0 else 0}">' for i, (n, f) in enumerate(shots))
    return f'<div class="phone" id="{sid}-ph">{imgs}</div>'


def swap(sid, a, b, t):
    return (f'tl.to("#{sid}-{a}", {{ opacity:0, filter:"blur(6px)", duration:0.16, ease:"power2.in" }}, {t:.2f});\n'
            f'tl.fromTo("#{sid}-{b}", {{ opacity:0, filter:"blur(6px)" }}, {{ opacity:1, filter:"blur(0px)", duration:0.16, ease:"power2.out", immediateRender:false }}, {t:.2f});\n')


def chapters(sid, items):
    """Numbered chapter labels above the phone, one at a time: [(number, title, time)]."""
    html = '<div class="chap">' + "".join(f'<div id="{sid}-ch{i}"><b>{n}</b><span>{t}</span></div>' for i, (n, t, _) in enumerate(items)) + '</div>'
    js = ""
    for i, (_, _, t) in enumerate(items):
        js += f'tl.fromTo("#{sid}-ch{i}", {{ opacity:0, y:-12 }}, {{ opacity:1, y:0, duration:0.3, ease:"expo.out", immediateRender:false }}, {t:.2f});\n'
        if i + 1 < len(items):
            js += f'tl.to("#{sid}-ch{i}", {{ opacity:0, y:8, duration:0.15, ease:"power2.in" }}, {items[i + 1][2] - 0.16:.2f});\n'
    return html, js


def build_scenes(lines, vo):
    durs = [vo[i] + LEAD + HOLD for i in range(len(vo))]
    durs[1] += 0.6
    durs[-1] = vo[-1] + LEAD + END_HOLD
    at = lambda i, frac: round(LEAD + vo[i] * frac, 2)          # a moment in line i, as a fraction of its clip
    sc = []

    # 1. the opening of the main film, recomposed for vertical
    css1 = """
      #s1-dots { position:absolute; inset:0; background-image:radial-gradient(#E8F1EC 1.4px, transparent 1.6px); background-size:44px 44px; opacity:.10;
        -webkit-mask-image:radial-gradient(520px 760px at 50% 50%, #000 30%, transparent 75%); mask-image:radial-gradient(520px 760px at 50% 50%, #000 30%, transparent 75%); }
      .cloud { position:absolute; border-radius:50%; background:#E8F1EC; filter:blur(60px); opacity:.06; }
      #s1-c0 { left:60px; top:520px; width:420px; height:150px; } #s1-c1 { left:560px; top:1220px; width:460px; height:170px; }
      #s1-trail { position:absolute; left:0; top:0; width:1080px; height:1920px; transform-origin:0 50%; }
      #s1-glow { position:absolute; left:0; top:0; width:240px; height:110px; border-radius:50%; background:#B6F36B; filter:blur(40px); opacity:.18; }
      #s1-plane { position:absolute; left:0; top:0; width:190px; height:95px; }
      #s1-kicker { position:absolute; left:0; right:0; top:820px; text-align:center; }
      #s1-kicker span { display:inline-block; padding:12px 26px; border-radius:999px; background:#E8F1EC; color:#0B1411; font-size:30px; font-weight:800; }
      #s1-line { position:absolute; left:60px; right:60px; top:920px; text-align:center; font-size:104px; line-height:1.08; font-weight:800; letter-spacing:-.03em; }
      #s1-line .hi { color:var(--lime); text-shadow:0 0 40px #B6F36B55; }
    """
    trail = ('<svg id="s1-trail" viewBox="0 0 1080 1920"><defs><linearGradient id="s1-g" x1="0" x2="1"><stop offset="0" stop-color="#B6F36B" stop-opacity="0"/>'
             '<stop offset="1" stop-color="#B6F36B" stop-opacity=".55"/></linearGradient></defs>'
             '<path d="M-60 760 C 260 640, 560 600, 820 610 S 1060 640, 1160 600" fill="none" stroke="url(#s1-g)" stroke-width="2.5"/>'
             '<path d="M-60 774 C 260 654, 560 614, 820 624 S 1060 654, 1160 614" fill="none" stroke="#B6F36B" stroke-opacity=".35" stroke-width="2" stroke-dasharray="2 16" stroke-linecap="round"/></svg>')
    html1 = ('<div id="s1-dots"></div><div class="cloud" id="s1-c0"></div><div class="cloud" id="s1-c1"></div>' + trail
             + f'<div id="s1-glow"></div><div id="s1-plane">{PLANE}</div><div id="s1-kicker"><span>For clinics and solo doctors</span></div>'
             f'<h1 id="s1-line"><span id="s1-l1">{words("Running a clinic shouldn’t feel")}</span><br>'
             f'<span id="s1-l2">{words("like")} <span class="w hi">flying</span> <span class="w hi">a</span> <span class="w hi">plane.</span></span></h1>')
    d = durs[0]
    js1 = ('tl.fromTo("#s1-trail", { scaleX:0.1 }, { scaleX:1, duration:%.2f, ease:"none" }, 0);\n' % (d * 0.9)
           + 'tl.fromTo("#s1-plane", { x:40, y:680, rotation:-10 }, { x:1100, y:560, rotation:2, duration:%.2f, ease:"none" }, 0);\n' % (d * 0.95)
           + 'tl.fromTo("#s1-glow", { x:10, y:670 }, { x:1070, y:550, duration:%.2f, ease:"none" }, 0);\n' % (d * 0.95)
           + 'tl.fromTo("#s1-c0", { x:0 }, { x:90, duration:%.2f, ease:"none" }, 0);\n' % d
           + 'tl.fromTo("#s1-c1", { x:0 }, { x:-100, duration:%.2f, ease:"none" }, 0);\n' % d
           + 'tl.fromTo("#s1-l1 .w", { opacity:1 }, { opacity:1, duration:0.1 }, 0);\n'
           + words_in("#s1-l2 .w", LEAD + 1.0, 0.14))
    sc.append(("s1", durs[0], css1, html1, js1))

    # 2. Dictate, then the whole clinic in four quick beats on the phone
    css2 = """
      #s2-mark { position:absolute; left:0; right:0; top:700px; text-align:center; font-size:170px; font-weight:800; letter-spacing:-.04em; }
      #s2-mark i { color:var(--lime); font-style:normal; }
      #s2-sub { position:absolute; left:80px; right:80px; top:930px; text-align:center; font-size:58px; line-height:1.15; font-weight:700; }
      #s2-sub span { color:var(--lime); }
    """
    t_desk, t_pat, t_con, t_col = at(1, 0.55), at(1, 0.68), at(1, 0.78), at(1, 0.9)
    ch, cj = chapters("s2", [(1, "Front desk", t_desk), (2, "Patients", t_pat), (3, "Consultation", t_con), (4, "Collections", t_col)])
    html2 = ('<div id="s2-mark">Dictate<i>.</i></div><div id="s2-sub">One simple place to run your <span>whole clinic.</span></div>'
             + ch + phone("s2", [("a", "p-ops"), ("b", "p-patient"), ("c", "p-note"), ("d", "p-money")]))
    js2 = ('tl.fromTo("#s2-mark", { opacity:0, scale:1.15, filter:"blur(14px)" }, { opacity:1, scale:1, filter:"blur(0px)", duration:0.6, ease:"expo.out" }, 0.1);\n'
           'tl.fromTo("#s2-sub", { opacity:0, filter:"blur(8px)" }, { opacity:1, filter:"blur(0px)", duration:0.4, ease:"power2.out" }, %.2f);\n' % at(1, 0.2)
           + f'tl.to(["#s2-mark", "#s2-sub"], {{ opacity:0, y:-90, filter:"blur(10px)", duration:0.35, ease:"power3.in" }}, {t_desk - 0.55:.2f});\n'
           + f'tl.fromTo("#s2-ph", {{ y:500, opacity:0 }}, {{ y:0, opacity:1, duration:0.7, ease:"expo.out" }}, {t_desk - 0.35:.2f});\n'
           + cj + swap("s2", "a", "b", t_pat) + swap("s2", "b", "c", t_con) + swap("s2", "c", "d", t_col))
    sc.append(("s2", durs[1], css2, html2, js2))

    # 3. dictate after the visit: the words appear while recording, then the note
    t_rec, t_note = 0.8, at(2, 0.55)
    ch, cj = chapters("s3", [(3, "Dictation", 0.05), (4, "AI note", t_note)])
    html3 = ch + phone("s3", [("a", "p-mic"), ("b", "p-rec1"), ("c", "p-rec2"), ("d", "p-rec3"), ("e", "p-note")])
    js3 = (rise("#s3-ph", 0.0, 0.5) + cj + swap("s3", "a", "b", t_rec) + swap("s3", "b", "c", t_rec + 0.45)
           + swap("s3", "c", "d", t_rec + 0.9) + swap("s3", "d", "e", t_note))
    sc.append(("s3", durs[2], "", html3, js3))

    # 4. built for clinics and solo doctors: tablet and phone together
    css4 = """
      .dev { position:absolute; overflow:hidden; background:#000; box-shadow:0 40px 80px -20px #000, 0 0 0 1px #ffffff1a; border:12px solid #1d2925; }
      .dev img { width:100%; height:100%; object-fit:cover; object-position:top; display:block; }
      #s4-tab { left:90px; top:420px; width:620px; height:893px; border-radius:40px; }
      #s4-pho { left:600px; top:640px; width:390px; height:845px; border-radius:52px; }
    """
    html4 = ('<div class="dev" id="s4-tab"><img src="assets/shots/09c-tablet-brief.jpg"></div>'
             '<div class="dev" id="s4-pho"><img src="assets/shots/p-charts.jpg"></div>')
    js4 = rise("#s4-tab", 0.0) + rise("#s4-pho", 0.35)
    sc.append(("s4", durs[3], css4, html4, js4))

    # 5. end card: the title and its line
    css5 = """
      #s5-mark { position:absolute; left:0; right:0; top:760px; text-align:center; font-size:180px; font-weight:800; letter-spacing:-.04em; }
      #s5-mark i { color:var(--lime); font-style:normal; }
      #s5-line { position:absolute; left:60px; right:60px; top:1000px; text-align:center; font-size:64px; line-height:1.15; font-weight:700; }
      #s5-line .hi { color:var(--lime); }
    """
    html5 = f'<div id="s5-mark">Dictate<i>.</i></div><div id="s5-line">{words("Your whole clinic,")} <span class="w hi">made</span> <span class="w hi">simple.</span></div>'
    js5 = ('tl.fromTo("#s5-mark", { opacity:0, scale:1.12, filter:"blur(14px)" }, { opacity:1, scale:1, filter:"blur(0px)", duration:0.7, ease:"expo.out" }, 0.1);\n'
           + words_in("#s5-line .w", LEAD + 0.5, 0.1))
    sc.append(("s5", durs[4], css5, html5, js5))
    return sc, durs


def caption_groups(lines, starts, vo):
    """3-5 word groups (vertical), timed by character count; the opening and closing lines are already on screen."""
    out = []
    for i, text in enumerate(lines):
        if i in (0, len(lines) - 1):
            continue
        groups, cur = [], []
        for w in text.split():
            cur.append(w)
            if len(cur) >= 5 or (len(cur) >= 3 and re.search(r"[.,:;!?]$", w)):
                groups.append(cur); cur = []
        if cur:
            if groups and len(cur) < 2:
                groups[-1] += cur
            else:
                groups.append(cur)
        total = sum(len(" ".join(g)) for g in groups)
        t = starts[i] + LEAD + 0.05
        for g in groups:
            d = vo[i] * len(" ".join(g)) / total
            out.append((" ".join(g), round(t, 2), round(t + d, 2)))
            t += d
    return out


def mix(starts, vo, total, out):
    """Same mix as the main film: voice on top, the music ducking gently under it, about -16 LUFS."""
    inputs, labels = [], []
    for i in range(len(vo)):
        inputs += ["-i", str(HERE / f"assets/audio/vo-{i + 1}.mp3")]
        ms = int((starts[i] + LEAD) * 1000)
        labels.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[v{i}]")
    n = len(vo)
    graph = (";".join(labels) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={total}[voice];"
             f"[voice]asplit=2[vmix][vkey];"
             f"[{n}:a]aresample=48000,atrim=0:{total},highpass=f=35,afftdn=nf=-30,volume=0.5,afade=t=in:d=1,afade=t=out:st={total - 2.5}:d=2.5[mus];"
             f"[mus][vkey]sidechaincompress=threshold=0.03:ratio=3:attack=150:release=1000:knee=6:makeup=1[duck];"
             f"[vmix][duck]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-i", str(HERE / "assets/audio/music.mp3"), "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-b:a", "192k", str(out)], check=True)


def build():
    lines = [l.split("|", 1)[1].strip() for l in (HERE / "script.txt").read_text().splitlines() if l.strip()]
    vo = [dur(HERE / f"assets/audio/vo-{i + 1}.mp3") for i in range(len(lines))]
    scenes, durs = build_scenes(lines, vo)
    starts, t = [], 0.0
    for d in durs:
        starts.append(round(t, 2)); t += d
    total = round(t, 2)
    for sid, d, css, html, js in scenes:
        (HERE / f"compositions/{sid}.html").write_text(scene(sid, d, css, html, js))

    caps = caption_groups(lines, starts, vo)
    cap_html = "".join(f'<div class="cap" id="cap-{i}"><span>{c}</span></div>' for i, (c, a, b) in enumerate(caps))
    cap_js = "".join(
        f'tl.fromTo("#cap-{i}", {{ opacity:0 }}, {{ opacity:1, duration:0.12, ease:"power2.out" }}, {a:.2f});\n'
        f'tl.to("#cap-{i}", {{ opacity:0, duration:0.12, ease:"power2.in" }}, {b - 0.12:.2f});\n'
        f'tl.set("#cap-{i}", {{ opacity:0, visibility:"hidden" }}, {b:.2f});\n' for i, (c, a, b) in enumerate(caps))
    (HERE / "compositions/captions.html").write_text(f"""<template>
  <style>
    @font-face {{ font-family:'Manrope'; src:url('assets/fonts/manrope-latin.woff2') format('woff2'); font-weight:400 800; }}
    #root {{ position:absolute; inset:0; font-family:'Manrope', sans-serif; }}
    .cap {{ position:absolute; left:60px; right:60px; top:1210px; text-align:center; opacity:0; }}
    .cap span {{ display:inline-block; padding:12px 26px; border-radius:18px; background:#0B1411eb; color:#E8F1EC; font-size:46px; line-height:1.2; font-weight:800; letter-spacing:-.01em; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">{cap_html}</div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {cap_js}
    tl.to({{}}, {{ duration: {total:.2f} }}, 0);
    window.__timelines["captions"] = tl;
  </script>
</template>
""")
    mix(starts, vo, total, HERE / "assets/audio/mix.mp3")
    hosts = "".join(
        f'      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{starts[i]}" '
        f'data-duration="{durs[i]:.2f}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>\n'
        for i, (sid, *_r) in enumerate(scenes))
    wave = "".join(f'<i style="left:{30 + i * 42}px"></i>' for i in range(25))
    wave_js = "".join(f'tl.fromTo("#wave i:nth-child({i + 1})", {{ scaleY:{0.2 + (i * 7 % 10) / 14:.2f} }}, {{ scaleY:{0.2 + (i * 3 % 10) / 14:.2f}, duration:2.4, ease:"sine.inOut", yoyo:true, repeat:{int(total / 2.4)} }}, 0);'
                      for i in range(25))
    (HERE / "index.html").write_text(f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>Dictate: your whole clinic, made simple (vertical)</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      @font-face {{ font-family:'Manrope'; src:url('assets/fonts/manrope-latin.woff2') format('woff2'); font-weight:400 800; }}
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:#0B1411; }}
      #bg {{ position:absolute; inset:0; background:radial-gradient(800px 1200px at 50% 52%, #16241e 0%, #0B1411 70%); overflow:hidden; }}
      #glow {{ position:absolute; left:190px; top:620px; width:700px; height:700px; border-radius:50%; background:#B6F36B; opacity:.07; filter:blur(120px); }}
      #wave {{ position:absolute; left:0; right:0; bottom:0; height:200px; opacity:.10; }}
      #wave i {{ position:absolute; bottom:60px; width:10px; height:120px; border-radius:5px; background:#E8F1EC; transform-origin:50% 100%; }}
      #contact {{ position:absolute; left:0; right:0; top:182px; display:flex; justify-content:center; z-index:50; font-family:'Manrope', sans-serif; }}
      #contact div {{ display:flex; align-items:center; gap:16px; padding:14px 30px 14px 16px; border-radius:999px; background:#E8F1EC; color:#0B1411;
        box-shadow:0 20px 40px -20px #000; }}
      #contact b {{ width:52px; height:52px; border-radius:50%; background:var(--lime, #B6F36B); display:grid; place-items:center; }}
      #contact span {{ font-size:34px; font-weight:800; letter-spacing:.01em; white-space:nowrap; }}
      #contact em {{ font-style:normal; color:#2F6B1E; font-weight:800; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
      <div id="bg"><div id="glow"></div><div id="wave">{wave}</div></div>
{hosts}      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions" data-width="{W}" data-height="{H}"></div>
      <div id="contact"><div><b>{PHONE_ICON}</b><span>{CONTACT[0]} <em>·</em> {CONTACT[1]}</span></div></div>
      <audio id="mix" class="clip" src="assets/audio/mix.mp3" data-start="0" data-duration="{total}" data-track-index="3" data-volume="1"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#glow", {{ x:-120, y:-60 }}, {{ x:120, y:60, duration:{total / 2:.2f}, ease:"sine.inOut", yoyo:true, repeat:1 }}, 0);
      {wave_js}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""")
    (HERE / "timing.json").write_text(json.dumps({"total": total, "scenes": dict(zip([s[0] for s in scenes], starts)), "captions": caps}, indent=1))
    print(f"short: {total} s, {len(scenes)} scenes, {len(caps)} caption groups")


if __name__ == "__main__":
    build()
