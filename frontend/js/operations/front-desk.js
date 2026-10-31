/* arrival, cancel, upload, register */
function openArrive(v) {
  M = { kind: "arrive", pay: "upi", v };
  modal(`<h2>${esc(v.patient_name)} has arrived</h2>${payBlock(v.fee, "upi")}
    <div class="foot"><button class="btn primary" data-a="arrive-paid">Send to Waiting</button></div>`);
}
function openRefund(v) {
  const left = v.refundable || 0;
  M = { kind: "refund", v, reason: "" };
  modal(`<h2>Refund · ${esc(v.patient_name)}</h2>
    <label class="field">Amount (₹)<input type="number" min="1" max="${left}" id="rf-amt" value="${left}"></label>
    ${reasonChips(REFUND_REASONS, "", "rf-reason")}
    <label class="field">Reason<input id="rf-why"></label>
    <div class="foot"><button class="btn danger" data-a="refund-go">Refund</button></div>`);
}
// Add documents to a visit; what's already added is listed with a remove button, so a wrong file can be taken back.
async function openUpload(visitId) {
  M = { kind: "upload", visitId };
  const docs = await api(`/visits/${visitId}/documents`);
  if (M?.kind !== "upload" || M.visitId !== visitId) return;
  modal(`<h2>Add document</h2>
    ${docs.length ? `<div class="up-list">${docs.map(d => `<div class="up-row"><span>📄 ${esc(d.filename)}</span>
      <button class="icon-x" data-a="doc-remove" data-v="${d.id}" aria-label="Remove ${esc(d.filename)}" title="Remove">×</button></div>`).join("")}</div>` : ""}
    <div class="up-pick"><label class="file-drop"><input type="file" id="up-file" accept="image/*,.pdf,.txt" data-a="up-file"><span class="file-btn">Choose file</span><span class="file-name" id="up-name">No file</span></label>
      <button class="icon-x up-clear" data-a="up-clear" aria-label="Clear chosen file" title="Clear" hidden>×</button></div>
    <div class="foot">${docs.length ? `<button class="btn" data-a="upload-done">Done</button>` : ""}<button class="btn primary" data-a="upload-go">Upload</button></div>`);
}
async function doUpload(visitId, file) {
  const fd = new FormData(); fd.append("file", file);
  await api(`/visits/${visitId}/documents`, { body: fd });
  toast("Uploaded.");
}
function openRegister(name) {
  const back = M?.kind === "booking" ? M : null;
  M = { kind: "register", back };
  modal(`<h2>New patient</h2>
    <div class="grid2"><label class="field">Name<input id="rg-name" value="${esc(name || "")}"></label><label class="field">Phone<input id="rg-phone" placeholder="98470 12345"></label></div>
    <div class="grid2"><label class="field">Date of birth<input id="rg-dob" type="date" max="${TODAY}"></label><label class="field">Sex<select id="rg-sex"><option value="M">Male</option><option value="F">Female</option><option value="O">Other</option></select></label></div>
    <label class="field">Address<input id="rg-addr"></label>
    <label class="choice"><input type="checkbox" id="rg-consent"><span><b>Patient agrees to the clinic keeping their health records</b></span></label>
    <div class="foot"><button class="btn" data-a="${back ? "rg-back" : "close"}">${back ? "Back" : "Cancel"}</button><button class="btn primary" data-a="rg-save">Register</button></div>`);
  setTimeout(() => $("#rg-name")?.focus(), 30);
}
