"""Writes the main demo film (16:9, ~63 s) as a HyperFrames project in main/: index.html and one file per scene.

    python marketing/video/build_main.py

Timings come from the voice-over clips (main/assets/audio/vo-N.mp3, one per script line in main/script.txt).
Positions of buttons and panels in the captured screens are in BOXES (measured from the real app at 1920x1080).
"""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent / "main"
W, H = 1920, 1080
WIN = dict(x=200, y=112, w=1520, h=855)         # the app window on the canvas (the chapter row sits above it)
S = WIN["w"] / 1920                             # screenshot -> window scale
LEAD, HOLD, END_HOLD = 0.35, 0.9, 3.2           # voice starts LEAD into its scene; scene holds HOLD after it
BOXES = {"ops.walkin": [410, 266, 93, 48], "ops.rows": [286, 734, 1570, 468], "walkin.modal": [650, 65, 620, 524],
         "patient.timeline": [1034, 344, 822, 545], "brief.pane": [378, 218, 1134, 118], "consult.text": [378, 225, 1134, 562],
         "consult.notetab": [539, 171, 64, 36], "note.read": [378, 225, 1134, 846], "note.cite": [419, 385, 15, 15],
         "sources.item": [1637, 251, 244, 60], "signed.dock": [665, 977, 560, 54], "money.panel1": [266, 251, 900, 106],
         "team.list": [266, 251, 1000, 290], "gen": [1167, 112, 138, 41], "mic": [913, 970, 64, 64], "stop": [1177, 981, 42, 42],
         "text.top": [378, 225, 1134, 800], "brief.charts": [1434, 164, 78, 36], "charts.pane": [378, 218, 1134, 525]}
DICTATION = ("Exams are over, she is relaxed and sleeping well. No panic attacks in six weeks. Wants to know how long to continue the tablets. "
             "Calm, euthymic, good insight. Generalised anxiety disorder in remission. Continue sertraline 50 mg once daily for 3 months, "
             "then plan a slow taper. Review in 6 weeks.")
CSS_VARS = "--ground:#0B1411;--ground-2:#121D19;--ink:#E8F1EC;--muted:#8FA39A;--lime:#B6F36B;--amber:#FFB04D"


def dur(path: Path) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


def center(key):
    x, y, w, h = BOXES[key]
    return x + w / 2, y + h / 2


def cam(key, z):
    """Window transform (x, y in px, scale z) that brings a box's centre to the window centre, without empty edges."""
    px, py = center(key)
    x = WIN["w"] / 2 - px * S * z
    y = WIN["h"] / 2 - py * S * z
    x = min(0, max(WIN["w"] - WIN["w"] * z, x))
    y = min(0, max(WIN["h"] - WIN["h"] * z, y))
    return round(x, 1), round(y, 1), z


def on_canvas(key, camera=(0, 0, 1)):
    """Where a box's centre lands on the canvas for a given window transform (for the cursor)."""
    px, py = center(key)
    x, y, z = camera
    return round(WIN["x"] + px * S * z + x, 1), round(WIN["y"] + py * S * z + y, 1)


CURSOR = ('<svg viewBox="0 0 32 32" width="64" height="64"><path d="M6 3 L6 27 L12.5 21 L16.8 30 L21 28.2 L16.8 19.4 L25 19.4 Z" '
          'fill="#FFFFFF" stroke="#0B1411" stroke-width="2" stroke-linejoin="round"/></svg>')


def window(sid, shots):
    """The app window: stacked screenshots (only the first visible), all moved by one camera wrapper."""
    imgs = "".join(f'<img id="{sid}-{n}" class="shot" src="assets/shots/{f}.jpg" style="opacity:{1 if i == 0 else 0}">'
                   for i, (n, f) in enumerate(shots))
    return f'<div id="{sid}-win" class="win"><div id="{sid}-cam" class="cam">{imgs}</div></div>'


BASE_CSS = f"""
#root {{ position:absolute; inset:0; {CSS_VARS}; background:transparent; font-family:'Manrope', sans-serif; color:var(--ink); overflow:hidden; }}
.win {{ position:absolute; left:{WIN['x']}px; top:{WIN['y']}px; width:{WIN['w']}px; height:{WIN['h']}px; border-radius:26px; overflow:hidden;
  box-shadow:0 40px 90px -30px #000, 0 0 0 1px #ffffff14; background:#0B1411; }}
.cam {{ position:absolute; left:0; top:0; width:{WIN['w']}px; height:{WIN['h']}px; transform-origin:0 0; }}
.shot {{ position:absolute; left:0; top:0; width:{WIN['w']}px; height:{WIN['h']}px; }}
.w {{ display:inline-block; }}

.cursor {{ position:absolute; left:0; top:0; width:64px; height:64px; filter:drop-shadow(0 6px 10px #0008); z-index:20; }}
"""


