/* team & collections */
const TEAM_TABS = [["members", "Members"], ["today", "Today"], ["leave", "Leave"], ["register", "Register"]];
const subTabs = (tab, cur) => `<div class="seg sub-seg">${TEAM_TABS.map(([k, l]) => `<button data-a="ad-sub" data-t="${tab}" data-v="${k}" aria-pressed="${k === cur}">${l}</button>`).join("")}</div>`;
const ATT = { present: ["Present", "s-paid"], late: ["Late", "s-waiting"], half: ["Half day", "s-waiting"], absent: ["Absent", "s-no_show"], leave: ["Leave", "s-soft"], off: ["Off", "s-soft"], due: ["Not in yet", "s-booked"] };
const LEAVE_ST = { pending: ["Pending", "s-waiting"], approved: ["Approved", "s-paid"], rejected: ["Rejected", "s-no_show"], cancelled: ["Cancelled", "s-cancelled"] };
const hhmm = ts => ts ? ts.slice(11, 16) : "—";
const roleOf = m => m.kind === "doctor" ? (m.speciality || "Doctor") : (m.designation || "Staff");
const monthPick = (a, ym) => { const [y, m] = ym.split("-").map(Number); return `<div class="month-picker"><span>Month</span><select data-a="${a}-m" aria-label="Month">${Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}" ${i + 1 === m ? "selected" : ""}>${new Date(2000, i, 1).toLocaleDateString("en-IN", { month: "long" })}</option>`).join("")}</select><select data-a="${a}-y" aria-label="Year">${Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - 4 + i).map(n => `<option ${n === y ? "selected" : ""}>${n}</option>`).join("")}</select></div>`; };
const person = m => `<span class="mname"><span class="avatar sm">${esc(initials(m.name))}</span><span class="pname"><b>${esc(m.name)}</b><small>${esc(m.role ?? roleOf(m))}</small></span></span>`;

async function teamView(sub) {
  S.adm = S.adm || { month: TODAY.slice(0, 7) };
  if (sub === "today") {
    const t = await api("/team/today");
    return `${subTabs("team", "today")}<section class="panel"><span class="label">${niceDate(t.date)}</span><div class="rows">${t.people.map(p => {
      const [l, c] = ATT[p.status] || [p.status, "s-soft"];
      const edit = p.status === "leave" || !p.working && p.status === "off" ? "" : `<div class="seg mini">${[["present", "Present"], ["late", "Late"], ["absent", "Absent"]].map(([k, x]) => `<button data-a="att-mark" data-m="${p.id}" data-v="${k}" aria-pressed="${p.status === k}">${x}</button>`).join("")}</div>`;
      return `<div class="r team-row">${person(p)}<span class="pill ${c}">${l}</span><span class="muted num">${p.check_in ? hhmm(p.check_in) + (p.check_out ? " – " + hhmm(p.check_out) : "") : p.working && p.start ? "from " + p.start : ""}</span>${edit}</div>`;
    }).join("") || `<div class="empty">—</div>`}</div></section>`;
  }
  if (sub === "leave") {
    const ls = await api(`/leave?month=${S.adm.month}`), pend = ls.filter(l => l.status === "pending"), rest = ls.filter(l => l.status !== "pending");
    const line = l => { const [st, c] = LEAVE_ST[l.status]; return `<div class="r leave-row">${person({ ...l, role: l.reason || "" })}
      <span class="num">${niceDate(l.start_date)}${l.end_date !== l.start_date ? " – " + niceDate(l.end_date) : ""}</span><span class="muted">${l.days} day${l.days > 1 ? "s" : ""}</span>
      <span class="actions" style="gap:6px;justify-content:flex-end">${l.status === "pending" ? `<button class="btn small dark" data-a="lv-approve" data-v="${l.id}">Approve</button><button class="btn small" data-a="lv-reject" data-v="${l.id}">Reject</button>` : `<span class="pill ${c}">${st}</span>${l.status === "approved" && l.end_date >= TODAY ? `<button class="btn small icon-btn" data-a="lv-cancel" data-v="${l.id}" aria-label="Cancel leave">×</button>` : ""}`}</span></div>`; };
    return `${subTabs("team", "leave")}<div class="bar-row">${monthPick("lvm", S.adm.month)}</div>
      ${pend.length ? `<section class="panel"><span class="label">Waiting for approval</span><div class="rows">${pend.map(line).join("")}</div></section>` : ""}
      <section class="panel"><span class="label">${new Date(S.adm.month + "-01T00:00").toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</span><div class="rows">${rest.map(line).join("") || `<div class="empty">—</div>`}</div></section>`;
  }
  if (sub === "register") {
    const r = await api(`/team/register?month=${S.adm.month}`);
    S.reg = r;
    return `${subTabs("team", "register")}<div class="bar-row">${monthPick("rgm", S.adm.month)}<span class="grow"></span><button class="btn" data-a="reg-print">Print</button></div>
      <section class="panel scroll"><table class="t"><thead><tr><th>Name</th><th>Working days</th><th>Present</th><th>Late</th><th>Leave</th><th>Absent</th></tr></thead><tbody>
      ${r.people.map(p => `<tr><td>${person(p)}</td><td class="num">${p.working}</td><td class="num">${p.present + p.late + p.half}</td><td class="num">${p.late}</td><td class="num">${p.leave}</td><td class="num">${p.absent}</td></tr>`).join("")}</tbody></table></section>`;
  }
  return "";
}
function moneyTiles(t) {
  const m = t.by_method, st = (k, v) => `<div class="st"><small>${k}</small><b>${v}</b></div>`;
  return `<div class="stat-strip"><div class="st net"><small>Net</small><b>${rupees(t.net)}</b></div>${st("Cash", rupees(m.cash))}${st("UPI", rupees(m.upi))}${st("Card", rupees(m.card))}
    <span class="st-gap"></span>${st("Visits", t.visits)}${st("Refunds", rupees(t.refunded))}${st("Discounts", rupees(t.discounts))}${st("Waived", t.waived)}</div>`;
}
async function moneyView() {
  S.mon = S.mon || { from: TODAY, to: TODAY };
  const f = S.mon, t = await api(`/collections?start=${f.from}&end=${f.to}`);
  S.monData = t;
  const dash = n => n ? n : `<span class="muted">—</span>`;
  const tot = t.by_doctor.reduce((a, d) => ({ seen: a.seen + d.seen, walk_ins: a.walk_ins + d.walk_ins, no_shows: a.no_shows + d.no_shows, collected: a.collected + d.collected, refunded: a.refunded + d.refunded, net: a.net + d.net }), { seen: 0, walk_ins: 0, no_shows: 0, collected: 0, refunded: 0, net: 0 });
  return `<div class="bar-row money-bar"><input class="date-pill" aria-label="From" type="date" id="mr-from" max="${TODAY}" value="${f.from}" data-a="mr-range"><input class="date-pill" aria-label="To" type="date" id="mr-to" max="${TODAY}" value="${f.to}" data-a="mr-range"><button class="btn" data-a="mr-print">Print</button></div>
    <section class="panel">${moneyTiles(t)}</section>
    <section class="panel scroll"><span class="label">By doctor</span><table class="t doc-table"><thead><tr><th>Doctor</th><th class="n">Patients seen</th><th class="n">Walk-ins</th><th class="n">No-shows</th><th class="n">Collected</th><th class="n">Refunds</th><th class="n">Net</th></tr></thead><tbody>
      ${t.by_doctor.map(d => `<tr><td>${person({ name: d.name, role: d.speciality || "Doctor" })}</td><td class="n"><b>${d.seen}</b></td><td class="n">${dash(d.walk_ins)}</td><td class="n">${dash(d.no_shows)}</td><td class="n">${rupees(d.collected)}</td><td class="n">${d.refunded ? rupees(d.refunded) : dash(0)}</td><td class="n"><b>${rupees(d.net)}</b></td></tr>`).join("") || `<tr><td colspan="7" class="muted">—</td></tr>`}
      ${t.by_doctor.length > 1 ? `<tr class="tot-row"><td><b>Total</b></td><td class="n"><b>${tot.seen}</b></td><td class="n">${tot.walk_ins}</td><td class="n">${tot.no_shows}</td><td class="n">${rupees(tot.collected)}</td><td class="n">${rupees(tot.refunded)}</td><td class="n"><b>${rupees(tot.net)}</b></td></tr>` : ""}</tbody></table></section>
    <section class="panel scroll"><span class="label">By date</span><table class="t doc-table"><thead><tr><th>Date</th><th class="n">Visits</th><th class="n">Cash</th><th class="n">UPI</th><th class="n">Card</th><th class="n">Refunds</th><th class="n">Net</th></tr></thead><tbody>
      ${t.days.map(d => `<tr><td><b>${niceDate(d.date)}</b></td><td class="n">${d.visits}</td><td class="n">${rupees(d.by_method.cash)}</td><td class="n">${rupees(d.by_method.upi)}</td><td class="n">${rupees(d.by_method.card)}</td><td class="n">${d.refunded ? rupees(d.refunded) : dash(0)}</td><td class="n"><b>${rupees(d.net)}</b></td></tr>`).join("") || `<tr><td colspan="7" class="muted">—</td></tr>`}</tbody></table></section>`;
}
function printCollections() {
  const t = S.monData, f = S.mon, w = window.open("", "_blank"), m = t.by_method;
  const span = f.from === f.to ? niceDate(f.from) : `${niceDate(f.from)} – ${niceDate(f.to)}`;
  const doc = "All doctors";
  w.document.write(`<!doctype html><meta charset="utf-8"><title>Collections · ${span}</title><link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
    <style>@page{size:A4;margin:14mm}*{box-sizing:border-box}body{font-family:Manrope,sans-serif;color:#0B1411;margin:0;background:#E8F1EC;-webkit-print-color-adjust:exact;print-color-adjust:exact}
    .page{max-width:860px;margin:28px auto;background:#F6FAF7;border-radius:28px;padding:40px 44px}header{display:flex;justify-content:space-between;align-items:flex-start;background:#0B1411;color:#E8F1EC;border-radius:22px;padding:22px 26px}
    h1{margin:0;font-size:22px;font-weight:800}small{color:#9FB1A9;font-size:12.5px;font-weight:600;display:block;margin-top:4px}.lime{color:#B6F36B;font-weight:800;font-size:16px}
    .tiles{display:flex;gap:10px;margin:22px 0 6px}.tk{flex:1;background:#E8F1EC;border-radius:16px;padding:12px 16px}.tk.big{background:#0B1411;color:#B6F36B}.tk small{color:#6B7C75;margin:0 0 2px;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase}.tk b{font-size:20px}
    h2{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#6B7C75;margin:26px 0 10px}table{width:100%;border-collapse:separate;border-spacing:0;font-size:14px}th{text-align:left;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:#6B7C75;padding:0 12px 8px}
    td{padding:11px 12px}.n{text-align:right}tr:nth-child(even) td{background:#E8F1EC}tr:nth-child(even) td:first-child{border-radius:12px 0 0 12px}tr:nth-child(even) td:last-child{border-radius:0 12px 12px 0}tr.tot td{background:#0B1411;color:#E8F1EC;font-weight:800}tr.tot td:first-child{border-radius:12px 0 0 12px}tr.tot td:last-child{border-radius:0 12px 12px 0;color:#B6F36B}
    @media print{body{background:#fff}.page{margin:0;padding:0;background:#fff;border-radius:0;max-width:none}}</style>
    <div class="page"><header><div><h1>${esc(S.clinic.name)}</h1><small>Collections · ${esc(doc)}</small></div><div style="text-align:right"><span class="lime">${span}</span><small>${t.visits} paid visits</small></div></header>
    <div class="tiles"><div class="tk big"><small style="color:#9FB1A9">Net</small><b>${rupees(t.net)}</b></div><div class="tk"><small>Cash</small><b>${rupees(m.cash)}</b></div><div class="tk"><small>UPI</small><b>${rupees(m.upi)}</b></div><div class="tk"><small>Card</small><b>${rupees(m.card)}</b></div><div class="tk"><small>Refunds</small><b>${rupees(t.refunded)}</b></div></div>
    <h2>By doctor</h2><table><tr><th>Doctor</th><th class="n">Patients seen</th><th class="n">Walk-ins</th><th class="n">No-shows</th><th class="n">Collected</th><th class="n">Refunds</th><th class="n">Net</th></tr>
    ${t.by_doctor.map(d => `<tr><td><b>${esc(d.name)}</b></td><td class="n">${d.seen}</td><td class="n">${d.walk_ins}</td><td class="n">${d.no_shows}</td><td class="n">${rupees(d.collected)}</td><td class="n">${rupees(d.refunded)}</td><td class="n"><b>${rupees(d.net)}</b></td></tr>`).join("")}
    <tr class="tot"><td>Total</td><td class="n">${t.by_doctor.reduce((a, d) => a + d.seen, 0)}</td><td class="n">${t.by_doctor.reduce((a, d) => a + d.walk_ins, 0)}</td><td class="n">${t.by_doctor.reduce((a, d) => a + d.no_shows, 0)}</td><td class="n">${rupees(t.collected)}</td><td class="n">${rupees(t.refunded)}</td><td class="n">${rupees(t.net)}</td></tr></table></div><script>onload=()=>setTimeout(print,300)<\/script>`);
  w.document.close();
}
function openLeave(memberId) {
  const admin = S.me.is_admin && !memberId?.self;
  M = { kind: "leave-new" };
  modal(`<h2>Leave</h2>
    ${admin ? `<label class="field">Person<select id="lv-who">${(S.members || []).filter(m => m.status === "active").map(m => `<option value="${m.id}" ${m.id === memberId ? "selected" : ""}>${esc(m.name)}</option>`).join("")}</select></label>` : ""}
    <div class="date-row"><input class="date-pill" aria-label="From" type="date" id="lvn-from" value="${TODAY}"><input class="date-pill" aria-label="To" type="date" id="lvn-to" value="${TODAY}"></div>
    <label class="field">Reason<input id="lvn-why"></label>
    <div class="foot"><button class="btn primary" data-a="lvn-save">${S.me.is_admin ? "Save" : "Request"}</button></div>`);
}
function printRegister() {
  const r = S.reg, w = window.open("", "_blank");
  const mon = new Date(r.month + "-01T00:00").toLocaleDateString("en-IN", { month: "long", year: "numeric" });
  w.document.write(`<!doctype html><meta charset="utf-8"><title>Register · ${mon}</title><link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
    <style>@page{size:A4 landscape;margin:14mm}*{box-sizing:border-box}body{font-family:Manrope,sans-serif;color:#0B1411;margin:0;background:#E8F1EC;-webkit-print-color-adjust:exact;print-color-adjust:exact}
    .page{max-width:980px;margin:28px auto;background:#F6FAF7;border-radius:28px;padding:40px 44px}
    header{display:flex;justify-content:space-between;align-items:flex-start;background:#0B1411;color:#E8F1EC;border-radius:22px;padding:22px 26px;margin-bottom:26px}
    h1{margin:0;font-size:22px;font-weight:800}small{color:#9FB1A9;font-size:12.5px;font-weight:600;display:block;margin-top:4px}.lime{color:#B6F36B;font-weight:800;font-size:16px}
    table{width:100%;border-collapse:separate;border-spacing:0;font-size:14.5px}th{text-align:left;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:#6B7C75;padding:0 14px 8px}
    td{padding:12px 14px}td.n,th.n{text-align:center}tr:nth-child(even) td{background:#E8F1EC}tr:nth-child(even) td:first-child{border-radius:12px 0 0 12px}tr:nth-child(even) td:last-child{border-radius:0 12px 12px 0}
    td small{color:#6B7C75;margin:0}@media print{body{background:#fff}.page{margin:0;padding:0;background:#fff;border-radius:0;max-width:none}}</style>
    <div class="page"><header><div><h1>${esc(S.clinic.name)}</h1><small>Working days register</small></div><div style="text-align:right"><span class="lime">${mon}</span><small>${r.people.length} ${r.people.length === 1 ? "person" : "people"}</small></div></header>
    <table><tr><th>Name</th><th class="n">Working days</th><th class="n">Present</th><th class="n">Late</th><th class="n">Leave</th><th class="n">Absent</th></tr>${r.people.map(p => `<tr><td><b>${esc(p.name)}</b><small>${esc(p.role || "")}</small></td><td class="n">${p.working}</td><td class="n">${p.present + p.late + p.half}</td><td class="n">${p.late}</td><td class="n">${p.leave}</td><td class="n">${p.absent}</td></tr>`).join("")}</table></div><script>onload=()=>setTimeout(print,300)<\/script>`);
  w.document.close();
}
