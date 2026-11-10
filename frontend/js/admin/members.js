/* members */
function openMember(kind, m) {
  M = { kind: "member", mkind: m?.kind || kind, m };
  const k = M.mkind;
  const screens = m ? m.screens : k === "doctor" ? ["patients", "consultation"] : ["operations", "patients"];
  const locked = m?.is_owner;
  modal(`<div class="mb-head"><div class="avatar big">${esc(initials(m?.name || "?"))}</div><div><h2>${m ? esc(m.name) : k === "doctor" ? "New doctor" : "New staff"}</h2>
      ${m ? `<span class="pill ${m.status === "active" ? "s-paid" : m.status === "invited" ? "s-waiting" : "s-no_show"}">${{ active: "Active", invited: "Invited", inactive: "Inactive" }[m.status]}</span>` : ""}</div></div>
    <div class="grid2"><label class="field">Name<input id="mb-name" value="${esc(m?.name || "")}"></label><label class="field">Phone<input id="mb-phone" value="${esc(m?.phone || "")}"></label></div>
    <label class="field">Email<input id="mb-email" type="email" value="${esc(m?.email || "")}"></label>
    <div class="grid2">${k === "doctor" ? `<div class="dept-row">${deptSelect("mb-spec", m?.speciality)}<button class="btn small" data-a="tpl-view" data-from="mb-spec">Preview template</button></div>`
        : `<label class="field">Designation<select id="mb-spec">${["Receptionist", "Nurse", "IT", "Other"].map(d => `<option ${m?.designation === d ? "selected" : ""}>${d}</option>`).join("")}</select></label>`}</div>
    ${k === "doctor" ? `<div class="fee-row"><div class="seg"><button data-a="mb-fee-mode" data-v="clinic" aria-pressed="${m?.fee_override == null}">Clinic fee</button><button data-a="mb-fee-mode" data-v="own" aria-pressed="${m?.fee_override != null}">Own fee</button></div>
      <label class="field" id="mb-fee-wrap" ${m?.fee_override == null ? "hidden" : ""}>Fee (₹)<input id="mb-fee" type="number" min="0" value="${m?.fee_override ?? S.clinic.fee}"></label></div>` : ""}
    ${m ? `<div class="grid2"><label class="field">Joining date<input type="date" id="mb-joined" value="${esc(m.joined_on || "")}"></label><label class="field">ID number<input id="mb-idno" value="${esc(m.id_number || "")}"></label></div>
    <div class="grid2"><label class="field">Emergency contact<input id="mb-emerg" value="${esc(m.emergency_contact || "")}"></label><label class="field">Address<input id="mb-addr" value="${esc(m.address || "")}"></label></div>
    ${k === "staff" ? `<div class="rule-group"><span class="rule-label">Working days</span><div class="day-dots">${["S", "M", "T", "W", "T", "F", "S"].map((d, i) => `<label><input type="checkbox" id="mb-d${i}" ${(m.work_days ? JSON.parse(m.work_days) : S.clinic.days).includes(i) ? "checked" : ""}><span>${d}</span></label>`).join("")}</div></div>
      <div class="grid2"><label class="field">Starts<input type="time" id="mb-ws" value="${esc(m.work_start || S.clinic.start || "09:00")}"></label><label class="field">Ends<input type="time" id="mb-we" value="${esc(m.work_end || S.clinic.end || "17:00")}"></label></div>` : ""}` : ""}
    <div class="field">Screens</div>
    <div class="days">${SCREENS.filter(([key]) => key !== "consultation" || k === "doctor").map(([key, , l]) => `<label><input type="checkbox" id="mb-s-${key}" ${screens.includes(key) || locked ? "checked" : ""} ${locked || (key === "administration" && !m?.is_admin) ? "disabled" : ""}>${l}</label>`).join("")}</div>
    <div class="toggles"><label class="choice"><input type="checkbox" id="mb-admin" data-a="mb-admin" ${m?.is_admin ? "checked" : ""} ${locked ? "disabled" : ""}><span><b>Admin access</b></span></label>
    ${m && !m.is_owner && m.status !== "invited" ? `<label class="choice"><input type="checkbox" id="mb-active" ${m.status === "active" ? "checked" : ""}><span><b>Active</b></span></label>` : ""}</div>
    <div class="foot">${m && !m.is_owner ? `<button class="btn danger" data-a="mb-remove" style="margin-right:auto">Remove</button>` : ""}${m?.status === "invited" ? `<button class="btn" data-a="renew-invite" data-v="${m.id}">Invite link</button>` : ""}${m?.status === "active" && !m.is_owner ? `<button class="btn" data-a="reset-link" data-v="${m.id}">Reset password</button>` : ""}${m && k === "doctor" ? `<button class="btn" data-a="mb-schedule" data-v="${m.id}">Schedule</button>` : ""}
      <button class="btn primary" data-a="mb-save">${m ? "Save" : "Send invitation"}</button></div>`);
}
async function saveMember() {
  const { mkind, m } = M, own = $('[data-a="mb-fee-mode"][data-v="own"]')?.getAttribute("aria-pressed") === "true";
  const body = { name: $("#mb-name").value, phone: $("#mb-phone").value, email: $("#mb-email").value,
    screens: SCREENS.map(s => s[0]).filter(k => $("#mb-s-" + k)?.checked), is_admin: $("#mb-admin").checked,
    ...(mkind === "doctor" ? { speciality: $("#mb-spec").value, fee_override: own ? Number($("#mb-fee").value) || 0 : null } : { designation: $("#mb-spec").value }) };
  if (m) {
    if (!m.is_owner) body.kind = mkind;
    if (mkind === "doctor" && !own) body.clear_fee = true;
    if (m.is_owner) { delete body.screens; delete body.is_admin; }
    if ($("#mb-active")) body.status = $("#mb-active").checked ? "active" : "inactive";
    Object.assign(body, { joined_on: $("#mb-joined").value || null, id_number: $("#mb-idno").value, emergency_contact: $("#mb-emerg").value, address: $("#mb-addr").value });
    if (mkind === "staff") Object.assign(body, { work_days: [0, 1, 2, 3, 4, 5, 6].filter(i => $("#mb-d" + i).checked), work_start: $("#mb-ws").value, work_end: $("#mb-we").value });
    await api(`/members/${m.id}`, { method: "PATCH", body });
    toast("Saved");
  } else {
    const r = await api("/members", { body: { ...body, kind: mkind } });
    copyLink(`${location.origin}/#/invite/${r.invite_code}`, `Invitation created for ${r.name} · link copied`);
  }
  S.doctors = await api("/doctors"); closeModal();
  if (OB.step === 4 && !S.clinic.onboarded) loadMembersStep(); else route();
}
function openShare(what, id, code, emailOn) {
  const m = (S.members || []).find(x => x.id === id), back = M?.kind === "member" ? M : null;
  const link = `${location.origin}/#/${what}/${code}`;
  M = { kind: "share", what, id, code, link, back };
  modal(`<h2>${what === "invite" ? "Invite link" : "Password reset"}</h2>
    <div class="pt-chip share-chip"><span class="avatar">${esc(initials(m?.name || "?"))}</span><span class="pt-main"><b>${esc(m?.name || "")}</b><span class="pt-meta"><span>${esc(m?.email || "")}</span><span>${what === "invite" ? "7 days" : "2 hours"}</span></span></span></div>
    <div class="share-row">${emailOn ? `<button class="share-opt" data-a="share-email"><b>Email link</b></button>` : ""}
      <button class="share-opt" data-a="share-copy"><b>Copy link</b></button></div>
    <div class="foot"><button class="btn primary" data-a="close">Done</button></div>`);
}
function copyLink(link, msg) {
  navigator.clipboard?.writeText(link).then(() => toast(msg), () => { M = { kind: "link" }; modal(`<h2>Share this link</h2><label class="field">Link<input readonly value="${esc(link)}" onfocus="this.select()"></label><div class="foot"><button class="btn primary" data-a="close">Done</button></div>`); });
}
async function openAccount() {
  const m = S.me, doc = m.kind === "doctor";
  const [att, myLeave] = await Promise.all([api("/attendance/me").catch(() => ({})), api("/leave?mine=true").catch(() => [])]);
  M = { kind: "account" };
  const upcoming = myLeave.filter(l => l.end_date >= TODAY && ["pending", "approved"].includes(l.status));
  modal(`<div class="mb-head"><div class="avatar big">${esc(initials(m.name))}</div><div><h2>${esc(m.name)}</h2><span class="muted">${esc(doc ? m.speciality || "Doctor" : m.designation || "Staff")}</span></div>
      <span class="grow"></span>${S.clinic.solo ? "" : att.check_out ? `<span class="pill s-paid">${hhmm(att.check_in)} – ${hhmm(att.check_out)}</span>` : att.check_in ? `<button class="btn small" data-a="att-out">Check out · in ${hhmm(att.check_in)}</button>` : `<button class="btn small dark" data-a="att-in">Check in</button>`}</div>
    ${upcoming.length ? `<div class="rows my-leave">${upcoming.map(l => `<div class="r my-leave-row"><span class="num">${niceDate(l.start_date)}${l.end_date !== l.start_date ? " – " + niceDate(l.end_date) : ""}</span><span class="who muted">${esc(l.reason || "")}</span><span class="actions" style="gap:6px"><span class="pill ${LEAVE_ST[l.status][1]}">${LEAVE_ST[l.status][0]}</span><button class="btn small icon-btn" data-a="lv-cancel" data-v="${l.id}" aria-label="Cancel leave">×</button></span></div>`).join("")}</div>` : ""}
    <div class="grid2"><label class="field">Name<input id="ac-name" value="${esc(m.name)}"></label>${doc ? deptSelect("ac-role", m.speciality) : `<label class="field">Designation<input id="ac-role" value="${esc(m.designation || "")}"></label>`}</div>
    <div class="grid2"><label class="field">Email<input id="ac-email" type="email" value="${esc(m.email)}"></label><label class="field">Phone<input id="ac-phone" value="${esc(m.phone || "")}"></label></div>
    <label class="field">Current password<input id="ac-cur" type="password" autocomplete="current-password"></label>
    <div class="grid2"><label class="field">New password<input id="ac-new" type="password" autocomplete="new-password"></label><label class="field">Repeat new password<input id="ac-new2" type="password" autocomplete="new-password"></label></div>
    <div class="foot"><button class="btn danger" data-a="logout" style="margin-right:auto">Log out</button>${S.clinic.solo ? `<button class="btn" data-a="so-places">Places</button><button class="btn" data-a="tpl-view" data-from="ac-role">Template</button>`
      : `<button class="btn" data-a="my-leave">Leave</button>${doc ? `<button class="btn" data-a="my-schedule">My schedule</button><button class="btn" data-a="tpl-view" data-from="ac-role">Template</button>` : ""}`}<button class="btn primary" data-a="ac-save">Save</button></div>`);
}
function copyInvite(code, msg) {
  const link = `${location.origin}/#/invite/${code}`;
  navigator.clipboard?.writeText(link).then(() => toast(msg || "Invite link copied"), () => toast(link));
}

