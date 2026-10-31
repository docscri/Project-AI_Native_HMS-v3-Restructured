/* consultation */
const CTABS = [["brief", "Brief"], ["dictate", "Consult"], ["note", "Note"]];
const BTABS = [["summary", "Summary"], ["events", "Events"], ["charts", "Charts"]];
async function viewConsult(visitId, doctorParam, patientParam) {
  const g = S.gen;
  const isDoctor = S.me.kind === "doctor";
  const doctorId = Number(doctorParam) || (isDoctor ? S.me.id : S.doctors[0]?.id);
  if (!CTABS.some(t => t[0] === S.ctab)) S.ctab = "brief";
  S.cside = S.cside || "profile"; S.cq = S.cq ?? "";
  const load = async () => {
    const today = await api(`/consultation/today?doctor_id=${doctorId}`);
    const cur = visitId ? await api(`/visits/${visitId}`) : null;
    const pid = cur?.patient_id || Number(patientParam) || null;
    const profile = pid && S.me.screens.includes("patients") ? await api(`/patients/${pid}`) : null;
    const found = S.cq.trim() ? await api(`/patients?q=${encodeURIComponent(S.cq)}`) : [];
    if (stale(g)) return;
    if (cur) { S.textRev = S.textRev || {}; S.textRev[cur.id] = Math.max(S.textRev[cur.id] ?? 0, cur.text_rev ?? 0); }
    S.data = { today, cur, profile, found, doctorId, pid };
    renderConsult();
    if (cur && ["waiting", "with_doctor"].includes(cur.status) && !cur.brief && !S.briefing) {
      S.briefing = true;
      run(async () => { try { await api(`/visits/${cur.id}/brief`, { body: {} }); } finally { S.briefing = false; } refreshConsult(); });
    }
  };
  S.reloadConsult = load;
  await run(load);
}
const refreshConsult = () => S.reloadConsult && run(S.reloadConsult);
function renderConsult() {
  const D = S.data, m = S.me, v = D.cur, y = window.scrollY, again = S.cxShown === (v?.id ?? "p" + D.pid);
  S.cxShown = v?.id ?? "p" + D.pid;
  const fe = $("#free-text"); if (fe && S.ft?.id === Number(fe.dataset.v)) { S.ft.sel = document.activeElement === fe ? fe.selectionEnd : null; S.ft.scroll = fe.scrollTop; }
  if (S.ft && S.ft.id !== v?.id) { saveText(S.ft.id, S.ft); S.ft = null; }
  if (!S.ft && v && S.drafts?.[v.id] && S.drafts[v.id].saved !== S.drafts[v.id].text) S.ft = S.drafts[v.id];   // restore unsaved text
  if (S.noteVisit !== v?.id) { S.noteVisit = v?.id; S.noteEdit = false; S.allEvents = false; }
  const floatMic = v && (["waiting", "with_doctor"].includes(v.status) || S.recState) && S.ctab !== "note";
  $("#root").innerHTML = `<div class="cx">
    <header class="cx-top">
      <b class="cx-logo">Dictate</b>
      <span class="cx-chip">${esc(S.clinic.name)} · OPD</span>
      <nav class="cx-links">${SCREENS.filter(s => m.screens.includes(s[0]) && s[0] !== "consultation").map(([, h, l]) => `<a href="${h}">${l}</a>`).join("")}</nav>
      <span class="grow"></span>
      ${S.doctors.length > 1 || m.kind !== "doctor" ? `<select class="cx-select" id="cs-doc" data-a="cs-doc" aria-label="Doctor">${S.doctors.map(d => `<option value="${d.id}" ${d.id === D.doctorId ? "selected" : ""}>${esc(d.name)}</option>`).join("")}</select>` : ""}
      <span class="cx-chip solid">${m.kind === "doctor" ? "Doctor" : esc(m.designation || "Staff")}</span>
      <button class="cx-avatar" data-a="account" title="Account">${esc(firstName(m.name)[0].toUpperCase())}</button>
    </header>
    <div class="cx-body ${S.rightCollapsed ? "wide" : ""}">
      <aside class="cx-left">${leftCol()}</aside>
      <main class="cx-center" id="cx-center">${center()}${floatMic ? `<div class="cx-float">${dock(v)}</div>` : v && S.ctab === "note" ? `<div class="cx-float">${noteDock(v)}</div>` : ""}</main>
      ${S.rightCollapsed ? "" : `<aside class="cx-right">${rightCol()}</aside>`}
    </div>
  </div>`;
  if (again) { $(".cx")?.classList.add("re"); window.scrollTo(0, y); }
  restoreFree();
  clearTimeout(S.docT);
  if (v?.documents.some(d => d.ai_status === "processing")) S.docT = setTimeout(refreshConsult, 2000);
}
function restoreFree() {
  const el = $("#free-text"); if (!el || !S.ft || S.ft.id !== Number(el.dataset.v)) return;
  if (S.ft.sel != null) { el.focus({ preventScroll: true }); el.setSelectionRange(S.ft.sel, S.ft.sel); }
  if (S.ft.scroll) el.scrollTop = S.ft.scroll;
}
const ICON = {
  pause: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><rect x="6.5" y="5" width="3.6" height="14" rx="1.4"/><rect x="13.9" y="5" width="3.6" height="14" rx="1.4"/></svg>',
  play: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M8 5.6v12.8a1 1 0 0 0 1.5.86l10.2-6.4a1 1 0 0 0 0-1.72L9.5 4.74A1 1 0 0 0 8 5.6z"/></svg>',
  x: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  stop: '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2.5"/></svg>',
};
const WAVE = [4, 9, 14, 7, 11, 5, 3, 16, 10, 6, 12, 8, 5, 13, 18, 7, 11, 6, 9, 4];
function dock(v) {
  if (S.recState && S.recVisit === v.id) {
    const paused = S.recState === "paused";
    return `<div class="dock rec ${paused ? "paused" : ""}"><button class="dock-cancel" data-a="mic-cancel" aria-label="Cancel dictation" title="Cancel — discard this recording">${ICON.x}</button>
      <div class="dock-wave">${WAVE.map((h, i) => `<i style="--h:${h}px;animation-delay:${(i * 97) % 900}ms"></i>`).join("")}</div>
      <span class="dock-time" id="dock-timer">${fmtClock(recElapsed())}</span>
      <button class="dock-round" data-a="${paused ? "mic-resume" : "mic-pause"}" aria-label="${paused ? "Resume" : "Pause"}" title="${paused ? "Resume" : "Pause"}">${paused ? ICON.play : ICON.pause}</button>
      <button class="dock-stop" data-a="mic-stop" aria-label="Stop" title="Stop">${ICON.stop}</button></div>`;
  }
  return micBtn(v);
}
// Generate note sits at the top beside Follow-up, on every tab, while the visit is under way and the note unsigned.
function genBtn(v) {
  if (v.status !== "with_doctor" || v.note?.status === "signed") return "";
  return `<button class="cx-pill-btn cx-gen" data-a="${v.note ? "cs-redraft" : "cs-draft"}" data-v="${v.id}">Generate note</button>`;
}
const sideBtn = () => !S.rightCollapsed ? "" : `<button class="cx-side-btn" data-a="cs-collapse" aria-label="${S.rightCollapsed ? "Show side panel" : "Hide side panel"}" title="${S.rightCollapsed ? "Show side panel" : "Hide side panel"}"><i></i><i></i></button>`;
function micBtn(v, small) {
  return `<button class="mic-dot ${small ? "sm" : ""}" data-a="cs-mic" data-v="${v.id}" aria-label="Dictate">${icon.mic}</button>`;
}
function leftCol() {
  const D = S.data, q = S.cq.trim().toLowerCase();
  const label = { waiting: "WAITING", with_doctor: "IN VISIT", done: "DONE" };
  const visits = D.today.visits.filter(v => !q || `${v.patient_name} ${v.uhid} ${v.phone}`.toLowerCase().includes(q));
  const inQueue = new Set(D.today.visits.map(v => v.patient_id));
  const others = D.found.filter(p => !inQueue.has(p.id));
  return `<h2 class="cx-kicker">Queue</h2>
    <input class="cx-input" id="cs-q" data-a="cs-q" placeholder="Name, phone or UHID" value="${esc(S.cq)}" autocomplete="off" aria-label="Search">
    <div class="cx-list">${visits.map(v => `<button data-a="cs-open" data-v="${v.id}" aria-current="${v.id === D.cur?.id}">
      <span class="cx-av">${esc(v.token_label)}</span><span class="cx-who"><b>${esc(v.patient_name)}${v.dob ? ", " + ageOf(v.dob) : ""}</b><small>${esc(v.uhid)} · ${esc(v.phone)}</small></span>
      <span class="cx-state st-${v.status}">${label[v.status] || ""}</span></button>`).join("")}
    ${others.map(p => `<button data-a="cs-patient" data-v="${p.id}" aria-current="${!D.cur && p.id === D.pid}">
      <span class="cx-av">${esc(initials(p.name))}</span><span class="cx-who"><b>${esc(p.name)}${p.dob ? ", " + ageOf(p.dob) : ""}</b><small>${esc(p.uhid)} · ${esc(p.phone)}</small></span></button>`).join("")}
    ${!visits.length && !others.length ? `<div class="cx-empty">—</div>` : ""}</div>`;
}
function center() {
  const D = S.data, v = D.cur;
  if (!v) {
    const p = D.profile;
    if (!p) return `<div class="cx-card cx-blank"></div>`;
    const past = p.visits.filter(x => x.status === "done");
    return `<div class="cx-card"><div class="cx-head"><div><h1>${esc(p.name)}${p.dob ? ", " + ageOf(p.dob) : ""}</h1>
      <p class="muted">${{ M: "Male", F: "Female", O: "Other" }[p.sex] || ""} · ${esc(p.uhid)}</p></div><span class="cx-top-right">${sideBtn()}</span></div>
      <div class="cx-events">${past.map(x => `<div><span>•</span><span><b>${longDate(x.date)}</b> · ${esc(x.note?.soap?.A || x.doctor)}</span></div>`).join("") || `<span class="muted">—</span>`}</div></div>`;
  }
  const stateLabel = { waiting: "Waiting", with_doctor: "In visit", done: "Signed", booked: "Booked" }[v.status];
  return `<div class="cx-card">
    <div class="cx-head"><div><h1>${esc(v.patient_name)}${v.age != null ? ", " + v.age : ""}</h1>
</div>
      <span class="cx-top-right">${genBtn(v)}${["with_doctor", "done"].includes(v.status) ? `<button class="cx-pill-btn" data-a="fu-open" data-v="${v.id}">Follow-up</button>` : ""}<span class="cx-status st-${v.status}"><i></i>${stateLabel}</span>${sideBtn()}</span></div>
    <div class="cx-tabrow"><div class="cx-tabs">${CTABS.map(([k, l]) => `<button data-a="cs-tab" data-v="${k}" aria-pressed="${S.ctab === k}">${l}</button>`).join("")}</div>
      ${S.ctab === "brief" ? `<div class="cx-tabs">${BTABS.map(([k, l]) => `<button data-a="cs-btab" data-v="${k}" aria-pressed="${(S.btab || "summary") === k}">${l}</button>`).join("")}</div>` : ""}</div>
    <div class="cx-pane">${({ brief: paneBrief, dictate: paneDictate, note: paneNote })[S.ctab](v)}</div>
  </div>`;
}
