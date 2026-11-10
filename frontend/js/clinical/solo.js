/* Solo doctors: one doctor seeing their own patients at several places. Phone and tablet first.
   Home (search, recent, new patient) -> patient (history, start a visit at a place) -> the consultation the app already has. */

function soloShell() {
  const m = S.me;
  if ($("#solo-view")) return;
  $("#root").innerHTML = `<div class="solo">
    <header class="solo-top"><a class="solo-brand" href="#/">Dictate<i>.</i></a><span class="grow"></span>
      <button class="cx-avatar" data-a="account" title="Settings">${esc(firstName(m.name)[0].toUpperCase())}</button></header>
    <main class="solo-view" id="solo-view"><div class="muted">Loading…</div></main></div>`;
}

const soloAge = p => p.dob ? ageOf(p.dob) : "";
const soloWho = p => [soloAge(p), { M: "Male", F: "Female", O: "Other" }[p.sex] || "", p.uhid, p.phone].filter(Boolean).join(" · ");

async function viewSoloHome() {
  const g = S.gen;
  soloShell();
  S.sq = S.sq ?? "";
  await run(async () => {
    const list = await api(`/patients?q=${encodeURIComponent(S.sq)}`);
    if (stale(g)) return;
    $("#solo-view").innerHTML = `
      <div class="solo-hello"><small>${new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</small>
        <h1>Hello, ${esc(firstName(S.me.name).replace(/^Dr\.?$/i, S.me.name))}</h1></div>
      <label class="solo-search"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
        <input id="so-q" data-a="so-q" placeholder="Search patients"${matchMedia("(hover: hover)").matches ? " title=\"Press / to search\"" : ""} value="${esc(S.sq)}" autocomplete="off" aria-label="Search patients"></label>
      <span class="solo-label">${S.sq.trim() ? "Results" : "Recent patients"}</span>
      <div class="solo-list" id="so-list">${list.map(p => `<button class="solo-card" data-a="so-open" data-v="${p.id}">
          <span class="solo-av">${esc(initials(p.name))}</span><span class="solo-who"><b>${esc(p.name)}</b><small>${esc(soloWho(p))}</small></span>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 6l6 6-6 6"/></svg></button>`).join("")
        || `<div class="solo-empty">${S.sq.trim() ? "No match" : "No patients yet"}</div>`}</div>
      <button class="solo-fab" data-a="so-new">+ New patient</button>`;
  });
}

async function viewSoloPatient(id) {
  const g = S.gen;
  soloShell();
  await run(async () => {
    const p = await api(`/patients/${id}`);
    if (stale(g)) return;
    const open = p.visits.find(v => v.status === "with_doctor");
    const past = p.visits.filter(v => ["done", "with_doctor"].includes(v.status));
    $("#solo-view").innerHTML = `
      <a class="solo-back" href="#/">‹ Patients</a>
      <section class="solo-pt"><span class="solo-av big">${esc(initials(p.name))}</span><div><h1>${esc(p.name)}</h1><p>${esc(soloWho(p))}</p></div></section>
      <button class="solo-go" data-a="${open ? "so-continue" : "so-start"}" data-v="${open ? open.id : p.id}">${open ? "Continue visit" : "Start visit"}</button>
      ${past.length ? `<span class="solo-label">Visits</span>` : ""}
      <div class="solo-visits">${past.map(v => `<article class="solo-visit">
          <div class="solo-vtop"><b>${longDate(v.date)}</b>${v.location ? `<span class="solo-place">${esc(v.location)}</span>` : ""}${v.status === "with_doctor" ? `<span class="pill s-with_doctor">In visit</span>` : ""}</div>
          ${v.line ? `<p>${esc(v.line)}</p>` : ""}
          <div class="solo-vbtns">${v.status === "with_doctor" ? ""
            : v.note ? `<button class="btn small" data-a="note-view" data-v="${v.id}">Note</button><button class="btn small" data-a="so-share" data-v="${v.id}">Share</button><button class="btn small" data-a="note-print" data-v="${v.note.id}">Print</button>` : ""}</div>
        </article>`).join("") || ""}</div>`;
  });
}

function openSoloNew() {
  modal(`<h2>New patient</h2>
    <label class="field">Name<input id="sn-name" autocomplete="off"></label>
    <div class="grid2"><label class="field">Age (years)<input id="sn-age" type="number" min="0" max="120" inputmode="numeric"></label>
      <label class="field">Sex<select id="sn-sex"><option value="">—</option><option value="M">Male</option><option value="F">Female</option><option value="O">Other</option></select></label></div>
    <label class="field">Phone (optional)<input id="sn-phone" type="tel" inputmode="tel" placeholder="98470 12345"></label>
    <label class="choice"><input type="checkbox" id="sn-consent"><span><b>Patient consents to records</b></span></label>
    <div class="foot"><button class="btn" data-a="close">Cancel</button><button class="btn primary" data-a="so-save">Save</button></div>`);
  setTimeout(() => $("#sn-name")?.focus(), 50);
}

async function openSoloStart(patientId) {
  const places = await api("/locations");
  M = { kind: "so-start", patientId };
  modal(`<h2>Where?</h2>
    <div class="solo-places">${places.map(l => `<button class="solo-place-btn" data-a="so-go" data-v="${l.id}">${esc(l.name)}</button>`).join("")}
      ${places.length ? "" : `<button class="solo-place-btn ghost" data-a="so-go" data-v="">Skip</button>`}</div>
    <div class="solo-add"><input id="so-place" placeholder="Add place" autocomplete="off"><button class="btn" data-a="so-place-add">Add</button></div>`);
}

async function openPlaces() {
  const places = await api("/locations");
  M = { kind: "places" };
  modal(`<h2>Places</h2>
    <div class="solo-plist">${places.map(l => `<div class="solo-prow"><span>${esc(l.name)}</span><button class="icon-x" data-a="so-place-del" data-v="${l.id}" aria-label="Remove ${esc(l.name)}">×</button></div>`).join("")}</div>
    <div class="solo-add"><input id="so-place" placeholder="Add place" autocomplete="off"><button class="btn" data-a="so-place-add">Add</button></div>`);
}

// What a signed note says, as plain text for WhatsApp or the phone's share sheet.
function noteText(v) {
  const c = v.note.content, lines = [`${S.me.name}`, `${v.patient_name}${v.age != null ? ", " + v.age : ""} · ${longDate(v.date)}`, ""];
  const dx = c.sections ? c.sections.find(s => /diagnos|impression|assessment/i.test(s.title))?.text : c.soap.A;
  const plan = c.sections ? c.sections.find(s => /management/i.test(s.title))?.text : c.soap.P;
  if (dx) lines.push(`Diagnosis: ${dx}`);
  const rx = (c.rx || []).filter(r => r.medicine);
  if (rx.length) lines.push("", "Prescription:", ...rx.map(r => `• ${r.medicine}${r.dose ? " — " + r.dose : ""}${r.duration ? ", " + r.duration : ""}${r.instructions ? " (" + r.instructions + ")" : ""}`));
  if (plan) lines.push("", `Advice: ${plan}`);
  return lines.join("\n");
}

async function shareNote(visitId) {
  const v = await api(`/visits/${visitId}`);
  if (!v.note) return;
  const text = noteText(v);
  if (navigator.share) { try { await navigator.share({ title: `Note · ${v.patient_name}`, text }); return; } catch (e) { if (e.name === "AbortError") return; } }
  const digits = (v.patient_phone || v.phone || "").replace(/\D/g, "");
  const to = digits.length === 10 ? "91" + digits : digits;
  window.open(`https://wa.me/${to}?text=${encodeURIComponent(text)}`, "_blank");
}

document.addEventListener("click", async e => {
  const el = e.target.closest("[data-a]"); if (!el || !S.clinic?.solo) return;
  const a = el.dataset.a, v = el.dataset.v;
  if (!a.startsWith("so-")) return;
  await run(async () => {
    if (a === "so-open") go(`#/p/${v}`);
    if (a === "so-new") openSoloNew();
    if (a === "so-save") {
      const age = $("#sn-age").value.trim(), d = new Date();
      const dob = age ? `${d.getFullYear() - Number(age)}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}` : null;
      const p = await api("/patients", { body: { name: $("#sn-name").value, dob, sex: $("#sn-sex").value || null, phone: $("#sn-phone").value, consent: $("#sn-consent").checked } });
      closeModal(); toast("Patient added"); go(`#/p/${p.id}`);
    }
    if (a === "so-start") await openSoloStart(Number(v));
    if (a === "so-continue") go(`#/consult/${v}`);
    if (a === "so-go") {
      const visit = await api("/visits/quick", { body: { patient_id: M.patientId, location_id: v ? Number(v) : null } });
      closeModal(); S.ctab = "dictate"; go(`#/consult/${visit.id}`);
    }
    if (a === "so-place-add") {
      const name = $("#so-place").value.trim(); if (!name) return;
      await api("/locations", { body: { name } }); toast("Place added");
      M?.kind === "so-start" ? await openSoloStart(M.patientId) : await openPlaces();
    }
    if (a === "so-place-del") { await api(`/locations/${v}`, { method: "DELETE" }); await openPlaces(); }
    if (a === "so-places") await openPlaces();
    if (a === "so-share") await shareNote(Number(v));
  });
});
// Laptop: "/" jumps to the search box on the home screen.
document.addEventListener("keydown", e => {
  if (e.key !== "/" || !S.clinic?.solo || e.target.closest("input,textarea,select,[contenteditable]")) return;
  const q = $("#so-q"); if (q) { e.preventDefault(); q.focus(); }
});
document.addEventListener("input", e => {
  if (e.target.dataset?.a !== "so-q") return;
  S.sq = e.target.value; clearTimeout(S.sqt);
  S.sqt = setTimeout(async () => { await viewSoloHome(); const q = $("#so-q"); if (q) { q.focus(); q.setSelectionRange(q.value.length, q.value.length); } }, 200);
});