def scene(sid, dur_s, css, html, js):
    return f"""<template>
  <style>
    @font-face {{ font-family:'Manrope'; src:url('assets/fonts/manrope-latin.woff2') format('woff2'); font-weight:400 800; }}
    {BASE_CSS}
    {CHROME_CSS}
    {css}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
    {html}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {js}
    tl.to({{}}, {{ duration: {dur_s:.2f} }}, 0);
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""


def js_cam(sid, camera, t, d=0.6, ease="power2.inOut"):
    x, y, z = camera
    return f'tl.to("#{sid}-cam", {{ x:{x}, y:{y}, scale:{z}, duration:{d}, ease:"{ease}" }}, {t:.2f});\n'


def js_swap(sid, a, b, t):
    """Next state of the UI: a quick blur swap on the same stage."""
    return (f'tl.to("#{sid}-{a}", {{ opacity:0, filter:"blur(6px)", duration:0.16, ease:"power2.in" }}, {t:.2f});\n'
            f'tl.fromTo("#{sid}-{b}", {{ opacity:0, filter:"blur(6px)" }}, {{ opacity:1, filter:"blur(0px)", duration:0.16, ease:"power2.out", immediateRender:false }}, {t:.2f});\n')


def js_cursor(sid, path, t_in):
    """The cursor enters from off-screen, then visits each (x, y, t, click) point; a click is a short press."""
    out = f'tl.fromTo("#{sid}-cursor", {{ x:{W + 80}, y:{H - 120}, opacity:1 }}, {{ x:{path[0][0]}, y:{path[0][1]}, opacity:1, duration:0.7, ease:"power3.out" }}, {t_in:.2f});\n'
    for n, (x, y, t, click) in enumerate(path):
        if n:   # the entry already brought it to the first point
            out += f'tl.to("#{sid}-cursor", {{ x:{x}, y:{y}, duration:0.5, ease:"power2.inOut" }}, {t - 0.6:.2f});\n'
        if click:
            out += (f'tl.to("#{sid}-cursor svg", {{ scale:0.82, duration:0.08, ease:"power2.in", transformOrigin:"20% 10%" }}, {t - 0.08:.2f});\n'
                    f'tl.to("#{sid}-cursor svg", {{ scale:1, duration:0.18, ease:"power2.out" }}, {t:.2f});\n')
    return out


def js_rise(sel, t, d=0.7):
    return f'tl.fromTo("{sel}", {{ y:60, opacity:0, filter:"blur(8px)" }}, {{ y:0, opacity:1, filter:"blur(0px)", duration:{d}, ease:"expo.out" }}, {t:.2f});\n'


def words_in(sel, t, gap=0.08):
    return (f'tl.fromTo("{sel}", {{ opacity:0, filter:"blur(6px)" }}, '
            f'{{ opacity:1, filter:"blur(0px)", duration:0.16, ease:"power2.out", stagger:{gap} }}, {t:.2f});\n')


def words(sid, text, cls=""):
    return " ".join(f'<span class="w {cls}">{w}</span>' for w in text.split())


# ---------------------------------------------------------------- the scenes
# Event times inside a scene were set against the first voice-over; REF holds those clip lengths, and kt() stretches
# a time by how much longer or shorter the current clip is, so clicks stay on their words when the voice changes.
REF = [2.92, 5.18, 6.38, 8.68, 8.35, 7.49, 6.82, 2.60, 3.84, 3.22, 2.41]
ICONS = {
    "ops": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>',
    "patients": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>',
    "consult": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12h4l2-5 4 10 2-5h6"/></svg>',
    "admin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></svg>',
}   # the app's own navigation icons (frontend/js/shared/core.js)
PILLARS = [("ops", "Front desk"), ("patients", "Patients"), ("consult", "Consultation"), ("admin", "Collections")]
CHROME_CSS = """
  .chap { position:absolute; left:200px; top:34px; display:flex; align-items:center; gap:16px; }
  .chap b { width:44px; height:44px; border-radius:12px; background:var(--lime); color:#0B1411; display:grid; place-items:center; font-size:22px; font-weight:800; }
  .chap span { font-size:34px; font-weight:800; letter-spacing:-.01em; }
  .call { position:absolute; right:200px; top:38px; display:flex; align-items:center; gap:12px; padding:10px 20px 10px 14px; border-radius:999px;
    background:#E8F1EC; color:#0B1411; font-size:24px; font-weight:700; opacity:0; }
  .call i { width:12px; height:12px; border-radius:50%; background:#2F6B1E; box-shadow:0 0 0 5px #B6F36B88; }
"""


def chapter(sid, n, title, calls):
    """The chapter title (numbered like the note's sections) and the callouts, shown one after another, top right."""
    html = f'<div class="chap" id="{sid}-chap"><b>{n}</b><span>{title}</span></div>' + \
        "".join(f'<div class="call" id="{sid}-call{i}"><i></i>{c}</div>' for i, (c, _) in enumerate(calls))
    js = 'tl.fromTo("#%s-chap", { opacity:0, x:-30 }, { opacity:1, x:0, duration:0.5, ease:"expo.out" }, 0.05);\n' % sid
    for i, (c, t) in enumerate(calls):
        js += f'tl.fromTo("#{sid}-call{i}", {{ opacity:0, y:-14 }}, {{ opacity:1, y:0, duration:0.35, ease:"expo.out", immediateRender:false }}, {t:.2f});\n'
        if i + 1 < len(calls):
            js += f'tl.to("#{sid}-call{i}", {{ opacity:0, y:-10, duration:0.2, ease:"power2.in" }}, {calls[i + 1][1] - 0.22:.2f});\n'
    return html, js


def build_scenes(lines, vo):
    kt = lambda i, x: round(x * vo[i] / REF[i], 2)
    durs = [vo[i] + LEAD + HOLD for i in range(len(vo))]
    durs[-1] = vo[-1] + LEAD + END_HOLD
    durs[4] += 1.6   # history: the brief, then its charts
    durs[5] += 1.5   # dictation: time for the words to appear at a speaking pace
    sc = []

    # 1. hook: a plane glides across on a dashed flight path while the line builds
    PLANE = ('<svg viewBox="0 0 120 60" width="210" height="105" fill="none" stroke="#B6F36B" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">'
             '<path d="M6 34 C 20 30, 70 28, 104 27 C 114 27, 118 31, 112 35 C 100 40, 40 42, 14 40 Z"/>'
             '<path d="M50 30 L 34 10 L 44 10 L 70 29"/><path d="M52 39 L 40 54 L 49 54 L 70 39"/>'
             '<path d="M10 33 L 4 20 L 12 20 L 22 31"/><circle cx="96" cy="30" r="1.6" fill="#B6F36B"/><circle cx="88" cy="30" r="1.6" fill="#B6F36B"/>'
             '<circle cx="80" cy="30" r="1.6" fill="#B6F36B"/></svg>')
    css1 = """
      #s1-dots { position:absolute; inset:0; background-image:radial-gradient(#E8F1EC 1.4px, transparent 1.6px); background-size:44px 44px; opacity:.10;
        -webkit-mask-image:radial-gradient(900px 520px at 50% 48%, #000 30%, transparent 75%); mask-image:radial-gradient(900px 520px at 50% 48%, #000 30%, transparent 75%); }
      .cloud { position:absolute; border-radius:50%; background:#E8F1EC; filter:blur(60px); opacity:.06; }
      #s1-c0 { left:180px; top:120px; width:520px; height:170px; } #s1-c1 { left:1180px; top:240px; width:620px; height:200px; }
      #s1-glow { position:absolute; left:0; top:0; width:260px; height:120px; border-radius:50%; background:#B6F36B; filter:blur(40px); opacity:.18; }
      #s1-path { position:absolute; left:0; top:0; width:1920px; height:1080px; }
      #s1-trail { position:absolute; left:0; top:0; width:1920px; height:1080px; transform-origin:0 50%; }
      #s1-plane { position:absolute; left:0; top:0; width:210px; height:105px; }
      #s1-kicker { position:absolute; left:0; right:0; top:330px; text-align:center; }
      #s1-kicker span { display:inline-block; padding:10px 22px; border-radius:999px; background:#E8F1EC; color:#0B1411; font-size:24px; font-weight:800; letter-spacing:.02em; }
      #s1-line { position:absolute; left:0; right:0; top:430px; text-align:center; font-size:96px; line-height:1.12; font-weight:800; letter-spacing:-.03em; }
      #s1-line .hi { color:var(--lime); text-shadow:0 0 40px #B6F36B55; }
    """
    trail = ('<svg id="s1-trail" viewBox="0 0 1920 1080"><defs><linearGradient id="s1-g" x1="0" x2="1"><stop offset="0" stop-color="#B6F36B" stop-opacity="0"/>'
             '<stop offset="1" stop-color="#B6F36B" stop-opacity=".55"/></linearGradient></defs>'
             '<path d="M-40 300 C 420 220, 900 180, 1320 210 S 1900 260, 2000 230" fill="none" stroke="url(#s1-g)" stroke-width="2.5"/>'
             '<path d="M-40 312 C 420 232, 900 192, 1320 222 S 1900 272, 2000 242" fill="none" stroke="#B6F36B" stroke-opacity=".35" stroke-width="2" stroke-dasharray="2 16" stroke-linecap="round"/></svg>')
    html1 = ('<div id="s1-dots"></div><div class="cloud" id="s1-c0"></div><div class="cloud" id="s1-c1"></div>' + trail
             + f'<div id="s1-glow"></div><div id="s1-plane">{PLANE}</div><div id="s1-kicker"><span>For clinics and solo doctors</span></div>'
             f'<h1 id="s1-line"><span id="s1-l1">{words("s1", "Running a clinic shouldn’t feel")}</span><br>'
             f'<span id="s1-l2">{words("s1", "like")} <span class="w hi">flying</span> <span class="w hi">a</span> <span class="w hi">plane.</span></span></h1>')
    d1 = durs[0]
    js1 = ('tl.fromTo("#s1-trail", { scaleX:0.08 }, { scaleX:1, duration:%.2f, ease:"none" }, 0);\n' % (d1 * 0.9)
           + 'tl.fromTo("#s1-plane", { x:60, y:220, rotation:-6 }, { x:1960, y:150, rotation:2, duration:%.2f, ease:"none" }, 0);\n' % (d1 * 0.95)
           + 'tl.fromTo("#s1-glow", { x:30, y:210 }, { x:1930, y:140, duration:%.2f, ease:"none" }, 0);\n' % (d1 * 0.95)
           + 'tl.fromTo("#s1-c0", { x:0 }, { x:120, duration:%.2f, ease:"none" }, 0);\n' % d1
           + 'tl.fromTo("#s1-c1", { x:0 }, { x:-140, duration:%.2f, ease:"none" }, 0);\n' % d1
           + 'tl.fromTo("#s1-kicker span", { opacity:1 }, { opacity:1, duration:0.1 }, 0);\n'
           + 'tl.fromTo("#s1-l1 .w", { opacity:1 }, { opacity:1, duration:0.1 }, 0);\n'
           + words_in("#s1-l2 .w", LEAD + 1.0, 0.14))
    sc.append(("s1", durs[0], css1, html1, js1))

    # 2. the problem: three cards rise, each acting out its words (windows pile up, steps climb, a bar crawls)
    css2 = """
      #s2-lead { position:absolute; left:0; right:0; top:190px; text-align:center; font-size:40px; font-weight:600; color:var(--muted); }
      .pc { position:absolute; top:300px; width:500px; height:470px; border-radius:30px; background:#121D19; box-shadow:0 40px 80px -30px #000, inset 0 0 0 1px #ffffff14;
        padding:40px; display:flex; flex-direction:column; justify-content:space-between; }
      #s2-k0 { left:170px; } #s2-k1 { left:710px; } #s2-k2 { left:1250px; }
      .pc .art { position:relative; height:200px; }
      .pc h2 { font-size:54px; line-height:1.05; font-weight:800; letter-spacing:-.02em; }
      .pc h2 em { font-style:normal; color:var(--amber); }
      .win2 { position:absolute; width:220px; height:140px; border-radius:14px; background:#1F2C27; box-shadow:0 14px 26px -12px #000, inset 0 0 0 1px #ffffff1c; }
      .win2::before { content:""; position:absolute; left:14px; top:14px; width:60px; height:8px; border-radius:4px; background:#FFB04D; opacity:.8; }
      .step { position:absolute; bottom:0; width:70px; border-radius:10px 10px 0 0; background:#1F2C27; box-shadow:inset 0 0 0 1px #ffffff1c; }
      .step.on { background:#FFB04D; }
      .bar { position:absolute; left:0; right:0; top:80px; height:26px; border-radius:13px; background:#1F2C27; box-shadow:inset 0 0 0 1px #ffffff1c; overflow:hidden; }
      .bar i { position:absolute; left:0; top:0; bottom:0; width:100%; border-radius:13px; background:#FFB04D; transform-origin:0 50%; }
      .pct { position:absolute; left:0; top:130px; font-size:30px; font-weight:800; color:var(--amber); }
    """
    wins = "".join(f'<div class="win2" id="s2-w{i}" style="left:{20 + i * 34}px;top:{10 + i * 22}px"></div>' for i in range(5))
    steps = "".join(f'<div class="step" id="s2-s{i}" style="left:{i * 80}px;height:{40 + i * 36}px"></div>' for i in range(5))
    cards = [("s2-k0", wins, "Too many<br><em>screens.</em>"), ("s2-k1", steps, "Too many<br><em>steps.</em>"),
             ("s2-k2", '<div class="bar"><i id="s2-bar"></i></div><div class="pct" id="s2-pct">Week 1 of 6</div>', "Too much<br><em>training.</em>")]
    html2 = '<div id="s2-lead">Most clinic software comes with…</div>' + "".join(f'<div class="pc" id="{c}"><div class="art">{a}</div><h2>{t}</h2></div>' for c, a, t in cards)
    js2 = 'tl.fromTo("#s2-lead", { opacity:0, filter:"blur(8px)" }, { opacity:1, filter:"blur(0px)", duration:0.4, ease:"power2.out" }, 0.25);\n'
    ts = (kt(1, LEAD + 2.1) - 0.4, kt(1, LEAD + 3.1) - 0.4, kt(1, LEAD + 4.1) - 0.4)
    for i, t in enumerate(ts):
        js2 += f'tl.fromTo("#s2-k{i}", {{ opacity:0, y:120, scale:0.92 }}, {{ opacity:1, y:0, scale:1, duration:0.6, ease:"expo.out" }}, {t:.2f});\n'
    js2 += 'tl.fromTo("#s2-k0 .win2", { opacity:0, y:30, scale:0.8 }, { opacity:1, y:0, scale:1, duration:0.35, ease:"back.out(1.6)", stagger:0.16 }, %.2f);\n' % (ts[0] + 0.3)
    js2 += 'tl.fromTo("#s2-k1 .step", { scaleY:0, transformOrigin:"50%% 100%%" }, { scaleY:1, duration:0.3, ease:"power3.out", stagger:0.14 }, %.2f);\n' % (ts[1] + 0.3)
    js2 += 'tl.to("#s2-k1 .step", { backgroundColor:"#FFB04D", duration:0.15, stagger:0.14 }, %.2f);\n' % (ts[1] + 0.9)
    js2 += 'tl.fromTo("#s2-bar", { scaleX:0 }, { scaleX:0.16, duration:%.2f, ease:"power1.inOut" }, %.2f);\n' % (max(1.0, durs[1] - ts[2] - 0.6), ts[2] + 0.3)
    sc.append(("s2", durs[1], css2, html2, js2))

    # 3. Dictate: the wordmark and the four parts of the clinic, then the app itself
    css3 = """
      #s3-sub { position:absolute; left:0; right:0; top:560px; text-align:center; font-size:52px; font-weight:700; letter-spacing:-.01em; }
      #s3-sub span { color:var(--lime); }
      #s3-mark { position:absolute; left:0; right:0; top:330px; text-align:center; font-size:150px; font-weight:800; letter-spacing:-.04em; }
      #s3-mark i { color:var(--lime); font-style:normal; }
      .pills { position:absolute; left:0; right:0; top:500px; display:flex; justify-content:center; gap:26px; }
      .pill { width:330px; padding:30px 28px; border-radius:26px; background:#E8F1EC; color:#0B1411; display:flex; flex-direction:column; gap:18px; }
      .pill b { width:64px; height:64px; border-radius:16px; background:#0B1411; color:var(--lime); display:grid; place-items:center; }
      .pill b svg { width:34px; height:34px; }
      .pill span { font-size:34px; font-weight:800; letter-spacing:-.01em; }
    """
    html3 = (f'<div id="s3-mark" data-layout-allow-overflow>Dictate<i>.</i></div>'
             f'<div id="s3-sub">One simple place to run your <span>whole clinic.</span></div>' + window("s3", [("a", "03-home")]))
    js3 = 'tl.fromTo("#s3-mark", { opacity:0, scale:1.15, filter:"blur(14px)" }, { opacity:1, scale:1, filter:"blur(0px)", duration:0.6, ease:"expo.out" }, 0.1);\n'
    js3 += f'tl.fromTo("#s3-sub", {{ opacity:0, filter:"blur(8px)" }}, {{ opacity:1, filter:"blur(0px)", duration:0.4, ease:"power2.out" }}, {kt(2, 1.4):.2f});\n'
    js3 += (f'tl.to(["#s3-mark", "#s3-sub"], {{ opacity:0, y:-80, filter:"blur(10px)", duration:0.35, ease:"power3.in" }}, {kt(2, 4.4):.2f});\n'
            f'tl.fromTo("#s3-win", {{ y:300, opacity:0, scale:0.9 }}, {{ y:0, opacity:1, scale:1, duration:0.8, ease:"expo.out" }}, {kt(2, 4.55):.2f});\n')
    sc.append(("s3", durs[2], css3, html3, js3))

    # 4. front desk: Walk-in -> token and payment -> the day's queue
    k = lambda x: kt(3, x)
    c_modal, c_rows = cam("walkin.modal", 1.45), cam("ops.rows", 1.3)
    wx, wy = on_canvas("ops.walkin")
    ch, cj = chapter("s4", 1, "Front desk", [("Token and payment in one step", k(2.2)), ("Today’s queue at a glance", k(6.3))])
    html4 = ch + window("s4", [("a", "04a-ops"), ("b", "04b-walkin")]) + f'<div id="s4-cursor" class="cursor" style="opacity:0">{CURSOR}</div>'
    js4 = (cj + js_rise("#s4-win", 0.0, 0.6) + js_cursor("s4", [(wx, wy, k(2.0), True)], k(0.9)) + js_swap("s4", "a", "b", k(2.0))
           + f'tl.to("#s4-cursor", {{ opacity:0, duration:0.2 }}, {k(2.3)});\n' + js_cam("s4", c_modal, k(2.2), 0.6)
           + js_swap("s4", "b", "a", k(5.6)) + js_cam("s4", (0, 0, 1), k(5.5), 0.5) + js_cam("s4", c_rows, k(6.3), 0.6))
    sc.append(("s4", durs[3], "", html4, js4))

    # 5. history: visit history, the brief, its charts
    k = lambda x: kt(4, x)
    chx, chy = on_canvas("brief.charts")
    ch, cj = chapter("s5", 2, "Patient history", [("Every visit, in order", 0.5), ("A brief before every visit", k(3.2)), ("Lithium, creatinine and TSH over time", k(5.9) + 0.4)])
    html5 = ch + window("s5", [("a", "05a-patient"), ("b", "05b-brief"), ("c", "05d-charts")]) + f'<div id="s5-cursor" class="cursor" style="opacity:0">{CURSOR}</div>'
    js5 = (cj + js_rise("#s5-win", 0.0, 0.5) + js_cam("s5", cam("patient.timeline", 1.4), 0.5, 0.7)
           + js_cam("s5", (0, 0, 1), k(2.9), 0.45) + js_swap("s5", "a", "b", k(3.2)) + js_cam("s5", cam("brief.pane", 1.6), k(3.4), 0.6)
           + js_cam("s5", (0, 0, 1), k(5.0), 0.45) + js_cursor("s5", [(chx, chy, k(5.9), True)], k(4.9)) + js_swap("s5", "b", "c", k(5.9))
           + f'tl.to("#s5-cursor", {{ opacity:0, duration:0.2 }}, {k(6.2)});\n' + js_cam("s5", cam("charts.pane", 1.35), k(6.2), 0.7))
    sc.append(("s5", durs[4], "", html5, js5))

    # 6. dictation: tap the mic, the words appear as the doctor speaks, stop
    T0, T1 = kt(5, 4.1), kt(5, 4.1) + 5.1               # recording: the mic tap on "tap the mic", then the stop tap
    words_d = DICTATION.split()
    mx, my = on_canvas("mic")
    c_type = cam("text.top", 1.15)
    stx, sty = on_canvas("stop")
    tx, ty, tw, th = (round(v * S, 1) for v in BOXES["consult.text"])
    bars = "".join(f'<i id="s6-b{i}" style="left:{round((731 + i * 17.9) * S, 1)}px"></i>' for i in range(20))
    css6 = f"""
      #s6-live {{ position:absolute; inset:0; opacity:0; }}
      #s6-paper {{ position:absolute; left:{tx}px; top:{ty - 6}px; width:{tw}px; height:{round(40 * S, 1)}px; background:#E8F1EC; opacity:0; }}
      #s6-text {{ position:absolute; left:{tx}px; top:{ty}px; width:{tw}px; font-family:'Manrope', sans-serif; font-size:{round(16 * S, 2)}px;
        line-height:{round(25.6 * S, 2)}px; font-weight:450; color:#0B1411; }}
      #s6-text span {{ opacity:0; }}
      #s6-wave {{ position:absolute; left:{round(722 * S, 1)}px; top:{round(985 * S, 1)}px; width:{round(358 * S, 1)}px; height:{round(32 * S, 1)}px; background:#0B1411; }}
      #s6-wave i {{ position:absolute; top:{round(4 * S, 1)}px; width:{round(3 * S, 1)}px; height:{round(24 * S, 1)}px; border-radius:2px; background:#FF7A59; margin-left:-{round(722 * S, 1)}px; transform-origin:50% 50%; }}
      #s6-clock {{ position:absolute; left:{round(1083 * S, 1)}px; top:{round(990 * S, 1)}px; width:{round(42 * S, 1)}px; height:{round(24 * S, 1)}px; background:#0B1411;
        color:#E8F1EC; font-family:'Manrope', sans-serif; font-size:{round(13 * S, 1)}px; font-weight:600; line-height:{round(24 * S, 1)}px; text-align:center; }}
    """
    live = (f'<div id="s6-live"><div id="s6-paper"></div><div id="s6-text">{" ".join(f"<span>{w}</span>" for w in words_d)}</div>'
            f'<div id="s6-wave">{bars}</div><div id="s6-clock">0:00</div></div>')
    ch, cj = chapter("s6", 3, "Dictation", [("After the visit, tap the mic", T0 - 1.2), ("Your words appear as you speak", T0 + 0.6)])
    html6 = ch + window("s6", [("a", "06e-mic"), ("b", "06f-rec"), ("c", "06a-consult")]).replace('</div></div>', live + '</div></div>', 1) + \
        f'<div id="s6-cursor" class="cursor" style="opacity:0">{CURSOR}</div>'
    js6 = (cj + js_rise("#s6-win", 0.0, 0.5) + js_cursor("s6", [(mx, my, T0, True)], T0 - 1.5) + js_swap("s6", "a", "b", T0)
           + f'tl.to("#s6-live", {{ opacity:1, duration:0.12 }}, {T0:.2f});\n'
           + f'tl.to("#s6-cursor", {{ opacity:0, duration:0.2 }}, {T0 + 0.3:.2f});\n'
           + js_cam("s6", c_type, T0 + 0.2, 0.6)
           + f'tl.to("#s6-paper", {{ opacity:1, duration:0.05 }}, {T0 + 0.5:.2f});\n'
           + f'tl.to("#s6-text span", {{ opacity:1, duration:0.06, stagger:{(T1 - T0 - 1.3) / len(words_d):.3f} }}, {T0 + 0.5:.2f});\n')
    for kk in range(int((T1 - T0) / 0.3)):           # the waveform: deterministic heights, a new set every 0.3 s
        t = T0 + kk * 0.3
        hs = [0.25 + ((i * 7 + kk * 13) % 10) / 11 for i in range(20)]
        js6 += "".join(f'tl.to("#s6-b{i}", {{ scaleY:{h:.2f}, duration:0.25, ease:"sine.inOut" }}, {t:.2f});\n' for i, h in enumerate(hs))
    for sec in range(1, int(T1 - T0) + 1):
        js6 += f'tl.set("#s6-clock", {{ textContent:"0:{sec:02d}" }}, {T0 + sec:.2f});\n'
    js6 += (js_cam("s6", (0, 0, 1), T1 - 0.9, 0.5)
            + f'tl.to("#s6-cursor", {{ x:{stx}, y:{sty}, opacity:1, duration:0.5, ease:"power2.inOut" }}, {T1 - 0.6:.2f});\n'
            + f'tl.to("#s6-cursor svg", {{ scale:0.82, duration:0.08, ease:"power2.in", transformOrigin:"20% 10%" }}, {T1 - 0.08:.2f});\n'
            + f'tl.to("#s6-cursor svg", {{ scale:1, duration:0.18, ease:"power2.out" }}, {T1:.2f});\n'
            + js_swap("s6", "b", "c", T1) + f'tl.to("#s6-live", {{ opacity:0, duration:0.16 }}, {T1:.2f});\n'
            + f'tl.to("#s6-cursor", {{ opacity:0, duration:0.2 }}, {T1 + 0.5:.2f});\n')
    sc.append(("s6", max(durs[5], T1 + 1.0), css6, html6, js6))
    durs[5] = max(durs[5], T1 + 1.0)

    # 7. Generate note -> the note -> a citation -> its source -> the exact words
    k = lambda x: kt(6, x)
    c_text = cam("consult.text", 1.3)
    gx, gy = on_canvas("gen")
    cx_, cy_ = on_canvas("note.cite")
    sx, sy = on_canvas("sources.item")
    ch, cj = chapter("s7", 4, "AI note", [("Written in the psychiatry case-sheet format", k(1.0) + 0.3), ("Tap a line to see its source", k(4.6)), ("Back to the exact words", k(6.3))])
    html7 = ch + window("s7", [("a", "06a-consult"), ("b", "06b-note"), ("c", "06c-sources"), ("d", "06d-highlight")]) + \
        f'<div id="s7-cursor" class="cursor" style="opacity:0">{CURSOR}</div>'
    js7 = (cj + js_cursor("s7", [(gx, gy, k(1.0), True), (cx_, cy_, k(4.6), True), (sx, sy, k(6.3), True)], 0.1)
           + js_swap("s7", "a", "b", k(1.0)) + js_swap("s7", "b", "c", k(4.6)) + js_swap("s7", "c", "d", k(6.3))
           + js_cam("s7", c_text, k(6.6), 0.6) + f'tl.to("#s7-cursor", {{ opacity:0, duration:0.2 }}, {k(6.6)});\n')
    sc.append(("s7", durs[6], "", html7, js7))

    # 8. sign and print
    k = lambda x: kt(7, x)
    css8 = """
      #s8-paper { position:absolute; left:500px; top:120px; width:920px; height:860px; border-radius:20px; overflow:hidden; box-shadow:0 40px 90px -20px #000; }
      #s8-paper img { position:absolute; left:-500px; top:-30px; width:1920px; height:1080px; }
    """
    ch, cj = chapter("s8", 5, "Sign and print", [("Signed, dated, ready to print", 0.3)])
    html8 = ch + window("s8", [("a", "07a-signed")]) + '<div id="s8-paper"><img src="assets/shots/07b-print.jpg"></div>'
    js8 = (cj + js_rise("#s8-win", 0.0, 0.4) + js_cam("s8", cam("signed.dock", 1.5), 0.2, 0.5)
           + f'tl.fromTo("#s8-paper", {{ y:1100 }}, {{ y:0, duration:0.6, ease:"expo.out" }}, {k(1.5)});\n')
    sc.append(("s8", durs[7], css8, html8, js8))

    # 9. collections, then the team
    k = lambda x: kt(8, x)
    ch, cj = chapter("s9", 6, "Clinic admin", [("Collections by cash, UPI and card", 0.3), ("Staff attendance and leave", k(2.3))])
    html9 = ch + window("s9", [("a", "08a-collections"), ("b", "08b-team")])
    js9 = (cj + js_rise("#s9-win", 0.0, 0.5) + js_cam("s9", cam("money.panel1", 1.35), 0.3, 0.6)
           + js_cam("s9", (0, 0, 1), k(2.1), 0.4) + js_swap("s9", "a", "b", k(2.3)) + js_cam("s9", cam("team.list", 1.25), k(2.6), 0.6))
    sc.append(("s9", durs[8], "", html9, js9))

    # 10. laptop, tablet and phone
    css10 = """
      .dev { position:absolute; overflow:hidden; background:#000; box-shadow:0 40px 80px -20px #000, 0 0 0 1px #ffffff1a; }
      .dev img { width:100%; height:100%; object-fit:cover; object-position:top; display:block; }
      #s10-lap { left:150px; top:210px; width:1060px; height:596px; border-radius:22px; border:10px solid #1d2925; }
      #s10-tab { left:1150px; top:170px; width:450px; height:648px; border-radius:30px; border:12px solid #1d2925; }
      #s10-pho { left:1530px; top:320px; width:270px; height:584px; border-radius:40px; border:10px solid #1d2925; }
    """
    ch, cj = chapter("s10", 7, "Any device", [("Laptop · tablet · phone", 0.6)])
    html10 = ch + ('<div class="dev" id="s10-lap"><img src="assets/shots/03-home.jpg"></div>'
                   '<div class="dev" id="s10-tab"><img src="assets/shots/09c-tablet-brief.jpg"></div>'
                   '<div class="dev" id="s10-pho"><img src="assets/shots/09a-phone-note.jpg"></div>')
    js10 = cj + js_rise("#s10-lap", 0.2) + js_rise("#s10-tab", 0.6) + js_rise("#s10-pho", 1.0)
    sc.append(("s10", durs[9], css10, html10, js10))

    # 11. end card: the mark, the line, the four parts, who it is for
    css11 = """
      #s11-mark { position:absolute; left:0; right:0; top:330px; text-align:center; font-size:170px; font-weight:800; letter-spacing:-.04em; }
      #s11-mark i { color:var(--lime); font-style:normal; }
      #s11-line { position:absolute; left:0; right:0; top:570px; text-align:center; font-size:58px; font-weight:700; }
      #s11-line .hi { color:var(--lime); }
      .row { position:absolute; left:0; right:0; top:640px; display:flex; justify-content:center; gap:18px; }
      .chipx { display:flex; align-items:center; gap:12px; padding:14px 24px 14px 16px; border-radius:999px; background:#E8F1EC; color:#0B1411; font-size:26px; font-weight:800; }
      .chipx svg { width:26px; height:26px; }
      #s11-for { position:absolute; left:0; right:0; top:780px; text-align:center; font-size:30px; font-weight:600; color:var(--muted); }
    """
    html11 = (f'<div id="s11-mark">Dictate<i>.</i></div><div id="s11-line">{words("s11", "Your whole clinic,")} <span class="w hi">made</span> <span class="w hi">simple.</span></div>'
              )
    js11 = ('tl.fromTo("#s11-mark", { opacity:0, scale:1.12, filter:"blur(14px)" }, { opacity:1, scale:1, filter:"blur(0px)", duration:0.7, ease:"expo.out" }, 0.1);\n'
            + words_in("#s11-line .w", LEAD + 0.5, 0.1)
            )
    sc.append(("s11", durs[10], css11, html11, js11))
    return sc, durs


# ---------------------------------------------------------------- captions
def caption_groups(lines, starts, vo):
    """4-6 word groups, timed across each voice clip by character count (there is no word-level timing)."""
    out = []
    for i, text in enumerate(lines):
        if i in (0, len(lines) - 1):   # the opening line and the end card already say it on screen
            continue
        ws = text.split()
        groups, cur = [], []
        for w in ws:
            cur.append(w)
            if len(cur) >= 6 or (len(cur) >= 3 and re.search(r"[.,:;!?]$", w)):
                groups.append(cur); cur = []
        if cur:
            if groups and len(cur) < 3:
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


MUSIC = HERE / "assets/audio/music.mp3"   # the chosen track (the person's own, from Pixabay)


def mix(starts, vo, total, out):
    """One audio file: the voice lines at their times, the music under them. The music ducks while the voice speaks
    (sidechain, slow and gentle so it glides rather than pumps) and rises in the gaps; the voice always sits on top.
    The track is a WhatsApp-compressed file, so a light high-pass and noise reduction take out its hiss. Loudness normalised for social (-16 LUFS)."""
    inputs, labels = [], []
    for i in range(len(vo)):
        inputs += ["-i", str(HERE / f"assets/audio/vo-{i + 1}.mp3")]
        ms = int((starts[i] + LEAD) * 1000)
        labels.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[v{i}]")
    n = len(vo)
    graph = (";".join(labels) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={total}[voice];"
             f"[voice]asplit=2[vmix][vkey];"
             f"[{n}:a]aresample=48000,atrim=0:{total},highpass=f=35,afftdn=nf=-30,volume=0.5,afade=t=in:d=1.5,afade=t=out:st={total - 3}:d=3[mus];"
             f"[mus][vkey]sidechaincompress=threshold=0.03:ratio=3:attack=150:release=1000:knee=6:makeup=1[duck];"
             f"[vmix][duck]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-i", str(MUSIC), "-filter_complex", graph, "-map", "[out]",
                    "-ar", "48000", "-b:a", "192k", str(out)], check=True)


def build():
    lines = [l.split("|", 1)[1].strip() for l in (HERE / "script.txt").read_text().splitlines() if l.strip()]
    vo = [dur(HERE / f"assets/audio/vo-{i + 1}.mp3") for i in range(len(lines))]
    scenes, durs = build_scenes(lines, vo)
    starts, t = [], 0.0
    for d in durs:
        starts.append(round(t, 2)); t += d
    total = round(t, 2)
    (HERE / "compositions").mkdir(exist_ok=True)
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
    .cap {{ position:absolute; left:0; right:0; bottom:22px; text-align:center; opacity:0; }}
    .cap span {{ display:inline-block; padding:8px 22px; border-radius:14px; background:#0B1411e6; color:#E8F1EC; font-size:36px; font-weight:700; letter-spacing:-.01em; }}
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

    hosts = "".join(
        f'      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{starts[i]}" '
        f'data-duration="{durs[i]:.2f}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>\n'
        for i, (sid, *_r) in enumerate(scenes))
    mix(starts, vo, total, HERE / "assets/audio/mix.mp3")
    wave = "".join(f'<i style="left:{40 + i * 46}px"></i>' for i in range(40))
    wave_js = "".join(f'tl.fromTo("#wave i:nth-child({i + 1})", {{ scaleY:{0.2 + (i * 7 % 10) / 14:.2f} }}, {{ scaleY:{0.2 + (i * 3 % 10) / 14:.2f}, duration:2.4, ease:"sine.inOut", yoyo:true, repeat:{int(total / 2.4)} }}, 0);'
                      for i in range(40))
    (HERE / "index.html").write_text(f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>Dictate: your whole clinic, made simple</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:#0B1411; }}
      #bg {{ position:absolute; inset:0; background:radial-gradient(1200px 700px at 50% 55%, #16241e 0%, #0B1411 70%); overflow:hidden; }}
      #glow {{ position:absolute; left:560px; top:240px; width:800px; height:600px; border-radius:50%; background:#B6F36B; opacity:.07; filter:blur(120px); }}
      #wave {{ position:absolute; left:0; right:0; bottom:0; height:180px; opacity:.10; }}
      #wave i {{ position:absolute; bottom:40px; width:10px; height:120px; border-radius:5px; background:#E8F1EC; transform-origin:50% 100%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
      <div id="bg"><div id="glow"></div><div id="wave">{wave}</div></div>
{hosts}      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions" data-width="{W}" data-height="{H}"></div>
      <audio id="mix" class="clip" src="assets/audio/mix.mp3" data-start="0" data-duration="{total}" data-track-index="3" data-volume="1"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      // the background breathes slowly: the glow drifts and the waveform (the app's login motif) moves
      tl.fromTo("#glow", {{ x:-160, y:-30 }}, {{ x:160, y:30, duration:{total / 2:.2f}, ease:"sine.inOut", yoyo:true, repeat:1 }}, 0);
      {wave_js}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""")
    (HERE / "timing.json").write_text(json.dumps({"total": total, "scenes": dict(zip([s[0] for s in scenes], starts)), "captions": caps}, indent=1))
    print(f"main: {total} s, {len(scenes)} scenes, {len(caps)} caption groups")


if __name__ == "__main__":
    build()
