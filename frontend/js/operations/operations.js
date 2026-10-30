/* operations */
async function viewOps() {
  const g = S.gen;
  S.date = S.date || TODAY;
  S.vf = S.vf || { q: "", st: "", doc: "" };
  const load = async () => {
    if (document.activeElement?.id === "vf-q") return;
    const d = await api(`/operations/day?date=${S.date}`);
    if (stale(g)) return;
    S.data = d;
    const st = d.stats, waiting = d.visits.filter(v => v.status === "waiting"), withDoc = d.visits.filter(v => v.status === "with_doctor");
    view(`<div class="head"><div><h1>Operations</h1><p>${S.date === TODAY ? "Today" : niceDate(S.date)} at ${esc(S.clinic.name)}</p></div><span class="grow"></span>
        <input class="top-date" type="date" data-a="ops-date" value="${S.date}" aria-label="Choose operations date"></div>
      <div class="tiles">
        <div class="tile"><span class="label">Booked</span><span class="big">${st.booked}</span></div>
        <div class="tile"><span class="label">Waiting</span><span class="big">${st.waiting}</span></div>
        <div class="tile"><span class="label">In consultation</span><span class="big">${st.with_doctor}</span></div>
        <div class="tile"><span class="label">Done</span><span class="big">${st.done}</span></div>
      </div>
      <div class="actions quick-actions"><button class="btn" data-a="book">New booking</button><button class="btn" data-a="walkin">Walk-in</button>
        <button class="btn" data-a="register">New patient</button><button class="btn" data-a="schedules">Doctor schedules</button></div>
      <div class="choices" style="gap:18px">
          <section class="panel"><span class="label">Doctors on ${S.date === TODAY ? "today" : niceDate(S.date)}</span>
            ${d.doctors.length ? `<div class="doctors">${d.doctors.map(doctorCard).join("")}</div>` : `<div class="empty">No doctors on this day</div>`}</section>
          <section class="panel"><span class="label">${S.date === TODAY ? "Today's" : "Day's"} visits</span>
            <div class="vf-bar"><input class="input" id="vf-q" placeholder="Search name, phone or UHID" value="${esc(S.vf.q)}" data-a="vf-q" autocomplete="off">
              ${S.doctors.length > 1 ? `<select class="input" data-a="vf-doc" aria-label="Doctor"><option value="">All doctors</option>${S.doctors.map(x => `<option value="${x.id}" ${String(x.id) === S.vf.doc ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select>` : ""}</div>
            <div class="seg vf-seg">${VF.map(([k, l]) => `<button data-a="vf-st" data-v="${k}" aria-pressed="${k === S.vf.st}">${l}</button>`).join("")}</div>
            <div class="rows" id="ops-rows">${opsRows(d.visits)}</div></section>
      </div>`);
  };
  await run(load);
  if (S.date === TODAY && !stale(g)) S.timer = setInterval(() => !M && !stale(g) && run(load), 8000);
}
const VF = [["", "All"], ["booked", "Booked"], ["waiting", "Waiting"], ["with_doctor", "In consultation"], ["done", "Done"], ["no_show", "No-show"]];
function opsRows(vs) {
  const q = S.vf.q.trim().toLowerCase(), digits = q.replace(/\D/g, "");
  const list = vs.filter(v => (!S.vf.st || v.status === S.vf.st) && (!S.vf.doc || String(v.doctor_id) === S.vf.doc)
    && (!q || v.patient_name.toLowerCase().includes(q) || (v.uhid || "").toLowerCase().includes(q) || (digits && (v.phone || "").replace(/\D/g, "").includes(digits))));
  return list.map(v => `<div class="r"><span class="num"><b>${v.token_label || v.expected_time || "—"}</b></span>${S.me.screens.includes("patients") ? `<button class="patient-link who" data-a="pt-open" data-v="${v.patient_id}">${esc(v.patient_name)}</button>` : `<span class="who">${esc(v.patient_name)}</span>`}<span class="muted who doc-col">${esc(v.doctor_name)}${v.session_label ? " · " + v.session_label : ""}</span>${pill(v.status)}</div>`).join("") || `<div class="empty">—</div>`;
}
function doctorCard(d) {
  const s = d.schedule;
  return `<button class="dcard" data-a="open-doctor" data-v="${d.id}">
    <div class="line"><span class="actions" style="gap:10px;align-items:center"><span class="letter">${d.letter}</span><h3>${esc(d.name)}</h3></span></div>
    <div class="muted" style="font-size:14px">${hoursOf(s)}</div>
    <div class="capacity-line"><span>Capacity</span><b class="num">${d.used}/${s.max_patients}</b></div>
    <div class="meter"><i style="width:${Math.min(100, (d.used / s.max_patients) * 100)}%"></i></div>
  </button>`;
}

async function viewQueue(doctorId) {
  const g = S.gen;
  S.date = S.date || TODAY;
  const load = async () => {
    const q = await api(`/operations/queue?doctor_id=${doctorId}&date=${S.date}`);
    const wl = await api(`/waitlist?doctor_id=${doctorId}&date=${S.date}`);
    if (stale(g)) return;
    S.data = q;
    const cols = [["booked", "Booked"], ["waiting", "Waiting"], ["with_doctor", "With doctor"], ["done", "Done"]];
    const s = q.schedule;
    view(`<div class="head"><div><a href="#/ops" class="back-link">${arrowLeft}<span>Back</span></a><h1>${esc(q.doctor.name)}</h1>
        <p>${s ? `${hoursOf(s)} · ${s.limit_by === "minutes" ? s.minutes_per_patient + " min per patient" : "up to " + s.max_patients + " patients"}` : "Off"}</p></div><span class="grow"></span>
        <input class="top-date" type="date" data-a="ops-date" value="${S.date}" aria-label="Choose queue date"></div>
      <div class="actions quick-actions"><button class="btn" data-a="book" data-v="${doctorId}">New booking</button><button class="btn" data-a="walkin" data-v="${doctorId}">Walk-in</button>
        ${s ? s.sessions.filter(x => q.columns.booked.some(v => v.session_start === x.key)).map(x => `<button class="btn" data-a="end-session" data-v="${doctorId}" data-s="${x.key}">End ${s.sessions.length > 1 ? x.label.toLowerCase() + " " : ""}session</button>`).join("") : ""}</div>
      <div class="board">${cols.map(([k, l]) => `<section class="col"><header>${pill(k).replace(STATUS[k], l)}<span class="muted num">${q.columns[k].length}</span></header>
        ${q.columns[k].map((v, i, l) => qCard(v, i, l)).join("")}</section>`).join("")}</div>
      ${wl.items.length ? `<section class="panel"><span class="label">Waitlist</span><div class="rows">${wl.items.map((w, i) => `<div class="r wl-row"><span class="num muted">${i + 1}</span><span class="who"><b>${esc(w.patient_name)}</b></span><span class="muted">${esc(w.phone || w.uhid)}</span>
          <span class="actions" style="gap:6px"><button class="btn small dark" data-a="wl-book" data-v="${w.id}" ${wl.open ? "" : "disabled"}>Book</button><button class="icon-x" data-a="wl-del" data-v="${w.id}" aria-label="Remove">×</button></span></div>`).join("")}</div></section>` : ""}
      ${q.not_seen.length ? `<section class="panel"><span class="label">Not seen</span><div class="rows">${q.not_seen.map(v => `<div class="r q" style="grid-template-columns:minmax(0,1fr) auto"><span>${esc(v.patient_name)}</span>${pill(v.status)}</div>`).join("")}</div></section>` : ""}`);
  };
  await run(load);
  if (S.date === TODAY && !stale(g)) S.timer = setInterval(() => !M && !stale(g) && run(load), 8000);
}
function qCard(v, i, list) {
  const tok = v.token_label ? `<span class="tok chip">${v.token_label}</span>` : `<span class="tok none">No token yet</span>`;
  const clip = `<button class="btn small" data-a="upload" data-v="${v.id}" aria-label="Add document">📎${v.doc_count ? " " + v.doc_count : ""}</button>`;
  const sess = (v.session_label ? `<span class="pill s-soft">${v.session_label}</span>` : "") + (v.follow_up_of ? `<span class="pill s-with_doctor">Follow-up</span>` : "");
  const paid = v.paid_at ? `<span class="pill s-paid">${v.amount_paid ? `${rupees(v.amount_paid)} · ${(v.payment_method || "").toUpperCase()}` : "Waived"}</span>` : "";
  const refunded = v.refund_amount && v.paid_at ? `<span class="pill s-no_show">Refunded ${rupees(v.refund_amount)}</span>` : "";
  const more = v.paid_at || (v.status === "waiting" && !v.is_walk_in) ? `<button class="btn small icon-btn" data-a="v-more" data-v="${v.id}" aria-label="More">⋯</button>` : "";
  let meta = sess, acts = "";
  if (v.status === "booked") {
    meta += (v.expected_time ? `<span>${S.clinic.limit_by === "minutes" ? "" : "~"}${v.expected_time}</span>` : "") + (v.late ? `<span class="pill s-waiting">Late</span>` : "");
    acts = `<div class="acts-row"><button class="btn small dark" data-a="arrive" data-v="${v.id}">Arrived</button><button class="btn small icon-btn" data-a="v-more" data-v="${v.id}" aria-label="More">⋯</button></div><div class="acts-row"><button class="btn small" data-a="late" data-v="${v.id}" aria-pressed="${v.late}">Late</button><button class="btn small" data-a="resched" data-v="${v.id}">Reschedule</button></div>`;
  } else if (v.status === "waiting") {
    const same = list.filter(x => x.session_start === v.session_start), k = same.indexOf(v);
    meta += `${paid}${refunded}${v.is_walk_in ? `<span class="pill s-soft">Walk-in</span>` : ""}<span>since ${(v.arrived_at || "").slice(11, 16)}</span>`;
    acts = `<button class="btn small icon-btn" data-a="q-move" data-v="${v.id}" data-d="up" aria-label="Move up" ${k === 0 ? "disabled" : ""}>↑</button><button class="btn small icon-btn" data-a="q-move" data-v="${v.id}" data-d="down" aria-label="Move down" ${k === same.length - 1 ? "disabled" : ""}>↓</button>${clip}${more}`;
  } else {
    meta += paid + refunded;
    acts = more;
  }
  return `<article class="card"><div class="top"><b>${esc(v.patient_name)}</b>${tok}</div><div class="meta"><span class="mono">${esc(v.uhid)}</span>${meta}</div>${acts ? `<div class="acts">${acts}</div>` : ""}</article>`;
}
const refresh = () => route();