// A department's OPD case-sheet template, in the app's own style: the vitals strip, then each section with its prompts.
async function openTemplate(dept) {
  const t = await api(`/departments/template?name=${encodeURIComponent(deptOf(dept))}`);
  // A layer of its own above any open form, so closing it leaves that form (and unsaved edits) as it was.
  const layer = document.getElementById("tpl-layer") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "tpl-layer" }));
  layer.innerHTML = `<div class="scrim" data-a="tpl-close"><div class="modal wide" role="dialog" aria-modal="true" aria-label="Note template">
    <button class="icon-x modal-x" data-a="tpl-close" aria-label="Close">×</button><div class="tp"><div class="tp-top"><div><span class="tp-kicker">Note template</span><h2>${esc(t.title)}</h2>
      <span class="muted">The OPD case sheet for this department: its sections, in order.</span></div></div>
    <div class="tp-body">
      <div class="tp-strip"><span class="tp-label">Patient</span>${t.header.patient.map(x => `<span class="tp-chip">${esc(x)}</span>`).join("")}</div>
      <div class="tp-strip"><span class="tp-label">Vitals</span>${t.header.vitals.map(x => `<span class="tp-chip">${esc(x)}</span>`).join("")}</div>
      <div class="tp-secs">${t.sections.map((s, i) => `<div class="soap-sec"><b class="soap-tile">${i + 1}</b><div><span class="soap-label">${esc(s.title)}</span>
        <ul class="tp-prompts">${s.prompts.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div></div>`).join("")}</div>
      ${t.note ? `<p class="tp-note">${esc(t.note)}</p>` : ""}
    </div></div></div></div>`;
}
