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
WIN = dict(x=160, y=34, w=1600, h=900)          # the app window on the canvas
S = WIN["w"] / 1920                             # screenshot -> window scale
LEAD, HOLD, END_HOLD = 0.35, 0.9, 3.2           # voice starts LEAD into its scene; scene holds HOLD after it
BOXES = {"ops.walkin": [410, 266, 93, 48], "ops.rows": [286, 734, 1570, 468], "walkin.modal": [650, 65, 620, 524],
         "patient.timeline": [1034, 344, 822, 545], "brief.pane": [378, 218, 1134, 118], "consult.text": [378, 225, 1134, 562],
         "consult.notetab": [539, 171, 64, 36], "note.read": [378, 225, 1134, 846], "note.cite": [419, 385, 15, 15],
         "sources.item": [1637, 251, 244, 60], "signed.dock": [665, 977, 560, 54], "money.panel1": [266, 251, 900, 106],
         "team.list": [266, 251, 1000, 290], "gen": [1167, 112, 138, 41], "mic": [913, 970, 64, 64], "stop": [1177, 981, 42, 42],
         "text.top": [378, 225, 1134, 800]}
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
#root {{ position:absolute; inset:0; {CSS_VARS}; background:var(--ground); font-family:'Manrope', sans-serif; color:var(--ink); overflow:hidden; }}
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
def build_scenes(lines, vo):
    durs = [vo[i] + LEAD + HOLD for i in range(len(vo))]
    durs[-1] = vo[-1] + LEAD + END_HOLD
    durs[5] += 1.5   # dictation: time for the words to appear at a speaking pace
    sc = []

    # 1. hook: a cockpit of switches and lights, then the line
    cells = []
    for i in range(96):
        kind = ("led", "knob", "toggle", "gauge")[(i * 7 + i // 12) % 4]
        cells.append(f'<div class="cell {kind}"><i></i></div>')
    css1 = """
      .panel { position:absolute; inset:60px 120px 230px; display:grid; grid-template-columns:repeat(16,1fr); gap:14px; opacity:.9; }
      .cell { border-radius:12px; background:var(--ground-2); box-shadow:inset 0 0 0 1px #ffffff10; position:relative; height:84px; }
      .cell i { position:absolute; inset:0; margin:auto; display:block; }
      .led i { width:16px; height:16px; border-radius:50%; background:#2a3a33; }
      .knob i { width:44px; height:44px; border-radius:50%; background:radial-gradient(circle at 35% 35%, #3b4d45, #16211d); box-shadow:0 0 0 2px #ffffff14; }
      .toggle i { width:18px; height:46px; border-radius:9px; background:#26332e; box-shadow:inset 0 -18px 0 #8FA39A; }
      .gauge i { width:52px; height:30px; border-radius:52px 52px 0 0; border:3px solid #33433d; border-bottom:0; }
      .lit i { background:var(--lime) !important; box-shadow:0 0 14px var(--lime); }
      .warn i { background:var(--amber) !important; box-shadow:0 0 14px var(--amber); }
      #s1-line { position:absolute; left:0; right:0; bottom:120px; text-align:center; font-size:74px; font-weight:800; letter-spacing:-.02em; }
      #s1-line .hi { color:var(--lime); }
      #s1-shade { position:absolute; inset:0; background:linear-gradient(180deg, transparent 40%, #0B1411 82%); }
    """
    for i in range(96):
        if (i * 13) % 5 == 0:
            cells[i] = cells[i].replace('class="cell led"', 'class="cell led lit"' if i % 3 else 'class="cell led warn"')
    html1 = f'<div class="panel" id="s1-panel">{"".join(cells)}</div><div id="s1-shade"></div>' \
            f'<h1 id="s1-line">{words("s1", "Running a clinic shouldn’t feel like")} <span class="w hi">flying</span> <span class="w hi">a</span> <span class="w hi">plane.</span></h1>'
    js1 = ('tl.fromTo("#s1-panel .lit i, #s1-panel .warn i", { opacity:0.15 }, { opacity:1, duration:0.12, ease:"power2.out", stagger:{ each:0.05, from:"random" } }, 0.1);\n'
           'tl.fromTo("#s1-panel", { scale:1.08 }, { scale:1, duration:3.8, ease:"power1.out" }, 0);\n'
           + words_in("#s1-line .w", LEAD, 0.11))
    sc.append(("s1", durs[0], css1, html1, js1))

    # 2. the problem: windows pile up, three chips
    wins = []
    for i in range(6):
        fields = "".join('<b></b>' for _ in range(18))
        wins.append(f'<div class="old" id="s2-o{i}"><div class="bar">{"".join("<u></u>" for _ in range(7))}</div><div class="grid">{fields}</div></div>')
    css2 = """
      .old { position:absolute; width:760px; height:470px; border-radius:14px; background:#1B2622; box-shadow:0 30px 60px -20px #000, inset 0 0 0 1px #ffffff12; overflow:hidden; }
      .old .bar { height:44px; background:#22302B; display:flex; gap:10px; padding:12px 16px; }
      .old .bar u { width:84px; border-radius:6px; background:#33433d; }
      .old .grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; padding:22px; }
      .old .grid b { height:38px; border-radius:6px; background:#26332e; box-shadow:inset 0 0 0 1px #ffffff0d; }
      #s2-o0 { left:120px; top:90px; } #s2-o1 { left:560px; top:150px; } #s2-o2 { left:1030px; top:70px; }
      #s2-o3 { left:260px; top:420px; } #s2-o4 { left:760px; top:470px; } #s2-o5 { left:1150px; top:380px; }
      .chips { position:absolute; left:0; right:0; bottom:120px; display:flex; justify-content:center; gap:22px; }
      .chip { padding:18px 32px; border-radius:999px; background:var(--amber); color:#0B1411; font-size:40px; font-weight:800; }
    """
    html2 = "".join(wins) + '<div class="chips"><span class="chip" id="s2-c0">Too many screens</span><span class="chip" id="s2-c1">Too many steps</span><span class="chip" id="s2-c2">Too much training</span></div>'
    js2 = ""
    for i in range(6):
        js2 += f'tl.fromTo("#s2-o{i}", {{ y:90, opacity:0, scale:0.94 }}, {{ y:0, opacity:1, scale:1, duration:0.5, ease:"expo.out" }}, {i * 0.3:.2f});\n'
    for i, t in enumerate((LEAD + 2.2, LEAD + 3.2, LEAD + 4.2)):
        js2 += f'tl.fromTo("#s2-c{i}", {{ scale:0.6, opacity:0 }}, {{ scale:1, opacity:1, duration:0.35, ease:"back.out(1.6)" }}, {t:.2f});\n'
    sc.append(("s2", durs[1], css2, html2, js2))

    # 3. Dictate: the wordmark, then the whole clinic in one clean window
    css3 = """
      #s3-mark { position:absolute; left:0; right:0; top:410px; text-align:center; font-size:150px; font-weight:800; letter-spacing:-.04em; }
      #s3-mark i { color:var(--lime); font-style:normal; }
      #s3-sub { position:absolute; left:0; right:0; top:600px; text-align:center; font-size:40px; font-weight:600; color:var(--muted); }
    """
    html3 = f'<div id="s3-mark" data-layout-allow-overflow>Dictate<i>.</i></div><div id="s3-sub">One simple place to run your whole clinic</div>' + window("s3", [("a", "03-home")])
    js3 = ('tl.fromTo("#s3-mark", { opacity:0, scale:1.15, filter:"blur(14px)" }, { opacity:1, scale:1, filter:"blur(0px)", duration:0.6, ease:"expo.out" }, 0.1);\n'
           'tl.fromTo("#s3-sub", { opacity:0, filter:"blur(8px)" }, { opacity:1, filter:"blur(0px)", duration:0.3, ease:"power2.out" }, 0.9);\n'
           'tl.to(["#s3-mark", "#s3-sub"], { opacity:0, y:-80, filter:"blur(10px)", duration:0.35, ease:"power3.in" }, 3.5);\n'
           'tl.fromTo("#s3-win", { y:300, opacity:0, scale:0.9 }, { y:0, opacity:1, scale:1, duration:0.8, ease:"expo.out" }, 3.65);\n')
    sc.append(("s3", durs[2], css3, html3, js3))

    # 4. front desk: Walk-in -> token and payment -> the day's queue
    c_modal, c_rows = cam("walkin.modal", 1.45), cam("ops.rows", 1.3)
    wx, wy = on_canvas("ops.walkin")
    html4 = window("s4", [("a", "04a-ops"), ("b", "04b-walkin")]) + f'<div id="s4-cursor" class="cursor" style="opacity:0">{CURSOR}</div>'
    js4 = (js_rise("#s4-win", 0.0, 0.6) + js_cursor("s4", [(wx, wy, 2.0, True)], 0.9) + js_swap("s4", "a", "b", 2.0)
           + 'tl.to("#s4-cursor", { opacity:0, duration:0.2 }, 2.3);\n' + js_cam("s4", c_modal, 2.2, 0.6)
           + js_swap("s4", "b", "a", 5.6) + js_cam("s4", (0, 0, 1), 5.5, 0.5) + js_cam("s4", c_rows, 6.3, 0.6))
    sc.append(("s4", durs[3], "", html4, js4))

    # 5. history: visit history, then the brief
    html5 = window("s5", [("a", "05a-patient"), ("b", "05b-brief")])
    js5 = (js_rise("#s5-win", 0.0, 0.5) + js_cam("s5", cam("patient.timeline", 1.4), 0.5, 0.7)
           + js_cam("s5", (0, 0, 1), 3.3, 0.45) + js_swap("s5", "a", "b", 3.6) + js_cam("s5", cam("brief.pane", 1.7), 3.9, 0.7))
    sc.append(("s5", durs[4], "", html5, js5))

    # 6. dictation: tap the mic, the words appear as the doctor speaks, stop
    T0, T1 = 4.1, 9.2                                   # recording: the mic tap on "tap the mic", then the stop tap
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
    html6 = window("s6", [("a", "06e-mic"), ("b", "06f-rec"), ("c", "06a-consult")]).replace('</div></div>', live + '</div></div>', 1) + \
        f'<div id="s6-cursor" class="cursor" style="opacity:0">{CURSOR}</div>'
    js6 = (js_rise("#s6-win", 0.0, 0.5) + js_cursor("s6", [(mx, my, T0, True)], 2.6) + js_swap("s6", "a", "b", T0)
           + f'tl.to("#s6-live", {{ opacity:1, duration:0.12 }}, {T0:.2f});\n'
           + f'tl.to("#s6-cursor", {{ opacity:0, duration:0.2 }}, {T0 + 0.3:.2f});\n'
           + js_cam("s6", c_type, T0 + 0.2, 0.6)
           + f'tl.to("#s6-paper", {{ opacity:1, duration:0.05 }}, {T0 + 0.5:.2f});\n'
           + f'tl.to("#s6-text span", {{ opacity:1, duration:0.06, stagger:{(T1 - T0 - 1.3) / len(words_d):.3f} }}, {T0 + 0.5:.2f});\n')
    for k in range(int((T1 - T0) / 0.3)):           # the waveform: deterministic heights, a new set every 0.3 s
        t = T0 + k * 0.3
        hs = [0.25 + ((i * 7 + k * 13) % 10) / 11 for i in range(20)]
        js6 += "".join(f'tl.to("#s6-b{i}", {{ scaleY:{h:.2f}, duration:0.25, ease:"sine.inOut" }}, {t:.2f});\n' for i, h in enumerate(hs))
    for sec in range(1, int(T1 - T0) + 1):
        js6 += f'tl.set("#s6-clock", {{ textContent:"0:{sec:02d}" }}, {T0 + sec:.2f});\n'
    js6 += (js_cam("s6", (0, 0, 1), T1 - 0.9, 0.5)
            + f'tl.to("#s6-cursor", {{ x:{stx}, y:{sty}, opacity:1, duration:0.5, ease:"power2.inOut" }}, {T1 - 0.6:.2f});\n'
            + f'tl.to("#s6-cursor svg", {{ scale:0.82, duration:0.08, ease:"power2.in", transformOrigin:"20% 10%" }}, {T1 - 0.08:.2f});\n'
            + f'tl.to("#s6-cursor svg", {{ scale:1, duration:0.18, ease:"power2.out" }}, {T1:.2f});\n'
            + js_swap("s6", "b", "c", T1) + f'tl.to("#s6-live", {{ opacity:0, duration:0.16 }}, {T1:.2f});\n'
            + f'tl.to("#s6-cursor", {{ opacity:0, duration:0.2 }}, {T1 + 0.5:.2f});\n')
    sc.append(("s6", durs[5], css6, html6, js6))

    # 7. Generate note -> the note -> a citation -> its source -> the exact words
    c_text = cam("consult.text", 1.3)
    gx, gy = on_canvas("gen")
    cx_, cy_ = on_canvas("note.cite")
    sx, sy = on_canvas("sources.item")
    html7 = window("s7", [("a", "06a-consult"), ("b", "06b-note"), ("c", "06c-sources"), ("d", "06d-highlight")]) + \
        f'<div id="s7-cursor" class="cursor" style="opacity:0">{CURSOR}</div>'
    js7 = (js_cursor("s7", [(gx, gy, 1.0, True), (cx_, cy_, 4.6, True), (sx, sy, 6.3, True)], 0.1)
           + js_swap("s7", "a", "b", 1.0) + js_swap("s7", "b", "c", 4.6) + js_swap("s7", "c", "d", 6.3)
           + js_cam("s7", c_text, 6.6, 0.6) + 'tl.to("#s7-cursor", { opacity:0, duration:0.2 }, 6.6);\n')
    sc.append(("s7", durs[6], "", html7, js7))

    # 8. sign and print
    css8 = """
      #s8-paper { position:absolute; left:460px; top:70px; width:1000px; height:940px; border-radius:20px; overflow:hidden; box-shadow:0 40px 90px -20px #000; }
      #s8-paper img { position:absolute; left:-460px; top:-30px; width:1920px; height:1080px; }
    """
    html7 = window("s8", [("a", "07a-signed")]) + '<div id="s8-paper"><img src="assets/shots/07b-print.jpg"></div>'
    js8 = (js_rise("#s8-win", 0.0, 0.4) + js_cam("s8", cam("signed.dock", 1.5), 0.2, 0.5)
           + 'tl.fromTo("#s8-paper", { y:1100 }, { y:0, duration:0.6, ease:"expo.out" }, 1.5);\n')
    sc.append(("s8", durs[7], css8, html7, js8))

    # 9. collections, then the team
    html8 = window("s9", [("a", "08a-collections"), ("b", "08b-team")])
    js9 = (js_rise("#s9-win", 0.0, 0.5) + js_cam("s9", cam("money.panel1", 1.35), 0.3, 0.6)
           + js_cam("s9", (0, 0, 1), 2.1, 0.4) + js_swap("s9", "a", "b", 2.3) + js_cam("s9", cam("team.list", 1.25), 2.6, 0.6))
    sc.append(("s9", durs[8], "", html8, js9))

    # 10. laptop, tablet and phone
    css10 = """
      .dev { position:absolute; overflow:hidden; background:#000; box-shadow:0 40px 80px -20px #000, 0 0 0 1px #ffffff1a; }
      .dev img { width:100%; height:100%; object-fit:cover; object-position:top; display:block; }
      #s10-lap { left:110px; top:190px; width:1100px; height:619px; border-radius:22px; border:10px solid #1d2925; }
      #s10-tab { left:1150px; top:150px; width:470px; height:676px; border-radius:30px; border:12px solid #1d2925; }
      #s10-pho { left:1540px; top:300px; width:280px; height:606px; border-radius:40px; border:10px solid #1d2925; }
    """
    html9 = ('<div class="dev" id="s10-lap"><img src="assets/shots/03-home.jpg"></div>'
             '<div class="dev" id="s10-tab"><img src="assets/shots/09c-tablet-brief.jpg"></div>'
             '<div class="dev" id="s10-pho"><img src="assets/shots/09a-phone-note.jpg"></div>')
    js10 = js_rise("#s10-lap", 0.2) + js_rise("#s10-tab", 0.7) + js_rise("#s10-pho", 1.2)
    sc.append(("s10", durs[9], css10, html9, js10))

    # 11. end card
    css11 = """
      #s11-mark { position:absolute; left:0; right:0; top:380px; text-align:center; font-size:170px; font-weight:800; letter-spacing:-.04em; }
      #s11-mark i { color:var(--lime); font-style:normal; }
      #s11-line { position:absolute; left:0; right:0; top:620px; text-align:center; font-size:56px; font-weight:700; }
      #s11-line .hi { color:var(--lime); }
    """
    html10 = f'<div id="s11-mark">Dictate<i>.</i></div><div id="s11-line">{words("s11", "Your whole clinic,")} <span class="w hi">made</span> <span class="w hi">simple.</span></div>'
    js11 = ('tl.fromTo("#s11-mark", { opacity:0, scale:1.12, filter:"blur(14px)" }, { opacity:1, scale:1, filter:"blur(0px)", duration:0.7, ease:"expo.out" }, 0.1);\n'
            + words_in("#s11-line .w", LEAD + 0.5, 0.1))
    sc.append(("s11", durs[10], css11, html10, js11))
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
    .cap {{ position:absolute; left:0; right:0; bottom:46px; text-align:center; opacity:0; }}
    .cap span {{ display:inline-block; padding:10px 22px; border-radius:14px; background:#0B1411d9; color:#E8F1EC; font-size:40px; font-weight:700; letter-spacing:-.01em; }}
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
    voices = "".join(f'      <audio id="vo-{i + 1}" class="clip" src="assets/audio/vo-{i + 1}.mp3" data-start="{starts[i] + LEAD:.2f}" '
                     f'data-duration="{vo[i]:.2f}" data-track-index="3" data-volume="1"></audio>\n' for i in range(len(vo)))
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
      #bg {{ position:absolute; inset:0; background:#0B1411; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
      <div id="bg"></div>
{hosts}      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions" data-width="{W}" data-height="{H}"></div>
      <audio id="music" class="clip" src="assets/audio/music-pad.mp3" data-start="0" data-duration="{total}" data-track-index="4" data-volume="0.14" data-fade-in="1.5" data-fade-out="2.5"></audio>
{voices}    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""")
    (HERE / "timing.json").write_text(json.dumps({"total": total, "scenes": dict(zip([s[0] for s in scenes], starts)), "captions": caps}, indent=1))
    print(f"main: {total} s, {len(scenes)} scenes, {len(caps)} caption groups")


if __name__ == "__main__":
    build()
