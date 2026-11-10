/* A doctor's signature, shown on the notes they sign (print and PDF). Drawn with a finger or uploaded as a photo;
   either way it is cleaned here into a small transparent PNG: ink only, trimmed, no paper. */

function paintSignature() {
  const box = $("#sig-box"); if (!box) return;
  const has = !!S.me.signature_id;
  box.innerHTML = `<div class="sig-state"><span class="sig-label">Signature</span>${has ? "<b>Added</b>" : `<b class="none">Not added</b>`}</div>
    <div class="sig-btns">${has ? `<button class="btn small" data-a="sig-view">View</button>` : ""}<button class="btn small" data-a="sig-draw">Draw</button>
      <label class="btn small sig-up">Upload<input type="file" accept="image/*" data-a="sig-file" hidden></label>
      ${has ? `<button class="btn small danger" data-a="sig-remove">Remove</button>` : ""}</div>`;
}
async function viewSignature() {
  const r = await fetch(`/api/signatures/${S.me.signature_id}`, { headers: { Authorization: "Bearer " + S.token } });
  if (!r.ok) throw new Error("Could not load the signature.");
  if (S.sigUrl) URL.revokeObjectURL(S.sigUrl);
  S.sigUrl = URL.createObjectURL(await r.blob());
  const layer = document.getElementById("sig-layer") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "sig-layer" }));
  layer.innerHTML = `<div class="scrim"><div class="modal sig-modal" role="dialog" aria-modal="true" aria-label="Your signature">
    <h2>Your signature</h2><div class="sig-view-img"><img src="${S.sigUrl}" alt="Your signature"></div>
    <span class="sig-hint">Shown on the notes you sign</span>
    <div class="foot"><button class="btn danger" data-a="sig-remove" style="margin-right:auto">Remove</button><button class="btn primary" data-a="sig-cancel">Done</button></div></div></div>`;
}

// Ink only: anything near the paper's brightness becomes transparent, the rest dark ink; trimmed and scaled down.
function cleanSignature(src, fromPhoto) {
  const max = 1400, k = Math.min(1, max / Math.max(src.width, src.height));
  const w = Math.max(1, Math.round(src.width * k)), h = Math.max(1, Math.round(src.height * k));
  const c = Object.assign(document.createElement("canvas"), { width: w, height: h }), x = c.getContext("2d", { willReadFrequently: true });
  x.drawImage(src, 0, 0, w, h);
  const d = x.getImageData(0, 0, w, h), p = d.data;
  let paper = 255;
  if (fromPhoto) {   // the paper is the bright majority: the 80th percentile of brightness
    const hist = new Array(256).fill(0);
    for (let i = 0; i < p.length; i += 16) hist[Math.round(.299 * p[i] + .587 * p[i + 1] + .114 * p[i + 2])]++;
    let n = 0, total = hist.reduce((a, b) => a + b, 0);
    for (let v = 0; v < 256; v++) { n += hist[v]; if (n >= total * .8) { paper = v; break; } }
  }
  const cut = paper * .78;
  let x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) for (let xx = 0; xx < w; xx++) {
    const i = (y * w + xx) * 4, a = p[i + 3] / 255, lum = (.299 * p[i] + .587 * p[i + 1] + .114 * p[i + 2]) * a + 255 * (1 - a);
    const ink = lum < cut ? Math.min(1, (cut - lum) / (cut * .55)) : 0;
    p[i] = 11; p[i + 1] = 20; p[i + 2] = 17; p[i + 3] = Math.round(ink * 255);
    if (ink > .15) { if (xx < x0) x0 = xx; if (xx > x1) x1 = xx; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  }
  if (x1 < 0) return null;   // nothing that looks like ink
  x.putImageData(d, 0, 0);
  const pad = 6; x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad); x1 = Math.min(w - 1, x1 + pad); y1 = Math.min(h - 1, y1 + pad);
  const cw = x1 - x0 + 1, ch = y1 - y0 + 1, s = Math.min(1, 600 / cw, 220 / ch);
  const out = Object.assign(document.createElement("canvas"), { width: Math.round(cw * s), height: Math.round(ch * s) });
  out.getContext("2d").drawImage(c, x0, y0, cw, ch, 0, 0, out.width, out.height);
  return new Promise(r => out.toBlob(r, "image/png"));
}

