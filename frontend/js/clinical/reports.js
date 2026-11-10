/* Reports a doctor adds: before a visit (filed under the patient), while choosing the place, or in the consultation
   (tied to that visit). One sheet for all three, in its own layer so whatever is underneath (the "Where?" picker)
   stays open. Photos are shrunk before upload to save mobile data; the AI reads each one in the background. */

let RP = null;
const RP_CAM = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>`;
const RP_FILE = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7v18h10V6z"/><path d="M14 3v3h3M10 12h4M10 16h4"/></svg>`;   // { patientId, visitId, done, timer }

const repLayer = () => document.getElementById("rep-layer") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "rep-layer" }));
const repStatus = d => d.ai_status === "processing" ? `<span class="rp-st reading">Reading…</span>`
  : d.ai_status === "failed" ? `<button class="rp-st failed" data-a="rp-retry" data-v="${d.id}">Couldn't read · Try again</button>` : `<span class="rp-st ok">Ready</span>`;

async function repList() {
  if (RP.visitId) return api(`/visits/${RP.visitId}/documents`);
  return (await api(`/patients/${RP.patientId}`)).documents.filter(d => !d.visit_id);
}

async function openReports(opts) {
  clearTimeout(RP?.timer);
  RP = { ...opts };
  await paintReports();
}

async function paintReports(busy) {
  if (!RP) return;
  const docs = await repList();
  if (!RP) return;
  repLayer().innerHTML = `<div class="scrim rp-scrim"><div class="modal rp-modal" role="dialog" aria-modal="true" aria-label="Reports">
    <button class="icon-x modal-x" data-a="rp-close" aria-label="Close">×</button>
    <h2>Reports</h2>
    ${docs.length ? `<div class="rp-list">${docs.map(d => `<div class="rp-row"><span class="rp-name">${esc(d.filename)}</span>${repStatus(d)}
        <button class="icon-x" data-a="rp-remove" data-v="${d.id}" aria-label="Remove ${esc(d.filename)}">×</button></div>`).join("")}</div>` : ""}
    ${busy ? `<div class="rp-busy">${esc(busy)}</div>` : `<div class="rp-pick">
      <label class="rp-btn"><input type="file" accept="image/*" capture="environment" data-a="rp-file" hidden>${RP_CAM}<span>Take photo</span></label>
      <label class="rp-btn"><input type="file" accept="image/*,.pdf,.txt" multiple data-a="rp-file" hidden>${RP_FILE}<span>Choose files</span></label></div>`}
    <div class="foot"><button class="btn primary" data-a="rp-close">Done</button></div></div></div>`;
  clearTimeout(RP.timer);
  if (docs.some(d => d.ai_status === "processing")) RP.timer = setTimeout(() => paintReports(), 2500);   // until each is read
}

function closeReports() {
  if (!RP) return;
  const done = RP.done; clearTimeout(RP.timer); RP = null; repLayer().innerHTML = "";
  done?.();
}

// Big photos are resized to 2000 px JPEG (a phone photo of a report: ~4 MB down to ~400 KB); PDFs and text go as they are.
async function shrink(file) {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size < 1.2e6) return file;
  try {
    const bmp = await createImageBitmap(file), k = Math.min(1, 2000 / Math.max(bmp.width, bmp.height));
    const c = Object.assign(document.createElement("canvas"), { width: Math.round(bmp.width * k), height: Math.round(bmp.height * k) });
    c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
    const blob = await new Promise(r => c.toBlob(r, "image/jpeg", .85));
    return blob && blob.size < file.size ? new File([blob], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" }) : file;
  } catch { return file; }   // e.g. HEIC on a browser that can't decode it: send the original
}

async function uploadReports(files) {
  const url = RP.visitId ? `/visits/${RP.visitId}/documents` : `/patients/${RP.patientId}/documents`;
  let ok = 0;
  for (const [i, f] of files.entries()) {
    await paintReports(files.length > 1 ? `Uploading ${i + 1} of ${files.length}…` : "Uploading…");
    const fd = new FormData(); fd.append("file", await shrink(f));
    try { await api(url, { body: fd }); ok++; } catch (e) { toast(`${f.name}: ${e.message}`, true); }
  }
  if (ok) toast(ok > 1 ? `${ok} reports added` : "Report added");
  await paintReports();
}

document.addEventListener("click", e => {
  const t = e.target.closest("[data-a]"); if (!t || !t.dataset.a.startsWith("rp-") || t.dataset.a === "rp-file") return;
  e.preventDefault(); e.stopPropagation();
  run(async () => {
    const a = t.dataset.a, v = t.dataset.v;
    if (a === "rp-open") await openReports({ patientId: Number(t.dataset.p), visitId: v ? Number(v) : null, done: RP_AFTER[t.dataset.after] });
    if (a === "rp-close") closeReports();
    if (a === "rp-remove") { await api(`/documents/${v}`, { method: "DELETE" }); toast("Removed"); await paintReports(); }
    if (a === "rp-retry") { await api(`/documents/${v}/retry`, { body: {} }); await paintReports(); }
  });
}, true);
document.addEventListener("change", e => {
  if (e.target.dataset?.a !== "rp-file" || !e.target.files.length || !RP) return;
  const files = [...e.target.files]; e.target.value = "";
  run(() => uploadReports(files));
});

// What to refresh when the sheet closes, by where it was opened.
const RP_AFTER = {
  patient: () => { if (location.hash.startsWith("#/p/")) viewSoloPatient(Number(location.hash.split("/")[2])); },
  consult: () => { if (location.hash.startsWith("#/consult")) refreshConsult(); },
  none: null,
};
const reportBtn = (cls, patientId, visitId, after, label = "+ Report") =>
  `<button class="${cls}" data-a="rp-open" data-p="${patientId}" data-v="${visitId || ""}" data-after="${after}">${label}</button>`;
