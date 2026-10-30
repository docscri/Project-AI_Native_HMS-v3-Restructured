/* booking modal */
let M = null;
function openBooking(mode, opts = {}) {
  M = { kind: "booking", mode, patient: opts.patient || null, q: "", results: [], doctorId: opts.doctorId || S.doctors[0]?.id, date: mode === "walk" ? TODAY : (S.date && S.date >= TODAY ? S.date : TODAY),
        avail: null, token: null, pay: "upi", session: opts.visit?.session_start || null, reason: "", visit: opts.visit || null, done: null };
  if (!S.doctors.length) return toast("Add a doctor first.", true);
  loadAvail();
}
async function loadAvail() {
  const b = M; if (!b || b.kind !== "booking") return;
  b.avail = await api(`/availability?doctor_id=${b.doctorId}&date=${b.mode === "walk" ? TODAY : b.date}${b.visit ? "&exclude_visit=" + b.visit.id : ""}${b.session ? "&session=" + b.session : ""}`).catch(e => ({ available: false, reason: e.message, sessions: [] }));
  b.session = b.avail.session || null;
  b.token = b.avail.next?.token ?? null;
  renderBooking();
}
function slotCard(token, time, note, a, fee) {
  return `<div class="tiles-row"><div class="tk big"><small>Token</small><b>${token}</b></div>
    ${time ? `<div class="tk"><small>${note ? "Around" : "Time"}</small><b>${time}</b></div>` : ""}
    <div class="tk"><small>Left</small><b>${a.left}</b></div>${fee != null ? feeTile(fee) : ""}</div>`;
}
function renderBooking() {
  const b = M; if (!b) return;
  if (b.done) return modal(b.done);
  const a = b.avail || {}, s = a.schedule;
  const title = { book: "New booking", walk: "Walk-in", resched: "Reschedule" }[b.mode];
  let slot = "";
  if (!a.available) slot = `<div class="warn">${esc(a.reason || "Not available.")}</div>`;
  else if (b.mode === "walk") slot = slotCard(a.token_timing === "booking" ? a.next.token : "—", "", "", a, a.available ? a.fee : null);
  else if (a.token_timing === "booking") {
    const free = new Set(a.free_tokens.map(t => t.token)), times = Object.fromEntries(a.free_tokens.map(t => [t.token, t.time]));
    slot = `${slotCard(b.token, times[b.token], s.exact_time ? "" : "approx.", a)}<div class="chips slot-chips">${Array.from({ length: s.max_patients }, (_, i) => i + 1).filter(t => free.has(t)).map(t => `<button data-a="pick-token" data-v="${t}" aria-pressed="${t === b.token}"><b>${t}</b>${times[t]}</button>`).join("")}</div>`;
  } else slot = slotCard("—", a.expected_time, "approx.", a);
  const p = b.patient;
  const sessChips = (a.sessions || []).length > 1 ? `<div class="seg">${a.sessions.map(x => `<button data-a="bk-session" data-v="${x.key}" aria-pressed="${x.key === b.session}" ${x.ended ? "disabled" : ""}>${x.label} · ${x.start}–${x.end}</button>`).join("")}</div>` : "";
  const extra = b.mode === "walk" && a.available ? payBlock(a.fee, b.pay, true) : b.mode === "resched" ? reasonChips(RESCHED_REASONS, b.reason, "bk-reason") : "";
  modal(`<div class="booking-dialog"><h2>${title}</h2>
    ${p ? `<div class="pt-chip"><span class="avatar">${esc(initials(p.name))}</span><span class="pt-main"><b>${esc(p.name)}</b><span class="pt-meta"><span class="mono">${esc(p.uhid)}</span>${p.phone ? `<span>${esc(p.phone)}</span>` : ""}</span></span>${b.mode === "resched" ? "" : `<button class="btn small" data-a="bk-clear">Change</button>`}</div>`
        : `<input class="input" id="bk-q" placeholder="Search name, phone or UHID" value="${esc(b.q)}" data-a="bk-q" autocomplete="off">
           <div class="pick">${b.results.map(r => `<button data-a="bk-pick" data-v="${r.id}"><span><b>${esc(r.name)}</b> · ${esc(r.phone)}</span><span class="mono muted">${esc(r.uhid)}</span></button>`).join("")}</div>`}
    <div class="grid2 booking-fields">
      ${b.mode === "walk" ? "" : `<label class="field"><input type="date" aria-label="Date" id="bk-date" min="${TODAY}" value="${b.date}" data-a="bk-date"></label>`}
      <label class="field"><select aria-label="Doctor" id="bk-doc" data-a="bk-doc">${S.doctors.map(d => `<option value="${d.id}" ${d.id === b.doctorId ? "selected" : ""}>${esc(d.name)}</option>`).join("")}</select></label>
    </div>
    ${sessChips}
    ${slot}
    ${extra}
    <div class="foot">
      ${p && !a.available && b.mode === "book" && /full/i.test(a.reason || "") ? `<button class="btn" data-a="bk-wait">Waitlist</button>` : ""}
      <button class="btn primary" data-a="bk-confirm" ${p && a.available ? "" : "disabled"}>${b.mode === "walk" ? "Paid" : b.mode === "resched" ? "Move booking" : "Confirm"}</button></div></div>`);
  const q = $("#bk-q"); if (q) { q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
}
async function confirmBooking() {
  const b = M, p = b.patient;
  if (b.mode === "walk") {
    const v = await api("/visits/walk-in", { body: { patient_id: p.id, doctor_id: b.doctorId, session: b.session, ...readPay(b.avail.fee) } });
    b.done = paidDone("Walk-in added", v);
  } else if (b.mode === "resched") {
    const v = await api(`/visits/${b.visit.id}/reschedule`, { body: { doctor_id: b.doctorId, date: b.date, session: b.session, token: b.token, reason: b.reason } });
    b.done = `<h2>Booking moved</h2><div class="result">${esc(p.name)} → ${esc(v.doctor_name)}, ${niceDate(v.date)}${v.token_label ? ` · token ${v.token_label} · ${v.expected_time}` : ""}</div><div class="foot"><button class="btn primary" data-a="close-refresh">Done</button></div>`;
  } else {
    const v = await api("/visits", { body: { patient_id: p.id, doctor_id: b.doctorId, date: b.date, session: b.session, token: b.token } });
    b.done = `<h2>Booked</h2><div class="result">${esc(p.name)} with ${esc(v.doctor_name)} · ${niceDate(v.date)}</div><div class="say">“${esc(v.tell_patient)}”</div>
      <div class="foot"><button class="btn" data-a="close-refresh">Done</button><button class="btn primary" data-a="book-another">Book another</button></div>`;
  }
  renderBooking();
}
let searchT;
function searchPatients(q) {
  M.q = q; clearTimeout(searchT);
  searchT = setTimeout(() => run(async () => { if (!M) return; M.results = q.trim() ? await api(`/patients?q=${encodeURIComponent(q)}`) : []; renderBooking(); }), 180);
}
