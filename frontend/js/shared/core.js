/* Hash routes, one state object, event delegation on data-a. */
"use strict";

const S = { token: null, me: null, clinic: null, doctors: [], date: null, data: null, timer: null, rec: null };
try { S.token = localStorage.getItem("clinic.token"); } catch {}

/* helpers */
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const TODAY = iso(new Date());
const addDays = (s, n) => { const d = new Date(s + "T00:00"); d.setDate(d.getDate() + n); return iso(d); };
const niceDate = s => new Date(s + "T00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
const longDate = s => new Date(s.slice(0, 10) + "T00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
const initials = n => n.replace(/^Dr\.?\s*/i, "").split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
const ageOf = dob => { if (!dob) return ""; const b = new Date(dob), t = new Date(); let a = t.getFullYear() - b.getFullYear(); if (t < new Date(t.getFullYear(), b.getMonth(), b.getDate())) a--; return a; };
const firstName = n => n.replace(/^Dr\.?\s*/i, "").trim().split(/\s+/)[0] || "User";
const STATUS = { booked: "Booked", waiting: "Waiting", with_doctor: "In consultation", done: "Done", no_show: "No-show", cancelled: "Cancelled" };
const pill = st => `<span class="pill s-${st}">${STATUS[st] || st}</span>`;
const rupees = n => "₹" + Number(n || 0).toLocaleString("en-IN");
const hoursOf = s => (s.sessions?.length ? s.sessions : [s]).map(x => `${x.start}–${x.end}`).join(" · ");
const openReceipt = id => openPrint(`/visits/${id}/receipt`);
// Print pages are fetched with the login header and written into the new tab, so the token never appears in a URL.
async function openPrint(path) {
  const w = window.open("", "_blank");   // opened inside the click so pop-up blockers allow it
  if (!w) return toast("Allow pop-ups for this site to print.", true);
  w.document.write('<p style="font:16px system-ui;padding:24px;color:#555">Loading…</p>');
  try {
    const res = await fetch("/api" + path, { headers: { Authorization: "Bearer " + S.token } });
    const html = res.headers.get("content-type")?.includes("text/html") ? await res.text()
      : `<p style="font:16px system-ui;padding:24px">${esc((await res.json().catch(() => ({}))).detail || "Could not open this page.")}</p>`;
    w.document.open(); w.document.write(html); w.document.close();
  } catch { w.close(); toast("Could not open the page. Check the connection.", true); }
}
const CANCEL_REASONS = ["Patient asked", "Doctor unavailable", "Booked by mistake"];
const RESCHED_REASONS = ["Patient asked", "Doctor unavailable", "Clinic change"];
const REFUND_REASONS = ["Charged twice", "Visit not done", "Fee changed"];
const reasonChips = (list, cur, a) => `<div class="seg reason-seg">${list.map(r => `<button data-a="${a}" data-v="${esc(r)}" aria-pressed="${r === cur}">${r}</button>`).join("")}</div>`;
const feeTile = fee => `<div class="tk fee"><small>Fee</small><b id="pay-due">${rupees(fee)}</b></div>`;
function payBlock(fee, pay, feeShown) {
  return `<div class="pay-box">${feeShown ? "" : `<div class="tiles-row">${feeTile(fee)}</div>`}
    <div class="pay-line"><div class="seg" id="pay-seg">${[["cash", "Cash"], ["upi", "UPI"], ["card", "Card"], ["waive", "Waive"]].map(([m, l]) => `<button data-a="pay" data-v="${m}" aria-pressed="${m === pay}">${l}</button>`).join("")}</div>
    <label class="field" id="pay-disc-wrap" ${pay === "waive" ? "hidden" : ""}>Discount (₹)<input type="number" min="0" max="${fee}" id="pay-disc" data-a="pay-disc" data-fee="${fee}" value=""></label></div></div>`;
}
function readPay(fee) {
  const pay = M.pay, why = $("#pay-why")?.value.trim() || "";
  if (pay === "waive") return { payment_method: null, discount: fee, discount_reason: why };
  return { payment_method: pay, discount: Number($("#pay-disc")?.value) || 0, discount_reason: why };
}
const paidDone = (title, v) => `<h2>${title}</h2><div class="result">${esc(v.patient_name)}${v.token_label ? ` · token ${v.token_label}` : ""} · ${rupees(v.amount_paid)}${v.payment_method ? " · " + v.payment_method.toUpperCase() : ""}</div>
  <div class="foot"><button class="btn" data-a="receipt" data-v="${v.id}">Receipt</button><button class="btn primary" data-a="close-refresh">Done</button></div>`;
const toMin = t => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
function limitsOf(start, end, by, val) {
  const len = Math.max(1, toMin(end) - toMin(start)); val = Math.max(1, Number(val) || 1);
  return by === "minutes" ? { max: Math.max(1, Math.floor(len / val)), per: val } : { max: val, per: Math.round(len / val) };
}
const icon = {
  ops: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>',
  patients: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>',
  consult: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12h4l2-5 4 10 2-5h6"/></svg>',
  admin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></svg>',
  mic: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>',
};

async function api(path, opts = {}) {
  const headers = { ...(S.token ? { Authorization: "Bearer " + S.token } : {}) };
  let body = opts.body;
  if (body && !(body instanceof FormData)) { headers["Content-Type"] = "application/json"; body = JSON.stringify(body); }
  const res = await fetch("/api" + path, { method: opts.method || (body ? "POST" : "GET"), headers, body });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && !opts.quiet && S.token) { endLocal(); throw new Error(data.detail || "Session ended. Log in again."); }
  if (!res.ok) {
    const d = data.detail;
    const err = new Error(Array.isArray(d) ? `Check ${String(d[0]?.loc?.slice(-1)[0] || "the form").replace(/_/g, " ")}.` : d || "Something went wrong.");
    err.status = res.status; throw err;
  }
  return data;
}
function toast(msg, err) {
  $("#toast").innerHTML = `<div class="toast ${err ? "err" : ""}" role="status">${esc(msg)}</div>`;
  clearTimeout(toast.t); toast.t = setTimeout(() => ($("#toast").innerHTML = ""), err ? 4200 : 2600);
}
async function run(fn) { try { return await fn(); } catch (e) { toast(e.message, true); } }
function modal(html, wide) {
  const old = $("#modal .modal"), top = old ? old.scrollTop : 0, scrim = $("#modal .scrim")?.scrollTop || 0;
  $("#modal").innerHTML = html ? `<div class="scrim" data-a="scrim"><div class="modal ${wide ? "wide" : ""} ${old ? "re" : ""}" role="dialog" aria-modal="true">${/data-a="close(-refresh)?"[^>]*>(Cancel|Close)</.test(html) ? "" : `<button class="icon-x modal-x" data-a="close-refresh" aria-label="Close">×</button>`}${html}</div></div>` : "";
  if (html && old) { $("#modal .modal").scrollTop = top; $("#modal .scrim").scrollTop = scrim; }
}
const closeModal = () => { modal(""); M = null; };
const go = h => { if (location.hash === h) route(); else location.hash = h; };
function setToken(t) { S.token = t; try { t ? localStorage.setItem("clinic.token", t) : localStorage.removeItem("clinic.token"); } catch {} }
function endLocal() { setToken(null); S.me = null; stopTimers(); closeModal(); go("#/login"); }
async function logout() { if (S.token) await fetch("/api/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + S.token } }).catch(() => {}); endLocal(); }
function stopTimers() { clearInterval(S.timer); S.timer = null; clearTimeout(S.docT); if (S.rec) { const r = S.rec; S.rec = null; try { r.stop(); } catch {} } S.recState = null; clearInterval(S.recT); }

/* routing */
const SCREENS = [["operations", "#/ops", "Operations", icon.ops], ["patients", "#/patients", "Patients", icon.patients],
  ["consultation", "#/consult", "Consultation", icon.consult], ["administration", "#/admin", "Administration", icon.admin]];

async function boot() {
  if (!S.token) return route();
  await run(async () => {
    const r = await api("/me");
    S.me = r.member; S.clinic = r.clinic; S.doctors = await api("/doctors");
    api("/dictation").then(d => { S.dictBy = d.provider; S.aiOn = d.ai; }, () => {});
  });
  route();
}
window.addEventListener("hashchange", route);

async function route() {
  stopTimers();
  S.gen = (S.gen || 0) + 1;
  const [path, query] = (location.hash.slice(1) || "/").split("?");
  const parts = path.split("/").filter(Boolean);
  if (parts[0] === "invite") return viewInvite(parts[1]);
  if (parts[0] === "reset") return viewReset(parts[1]);
  if (parts[0] === "forgot" && !S.me) return viewForgot();
  if (!S.token || !S.me) return parts[0] === "signup" ? viewOnboarding(1) : viewLogin();
  if (!S.clinic.onboarded) return viewOnboarding(2);
  const allowed = SCREENS.filter(s => S.me.screens.includes(s[0]));
  const map = { ops: "operations", patients: "patients", consult: "consultation", admin: "administration" };
  if (!parts[0] || !map[parts[0]] || !S.me.screens.includes(map[parts[0]])) return go(allowed[0]?.[1] || "#/patients");
  if (parts[0] !== "consult") shell(parts[0]);
  const q = new URLSearchParams(query || "");
  if (parts[0] === "ops") return parts[1] === "doctor" ? viewQueue(Number(parts[2])) : viewOps();
  if (parts[0] === "patients") return viewPatients(parts[1] ? Number(parts[1]) : null);
  if (parts[0] === "consult") return viewConsult(parts[1] ? Number(parts[1]) : null, q.get("doctor"), q.get("patient"));
  if (parts[0] === "admin") return viewAdmin(parts[1] === "members" ? "team" : parts[1] || "clinic", parts[2]);
}

function shell(active) {
  const m = S.me;
  if ($("#view") && S.shellFor === active) return;   // keep the frame to avoid flash/scroll
  S.shellFor = active;
  $("#root").innerHTML = `<div class="app">
    <nav class="nav" aria-label="Main">
      <div class="brand"><b>Dictate</b><span>${esc(S.clinic.name)}</span></div>
      ${SCREENS.filter(s => m.screens.includes(s[0])).map(([k, h, l, i]) => `<a href="${h}" ${h.slice(2) === active ? 'aria-current="page"' : ""}>${i}${l}</a>`).join("")}
      <div class="me"><button class="me-open" data-a="account" title="Account"><span class="avatar">${esc(firstName(m.name)[0].toUpperCase())}</span><b>${esc(firstName(m.name))}</b></button><button class="logout-icon" data-a="logout" aria-label="Log out" title="Log out"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 17l5-5-5-5M15 12H3M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4"/></svg></button></div>
    </nav>
    <div class="stage"><main class="surface" id="view"><div class="muted">Loading…</div></main></div></div>`;
}
const pageKey = () => location.hash.replace(/^(#\/patients)\/\d+/, "$1");
const view = (html, g) => {
  if (g !== undefined && g !== S.gen) return;
  const v = $("#view"); if (!v) return;
  const same = S.viewKey === pageKey(), top = v.scrollTop;
  v.innerHTML = html;
  v.scrollTop = same ? top : 0;
  S.viewKey = pageKey();
};
const stale = g => g !== S.gen;
