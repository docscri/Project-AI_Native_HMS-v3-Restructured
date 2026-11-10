/* login, onboarding, invite */
const WAVE_H = [14, 26, 40, 22, 48, 34, 18, 52, 30, 44, 20, 38, 54, 28, 16, 42, 50, 24, 36, 46, 18, 32, 52, 26, 40, 20, 48, 30];
const wave = () => `<div class="login-wave" aria-hidden="true">${Array.from({ length: 64 }, (_, i) => `<span style="--h:${WAVE_H[(i * 11) % 28]}px;animation-delay:${(i % 28) * 40}ms"></span>`).join("")}</div>`;
const arrowRight = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
const arrowLeft = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>';
function authPage(inner, cls = "") {
  $("#root").innerHTML = `<main class="login-screen ${cls}"><div class="login-brand">Dictate</div>${wave()}<section class="login-stage">${inner}</section></main>`;
}
function viewLogin() {
  authPage(`<div class="login-card login-home"><form id="login" class="login-fields" novalidate>
      <input class="login-input" id="lg-email" type="email" placeholder="Email" aria-label="Email" autocomplete="username">
      <div class="login-pw"><input class="login-input" id="lg-pw" type="password" placeholder="Password" aria-label="Password" autocomplete="current-password">
        <button class="login-submit glow" type="submit" aria-label="Sign in">${arrowRight}</button></div>
    </form>
    <p class="login-footer"><a class="login-link" href="#/signup">Create account</a><span class="dot-sep">·</span><a class="login-link" href="#/forgot">Forgot password?</a></p></div>`);
  $("#login").addEventListener("submit", e => { e.preventDefault(); $(".login-screen").classList.add("busy"); run(async () => {
    try {
      const r = await api("/auth/login", { body: { email: $("#lg-email").value, password: $("#lg-pw").value }, quiet: true });
      setToken(r.token); await boot(); go("#/");
    } finally { $(".login-screen")?.classList.remove("busy"); }
  }); });
}

let OB = {};
function obFrame(step, inner, next = "Continue") {
  authPage(`<div class="ob-card">
    <div class="ob-top"><button class="ob-back" data-a="ob-back" data-v="${step}">${arrowLeft}<span>Back</span></button><span class="label">Step ${step} of 4</span></div>
    ${inner}
    <div class="ob-foot">${step === 4 ? `<button class="btn" data-a="ob-finish">Skip</button>` : ""}<button class="btn primary glow" data-a="ob-next" data-v="${step}">${next}</button></div></div>`, "ob");
}
function viewOnboarding(step) {
  OB.step = step;
  const me = S.me || {};
  if (step === 1) obFrame(1, `<h1>Create your account</h1>
    ${S.me ? "" : `<div class="seg ob-kind" role="group" aria-label="Account type"><button type="button" data-a="ob-kind" data-v="clinic" aria-pressed="${!OB.solo}">My clinic</button><button type="button" data-a="ob-kind" data-v="solo" aria-pressed="${!!OB.solo}">Just me</button></div>`}
    <label class="field">Name<input id="ob-name" value="${esc(me.name || "")}"></label>
    <div class="grid2"><label class="field">Email<input id="ob-email" type="email" value="${esc(me.email || "")}"></label><label class="field">Phone<input id="ob-phone" value="${esc(me.phone || "")}"></label></div>
    <label class="field">Password<input id="ob-pw" type="password" autocomplete="new-password"></label>
    <label class="choice" ${OB.solo ? "hidden" : ""}><input type="checkbox" id="ob-doc" ${me.kind === "staff" ? "" : "checked"} onchange="document.getElementById('ob-dept-wrap').hidden = !this.checked"><span><b>I am also a doctor here</b></span></label>
    <div id="ob-dept-wrap" ${me.kind === "staff" ? "hidden" : ""}>${deptSelect("ob-dept", me.speciality)}</div>`);
  if (step === 2) obFrame(2, `<h1>Your clinic</h1>
    <label class="field">Clinic name<input id="ob-cname" value="${esc(S.clinic.name)}"></label>
    <label class="field">Phone<input id="ob-cphone" value="${esc(S.clinic.phone)}"></label>
    <label class="field">Address<input id="ob-caddr" value="${esc(S.clinic.address)}"></label>`);
  if (step === 3) obFrame(3, `<h1>Clinic rules</h1>${rulesForm("ob", S.clinic)}`);
  if (step === 4) loadMembersStep();
}
async function loadMembersStep() {
  const ms = (await api("/members")).filter(m => !m.is_owner);
  S.members = ms;
  obFrame(4, `<h1>Your team</h1>
    <div class="ob-team"><button class="btn" data-a="member-add" data-v="doctor">+ Add doctor</button><button class="btn" data-a="member-add" data-v="staff">+ Add staff</button></div>
    ${ms.length ? `<div class="rows">${ms.map(m => `<div class="r q"><b>${m.kind === "doctor" ? "Doctor" : esc(m.designation)}</b><span class="who">${esc(m.name)}</span>${inviteLink(m)}</div>`).join("")}</div>` : ""}`, "Finish setup");
}
const inviteLink = m => m.status === "invited" ? `<button class="btn small" data-a="renew-invite" data-v="${m.id}">Invite link</button>` : `<span class="pill s-paid">Active</span>`;

