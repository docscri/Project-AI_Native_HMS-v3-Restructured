/* patients */
async function viewPatients(id) {
  const g = S.gen;
  S.pq = S.pq ?? "";
  await run(async () => {
    const list = await api(`/patients?q=${encodeURIComponent(S.pq)}`);
    const p = id ? await api(`/patients/${id}`) : null;
    if (stale(g)) return;
    view(`<div class="head"><div><h1>Patients</h1></div><span class="grow"></span><button class="btn primary" data-a="register">New patient</button></div>
      <input class="input" id="pt-q" placeholder="Search name, phone or UHID" value="${esc(S.pq)}" data-a="pt-q" autocomplete="off" aria-label="Search patients">
      <div class="cols" style="grid-template-columns:minmax(0,1fr) minmax(0,1.2fr)">
        <section class="panel scroll"><table class="t"><thead><tr><th class="uhid-col">UHID</th><th>Name</th><th>Age</th><th>Phone</th></tr></thead><tbody>
          ${list.map(x => `<tr class="click ${x.id === id ? "selected" : ""}" data-a="pt-open" data-v="${x.id}"><td class="mono uhid-col">${esc(x.uhid)}</td><td><b>${esc(x.name)}</b></td><td>${ageOf(x.dob)} ${esc(x.sex || "")}</td><td>${esc(x.phone)}</td></tr>`).join("") || `<tr><td colspan="4" class="muted">—</td></tr>`}
        </tbody></table></section>
        ${p ? profile(p) : `<section class="panel pt-none"><span class="muted">—</span></section>`}
      </div>${p ? `<div class="pt-scrim" data-a="pt-close"></div>` : ""}`);
  });
}
function profile(p) {
  const visits = p.visits.filter(v => ["done", "with_doctor", "waiting", "booked"].includes(v.status));
  return `<section class="panel pt-sheet" style="gap:14px"><button class="pt-close icon-x" data-a="pt-close" aria-label="Close">×</button><div class="actions" style="justify-content:space-between;align-items:flex-start"><div><h2>${esc(p.name)}</h2>
      <div class="muted">${ageOf(p.dob)} ${esc(p.sex || "")} · <span class="mono">${esc(p.uhid)}</span> · ${esc(p.phone)}</div>${p.address ? `<div class="muted">${esc(p.address)}</div>` : ""}${p.consent_at ? `<div class="muted consent-line">✓ Consent ${longDate(p.consent_at)}</div>` : ""}</div><span class="actions" style="gap:6px"><button class="btn small" data-a="pt-edit" data-v="${p.id}">Profile</button><button class="btn small" data-a="pt-merge" data-v="${p.id}">Merge</button></span></div>
    <span class="label">Visit history</span>
    ${visits.length ? `<div class="timeline">${visits.map(v => `<div class="tl"><div class="tl-head"><b>${longDate(v.date)}</b><span>${esc(v.doctor)}</span>${pill(v.status)}</div>
      <div class="items">${v.note ? `<button class="btn small" data-a="note-view" data-v="${v.id}">${v.note.status === "signed" ? "Note & prescription" + (v.note.addenda ? ` · ${v.note.addenda} addend${v.note.addenda > 1 ? "a" : "um"}` : "") : "Draft note"}</button>` : ""}
      ${v.documents.map(d => `<button class="btn small" data-a="open-doc" data-v="${d.id}">📄 ${esc(docTitle(d))}</button>${d.ai_status === "failed" ? `<button class="btn small dark" data-a="doc-retry" data-v="${d.id}" title="Couldn't be read. Try again, or tell the clinic admin if it keeps failing.">Couldn't read · Try again</button>` : ""}`).join("")}</div>
      ${v.line ? `<div class="muted" style="font-size:13.5px;margin-top:6px">${esc(v.line)}</div>` : ""}</div>`).join("")}</div>` : `<div class="empty">—</div>`}
  </section>`;
}
const stampOf = ts => { const d = new Date(ts); return `${d.getDate()} ${d.toLocaleDateString("en-IN", { month: "short" })}, ${d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" }).toLowerCase()}`; };
async function openNoteView(visitId) {
  const v = await api(`/visits/${visitId}`), n = v.note;
  if (!n) return;
  const signed = n.status === "signed", when = ts => { const d = new Date(ts); return `${d.getDate()} ${d.toLocaleDateString("en-IN", { month: "short" })}, ${d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" }).toLowerCase()}`; };
  M = { kind: "note-view", noteId: n.id };
  const by = n.signed_by_name && n.signed_by_name !== v.doctor_name ? ` by ${esc(n.signed_by_name)}` : "";
  modal(`<div class="nv">
    <div class="nv-top"><div><h2>${esc(v.patient_name)}${v.age != null ? ", " + v.age : ""}</h2>
      <span class="muted">${longDate(v.date)} · ${esc(v.doctor_name)}${signed ? ` · Signed ${when(n.signed_at)}${by}` : ""}</span></div>
      <span class="grow"></span><div class="nv-acts"><span class="pill ${signed ? "s-paid" : "s-waiting"}">${signed ? "Signed" : "Draft"}</span>${signed && S.me.kind === "doctor" ? `<button class="btn small" data-a="add-addendum" data-v="${n.id}" data-visit="${v.id}">Add addendum</button>` : ""}${signed ? `<button class="btn small primary" data-a="note-print" data-v="${n.id}">Print</button>` : ""}</div></div>
    <div class="nv-body">${soapRead(v, n, true, signed)}</div></div>`, true);
}
function renderFollowUp() {
  const opts = [[3, "3 days"], [7, "1 week"], [14, "2 weeks"], [30, "1 month"]];
  modal(`<h2>Follow-up</h2>
    <div class="seg">${opts.map(([n, l]) => `<button data-a="fu-pick" data-v="${n}" aria-pressed="${addDays(TODAY, n) === M.date}">${l}</button>`).join("")}</div>
    <input class="date-pill" aria-label="Date" type="date" id="fu-date" min="${addDays(TODAY, 1)}" value="${M.date}">
    <div class="foot"><button class="btn primary" data-a="fu-go">Book</button></div>`);
}
function renderMerge() {
  const m = M;
  modal(`<h2>Merge into this patient</h2>
    ${m.other ? `<div class="hit actions" style="justify-content:space-between;align-items:center"><span><b>${esc(m.other.name)}</b> · ${esc(m.other.phone || "—")}</span><span class="mono muted">${esc(m.other.uhid)}</span></div>`
      : `<input class="input" id="mg-q" placeholder="Search name, phone or UHID" value="${esc(m.q)}" data-a="mg-q" autocomplete="off">
         <div class="pick">${m.results.filter(x => x.id !== m.id).map(x => `<button data-a="mg-pick" data-v="${x.id}"><span><b>${esc(x.name)}</b> · ${esc(x.phone || "—")}</span><span class="mono muted">${esc(x.uhid)}</span></button>`).join("")}</div>`}
    <div class="foot"><button class="btn danger" data-a="mg-go" ${m.other ? "" : "disabled"}>Merge</button></div>`);
  const q = $("#mg-q"); if (q) { q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
}
function openPatientEdit(p) {
  M = { kind: "pedit", id: p.id };
  modal(`<div><h2>${esc(p.name)}</h2><span class="muted">${esc(p.uhid)}${p.dob ? " · " + ageOf(p.dob) : ""}${p.sex ? " " + esc(p.sex) : ""}</span></div><div class="grid2"><label class="field">Name<input id="pe-name" value="${esc(p.name)}"></label><label class="field">Phone<input id="pe-phone" value="${esc(p.phone)}"></label></div>
    <div class="grid2"><label class="field">Date of birth<input id="pe-dob" type="date" value="${esc(p.dob || "")}"></label><label class="field">Sex<select id="pe-sex">${["M", "F", "O"].map(s => `<option ${p.sex === s ? "selected" : ""}>${s}</option>`).join("")}</select></label></div>
    <label class="field">Address<input id="pe-addr" value="${esc(p.address || "")}"></label>
    <div class="foot"><button class="btn primary" data-a="pe-save">Save</button></div>`);
}
