/* schedules */
async function openSchedules(doctorId, own) {
  M = { kind: "sched", own: !!own, doctorId: doctorId || S.doctors[0]?.id, month: (S.date || TODAY).slice(0, 7), days: [], sel: null };
  await loadMonth();
}
async function loadMonth() { M.days = await api(`/schedules/${M.doctorId}?month=${M.month}`); renderSched(); }
function renderSched() {
  const s = M, [y, m] = s.month.split("-").map(Number), lead = new Date(y, m - 1, 1).getDay();
  const scheduleYears = Array.from({ length: 11 }, (_, i) => new Date().getFullYear() - 2 + i);
  const sel = s.days.find(d => d.date === s.sel);
  let editor = "";
  if (sel) {
    const base = sel.edit || sel.schedule || { sessions: S.clinic.sessions, limit_by: S.clinic.limit_by, limit_value: S.clinic.limit_value };
    editor = `<div class="hit choices"><div class="actions" style="justify-content:space-between;align-items:center"><h3>${niceDate(sel.date)}</h3>${sel.override ? `<span class="pill s-with_doctor">Changed</span>` : `<span class="pill s-soft">Clinic hours</span>`}</div>
      <div class="seg"><button data-a="sc-off" data-v="0" aria-pressed="${!sel.off}">Working</button><button data-a="sc-off" data-v="1" aria-pressed="${sel.off}">Off</button></div>
      <div id="so-lim" class="choices" ${sel.off ? 'style="opacity:.35;pointer-events:none"' : ""}>${limitBlock("so", base)}</div>
      <div class="foot"><button class="btn" data-a="sc-reset" ${sel.override ? "" : "disabled"}>Default</button><button class="btn primary" data-a="sc-save">Save</button></div></div>`;
  }
  modal(`<div class="actions" style="justify-content:space-between;align-items:center"><h2>${s.own ? "My schedule" : "Doctor schedules"}</h2>
      ${s.own ? "" : `<select class="input" style="width:auto" id="sc-doc" data-a="sc-doc">${S.doctors.map(d => `<option value="${d.id}" ${d.id === s.doctorId ? "selected" : ""}>${esc(d.name)}</option>`).join("")}</select>`}</div>
    <div class="actions month-picker-wrap"><div class="month-picker"><span>Month</span><select data-a="sc-month-picker" aria-label="Choose schedule month">${Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}" ${i + 1 === m ? "selected" : ""}>${new Date(2000, i, 1).toLocaleDateString("en-IN", { month: "long" })}</option>`).join("")}</select><select data-a="sc-year-picker" aria-label="Choose schedule year">${scheduleYears.map(n => `<option value="${n}" ${n === y ? "selected" : ""}>${n}</option>`).join("")}</select></div></div>
    <div class="cal">${["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(d => `<span class="dow">${d}</span>`).join("")}${"<span></span>".repeat(lead)}
      ${s.days.map(d => `<button class="${d.off ? "off" : ""} ${d.override ? "ovr" : ""}" data-a="sc-day" data-v="${d.date}" aria-pressed="${d.date === s.sel}" ${d.date < TODAY ? "disabled" : ""}><b>${Number(d.date.slice(8))}</b>${d.off ? "Off" : `${d.schedule.start}–${d.schedule.end}`}</button>`).join("")}</div>
    ${s.leave ? leaveEditor() : editor}
    <div class="foot">${s.leave ? "" : `<button class="btn" data-a="lv-open" data-v="doc">Leave</button>${hasAdmin() && !s.own ? `<button class="btn" data-a="lv-open" data-v="all">Clinic holiday</button>` : ""}`}</div>`, true);
}
function leaveEditor() {
  const l = M.leave;
  return `<div class="hit choices"><h3>${l.all ? "Clinic holiday" : `${esc(S.doctors.find(d => d.id === M.doctorId)?.name || "Doctor")} · Leave`}</h3>
    <div class="date-row"><input class="date-pill" aria-label="From" type="date" id="lv-from" min="${TODAY}" value="${l.from}"><input class="date-pill" aria-label="To" type="date" id="lv-to" min="${TODAY}" value="${l.to}"></div>
    <div class="foot"><button class="btn" data-a="lv-save" data-v="0">Working</button><button class="btn primary" data-a="lv-save" data-v="1">${l.all ? "Holiday" : "Leave"}</button></div></div>`;
}