async function obNext(step) {
  if (step === 1 && S.me) { S.me = await api("/onboarding/owner", { method: "PUT", body: { name: $("#ob-name").value, email: $("#ob-email").value, phone: $("#ob-phone").value, password: $("#ob-pw").value, is_doctor: $("#ob-doc").checked, speciality: $("#ob-dept")?.value || "" } }); S.doctors = await api("/doctors"); return viewOnboarding(2); }
  if (step === 1 && OB.solo) {
    const r = await api("/onboarding/solo", { body: { name: $("#ob-name").value, email: $("#ob-email").value, phone: $("#ob-phone").value, password: $("#ob-pw").value, speciality: $("#ob-dept")?.value || "" } });
    OB = {}; setToken(r.token); await boot(); return go("#/");
  }
  if (step === 1) {
    const r = await api("/onboarding/owner", { body: { name: $("#ob-name").value, email: $("#ob-email").value, phone: $("#ob-phone").value, password: $("#ob-pw").value, is_doctor: $("#ob-doc").checked, speciality: $("#ob-dept")?.value || "General Medicine" } });
    setToken(r.token); const me = await api("/me"); S.me = me.member; S.clinic = me.clinic; return viewOnboarding(2);
  }
  if (step === 2) { S.clinic = await api("/clinic", { method: "PUT", body: { name: $("#ob-cname").value, phone: $("#ob-cphone").value, address: $("#ob-caddr").value } }); return viewOnboarding(3); }
  if (step === 3) { S.clinic = await api("/clinic/rules", { method: "PUT", body: readRules("ob") }); return viewOnboarding(4); }
  return obFinish();
}
async function obFinish() { S.clinic = await api("/onboarding/finish", { body: {} }); S.doctors = await api("/doctors"); toast(`Welcome to ${S.clinic.name}`); go("#/"); }

async function viewInvite(code) {
  await run(async () => {
    const inv = await api("/invites/" + code);
    authPage(`<div class="login-card"><h1 class="login-title">${esc(inv.clinic)}</h1><p class="login-sub">${esc(inv.name)}</p>
      <form class="login-pw" data-form="accept-invite" data-v="${esc(code)}"><input class="login-input" id="iv-pw" type="password" placeholder="New password · 8+ letters & numbers" aria-label="New password" autocomplete="new-password">
      <button class="login-submit glow" type="submit" aria-label="Join">${arrowRight}</button></form></div>`);
  }).then(r => { if (!$(".login-card")) authPage(`<div class="login-card"><h1 class="login-title">Link not valid</h1><p class="login-sub">Ask the clinic for a new invitation.</p><p class="login-footer"><a class="login-link" href="#/login">Back</a></p></div>`); });
}
function viewForgot() {
  authPage(`<div class="login-card"><h1 class="login-title">Reset password</h1>
    <form class="login-pw" data-form="forgot"><input class="login-input" id="fg-email" type="email" placeholder="Email" aria-label="Email" autocomplete="username">
    <button class="login-submit glow" type="submit" aria-label="Send reset link">${arrowRight}</button></form>
    <p class="login-footer"><a class="login-link" href="#/login">Back</a></p></div>`);
}
function viewReset(code) {
  authPage(`<div class="login-card"><h1 class="login-title">New password</h1>
    <form class="login-pw" data-form="reset" data-v="${esc(code)}"><input class="login-input" id="rs-pw" type="password" placeholder="8+ letters & numbers" aria-label="New password" autocomplete="new-password">
    <button class="login-submit glow" type="submit" aria-label="Save password">${arrowRight}</button></form>
    <p class="login-footer"><a class="login-link" href="#/login">Back</a></p></div>`);
}
document.addEventListener("submit", e => {
  const f = e.target.closest("[data-form]"); if (!f) return;
  e.preventDefault(); const kind = f.dataset.form, v = f.dataset.v;
  $(".login-screen")?.classList.add("busy");
  run(async () => {
    try {
      if (kind === "accept-invite") { const r = await api("/invites/accept", { body: { code: v, password: $("#iv-pw").value } }); setToken(r.token); await boot(); go("#/"); }
      if (kind === "reset") { const r = await api("/auth/reset", { body: { code: v, password: $("#rs-pw").value } }); setToken(r.token); await boot(); toast("Password updated"); go("#/"); }
      if (kind === "forgot") {
        const r = await api("/auth/forgot", { body: { email: $("#fg-email").value } });
        authPage(`<div class="login-card"><h1 class="login-title">Check your email</h1><p class="login-sub">${r.email_sent ? "If this email has an account, a reset link is on its way." : "Ask your clinic admin for a reset link."}</p>
          <p class="login-footer"><a class="login-link" href="#/login">Back</a></p></div>`);
      }
    } finally { $(".login-screen")?.classList.remove("busy"); }
  });
});

// Sign-up: own clinic (4 steps) or a doctor who visits clinics (just the account).
document.addEventListener("click", e => {
  const b = e.target.closest('[data-a="ob-kind"]'); if (!b) return;
  OB.solo = b.dataset.v === "solo";
  const keep = ["ob-name", "ob-email", "ob-phone", "ob-pw", "ob-dept"].map(id => [id, $("#" + id)?.value]);
  viewOnboarding(1);
  keep.forEach(([id, v]) => { if (v != null && $("#" + id)) $("#" + id).value = v; });
  if (OB.solo) { $("#ob-dept-wrap").hidden = false; $(".ob-top .label").textContent = ""; }
  $(".ob-foot [data-a=ob-next]").textContent = OB.solo ? "Create account" : "Continue";
});