async function saveSignature(blob) {
  if (!blob) return toast("No signature found in that image.", true);
  const fd = new FormData(); fd.append("file", blob, "signature.png");
  const res = await fetch("/api/me/signature", { method: "PUT", headers: { Authorization: "Bearer " + S.token }, body: fd });
  const out = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(out.detail || "Could not save the signature.");
  S.me.signature_id = out.signature_id; S.me.has_signature = true;
  toast("Signature saved"); paintSignature();
}

// Draw pad: its own layer above the account form, so unsaved edits there stay.
function openSignaturePad() {
  const layer = document.getElementById("sig-layer") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "sig-layer" }));
  layer.innerHTML = `<div class="scrim"><div class="modal sig-modal" role="dialog" aria-modal="true" aria-label="Draw your signature">
    <h2>Draw your signature</h2><canvas class="sig-pad" id="sig-pad"></canvas><span class="sig-hint">Sign above the line</span>
    <div class="foot"><button class="btn ghost" data-a="sig-clear" style="margin-right:auto">Clear</button><button class="btn" data-a="sig-cancel">Cancel</button><button class="btn primary" data-a="sig-save">Save</button></div></div></div>`;
  const cv = $("#sig-pad"), r = cv.getBoundingClientRect(), dpr = Math.min(3, devicePixelRatio || 1);
  cv.width = r.width * dpr; cv.height = r.height * dpr;
  const g = cv.getContext("2d"); g.scale(dpr, dpr); g.lineCap = g.lineJoin = "round"; g.strokeStyle = "#0B1411";
  let last = null, drew = false;
  const at = e => { const b = cv.getBoundingClientRect(); return { x: e.clientX - b.left, y: e.clientY - b.top, p: e.pressure || .5 }; };
  cv.addEventListener("pointerdown", e => { cv.setPointerCapture(e.pointerId); last = at(e); g.beginPath(); g.arc(last.x, last.y, 1.2, 0, 7); g.fillStyle = "#0B1411"; g.fill(); drew = true; });
  cv.addEventListener("pointermove", e => {
    if (!last) return; const pt = at(e);
    g.lineWidth = 1.6 + pt.p * 2.2; g.beginPath(); g.moveTo(last.x, last.y); g.lineTo(pt.x, pt.y); g.stroke(); last = pt;
  });
  const end = () => { last = null; }; cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end);
  S.sigPad = { cv, g, drew: () => drew, clear: () => { g.clearRect(0, 0, cv.width, cv.height); drew = false; } };
}
const closeSignaturePad = () => { const l = document.getElementById("sig-layer"); if (l) l.innerHTML = ""; S.sigPad = null; };

document.addEventListener("click", e => {
  const t = e.target.closest("[data-a]"); if (!t || !t.dataset.a.startsWith("sig-") || t.dataset.a === "sig-file") return;
  e.preventDefault(); e.stopPropagation();
  run(async () => {
    const a = t.dataset.a;
    if (a === "sig-view") await viewSignature();
    if (a === "sig-draw") openSignaturePad();
    if (a === "sig-clear") S.sigPad?.clear();
    if (a === "sig-cancel") closeSignaturePad();
    if (a === "sig-save") { if (!S.sigPad?.drew()) return toast("Sign in the box first.", true); const blob = await cleanSignature(S.sigPad.cv, false); closeSignaturePad(); await saveSignature(blob); }
    if (a === "sig-remove") { closeSignaturePad(); await api("/me/signature", { method: "DELETE" }); S.me.signature_id = null; S.me.has_signature = false; toast("Signature removed. Notes already signed keep it."); paintSignature(); }
  });
}, true);
document.addEventListener("change", e => {
  if (e.target.dataset?.a !== "sig-file" || !e.target.files[0]) return;
  const f = e.target.files[0]; e.target.value = "";
  run(async () => {
    const url = URL.createObjectURL(f);
    try {
      const img = await new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => bad(new Error("Couldn't read that image.")); i.src = url; });
      await saveSignature(await cleanSignature(img, true));
    } finally { URL.revokeObjectURL(url); }
  });
});
