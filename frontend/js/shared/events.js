/* events */
document.addEventListener("click", e => {
  const t = e.target.closest("[data-a]"); if (!t) return;
  const a = t.dataset.a, v = t.dataset.v;
  if (a === "scrim") { if (e.target === t && M?.kind !== "sched") closeModal(); return; }
  if (["lim", "mb-admin", "mr-range", "lvm-m", "lvm-y", "rgm-m", "rgm-y", "free-text", "up-file", "mg-q", "vf-q", "vf-doc", "pay-disc", "bk-q", "pt-q", "cs-q", "bk-date", "bk-doc", "sc-doc", "sc-month-picker", "sc-year-picker", "cs-doc"].includes(a)) return;
  e.preventDefault();
  const D = S.data;
  run(async () => {
    switch (a) {
      case "logout": logout(); break;
      case "ob-next": await obNext(Number(v)); break;
      case "ob-finish": await obFinish(); break;
      case "ob-back": { const st = Number(v); if (st === 1) { if (S.me) { logout(); } else go("#/login"); } else viewOnboarding(st - 1); break; }
      case "renew-invite": { const r = await api(`/members/${v}/invite`, { body: {} }); openShare("invite", Number(v), r.invite_code, r.email_enabled); break; }
      case "reset-link": { const r = await api(`/members/${v}/reset-link`, { body: {} }); openShare("reset", Number(v), r.code, r.email_enabled); break; }
      case "share-copy": copyLink(M.link, M.what === "invite" ? "Invite link copied · valid 7 days" : "Reset link copied · valid 2 hours"); break;
      case "share-email": { const r = M.what === "invite" ? await api(`/members/${M.id}/invite/email`, { body: {} }) : await api(`/members/${M.id}/reset-link/email`, { body: { code: M.code } });
        toast(`${M.what === "invite" ? "Invite" : "Reset link"} emailed to ${r.email}`); break; }
      case "account": await openAccount(); break;
      case "ac-save": {
        const nw = $("#ac-new").value;
        if (nw && nw !== $("#ac-new2").value) return toast("New passwords don't match", true);
        const doc = S.me.kind === "doctor", role = $("#ac-role").value;
        const me = await api("/me", { method: "PUT", body: { name: $("#ac-name").value, email: $("#ac-email").value, phone: $("#ac-phone").value, speciality: doc ? role : "", designation: doc ? "" : role } });
        if (nw) await api("/auth/change-password", { body: { current: $("#ac-cur").value, new: nw } });
        S.me = me; S.doctors = await api("/doctors"); S.shellFor = null; closeModal(); toast("Saved"); route(); break; }
      case "my-schedule": await openSchedules(S.me.id, true); break;
      case "pw-save": {
        if ($("#ac-new").value !== $("#ac-new2").value) return toast("New passwords don't match", true);
        await api("/auth/change-password", { body: { current: $("#ac-cur").value, new: $("#ac-new").value } }); closeModal(); toast("Password changed"); break; }
      case "copy-invite": copyInvite(v); break;
      case "day": S.date = addDays(S.date, Number(v)); route(); break;
      case "open-doctor": go(`#/ops/doctor/${v}`); break;
      case "book": openBooking("book", { doctorId: v ? Number(v) : undefined }); break;
      case "walkin": openBooking("walk", { doctorId: v ? Number(v) : undefined }); break;
      case "book-another": openBooking("book", { doctorId: M.doctorId }); break;
      case "resched": { const vis = D.columns.booked.find(x => x.id === Number(v)); openBooking("resched", { visit: vis, doctorId: vis.doctor_id, patient: { id: vis.patient_id, name: vis.patient_name, uhid: vis.uhid, phone: vis.phone } }); break; }
      case "close": closeModal(); break;
      case "close-refresh": closeModal(); refresh(); break;
      case "bk-pick": M.patient = M.results.find(r => r.id === Number(v)); renderBooking(); break;
      case "bk-clear": M.patient = null; M.q = ""; M.results = []; renderBooking(); break;
      case "pick-token": M.token = Number(v); renderBooking(); break;
      case "bk-pay": M.pay = v; renderBooking(); break;
      case "bk-confirm": await confirmBooking(); break;
      case "bk-wait": { await api("/waitlist", { body: { patient_id: M.patient.id, doctor_id: M.doctorId, date: M.date, session: M.session } });
        M.done = `<h2>Added to waitlist</h2><div class="result">${esc(M.patient.name)} · ${niceDate(M.date)}</div><div class="foot"><button class="btn primary" data-a="close-refresh">Done</button></div>`; renderBooking(); break; }
      case "wl-book": { const r = await api(`/waitlist/${v}/book`, { body: {} }); toast(`Booked · ${r.token_label || r.patient_name}`); refresh(); break; }
      case "wl-del": await api(`/waitlist/${v}`, { method: "DELETE" }); refresh(); break;
      case "fu-open": M = { kind: "followup", id: Number(v), date: addDays(TODAY, 7) }; renderFollowUp(); break;
      case "fu-pick": M.date = addDays(TODAY, Number(v)); renderFollowUp(); break;
      case "fu-go": { const d = $("#fu-date").value || M.date; const r = await api(`/visits/${M.id}/follow-up`, { body: { date: d } });
        M = { kind: "done" }; modal(`<h2>${r.waitlisted ? "Day is full" : "Follow-up booked"}</h2><div class="result">${niceDate(d)}${r.waitlisted ? " · added to waitlist" : r.token_label ? ` · token ${r.token_label}` : ""}</div><div class="foot"><button class="btn primary" data-a="close">Done</button></div>`); break; }
      case "register": openRegister(v); break;
      case "rg-use": { const p = M.same.find(x => x.id === Number(v));
        if (M.back) { const back = M.back; M = back; M.patient = p; renderBooking(); } else { closeModal(); location.hash.startsWith("#/consult") ? go(`#/consult?doctor=${S.data.doctorId}&patient=${p.id}`) : go(`#/patients/${p.id}`); }
        break; }
      case "pt-merge": M = { kind: "merge", id: Number(v), q: "", results: [] }; renderMerge(); break;
      case "mg-pick": M.other = M.results.find(x => x.id === Number(v)); renderMerge(); break;
      case "mg-go": { const p = await api(`/patients/${M.id}/merge`, { body: { other_id: M.other.id } }); closeModal(); toast(`Merged into ${p.uhid}`); go(`#/patients/${p.id}`); route(); break; }
      case "rg-back": { const back = M.back; M = back; renderBooking(); break; }
      case "rg-save": case "rg-new": {
        const f = a === "rg-new" ? M.form : { name: $("#rg-name").value, phone: $("#rg-phone").value, dob: $("#rg-dob").value || null, sex: $("#rg-sex").value, address: $("#rg-addr").value, consent: $("#rg-consent").checked };
        if (!f.consent) return toast("Tick patient consent", true);
        if (a === "rg-save") {
          const same = await api(`/patients/check?name=${encodeURIComponent(f.name)}&phone=${encodeURIComponent(f.phone)}&dob=${f.dob || ""}`);
          if (same.length) {
            M.form = f; M.same = same;
            modal(`<h2>Same person?</h2><div class="pick">${same.map(x => `<button data-a="rg-use" data-v="${x.id}"><span><b>${esc(x.name)}</b> · ${esc(x.phone || "—")}${x.dob ? " · " + ageOf(x.dob) : ""} ${esc(x.sex || "")}</span><span class="mono muted">${esc(x.uhid)}</span></button>`).join("")}</div>
              <div class="foot"><button class="btn primary" data-a="rg-new">New patient</button></div>`);
            break;
          }
        }
        const p = await api("/patients", { body: f });
        toast(`Registered ${p.uhid}`);
        if (M.back) { const back = M.back; M = back; M.patient = p; renderBooking(); } else { closeModal(); location.hash.startsWith("#/consult") ? go(`#/consult?doctor=${S.data.doctorId}&patient=${p.id}`) : go(`#/patients/${p.id}`); }
        break; }
      case "arrive": openArrive([...D.columns.booked].find(x => x.id === Number(v))); break;
      case "pay": M.pay = v; document.querySelectorAll("#pay-seg button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v)); payShow(); break;
      case "arrive-paid": { const r = await api(`/visits/${M.v.id}/arrive`, { body: readPay(M.v.fee) }); M = { kind: "done" }; modal(paidDone("Sent to Waiting", r)); break; }
      case "receipt": openReceipt(v); break;
      case "v-more": { const vis = Object.values(D.columns).flat().find(x => x.id === Number(v)); M = { kind: "more" };
        modal(`<h2>${esc(vis.patient_name)}</h2><div class="more-list">${vis.paid_at ? `<button class="btn" data-a="receipt" data-v="${v}">Receipt</button>` : ""}
          ${(vis.refundable || 0) > 0 ? `<button class="btn" data-a="refund" data-v="${v}">Refund</button>` : ""}
          ${vis.status === "waiting" && !vis.is_walk_in ? `<button class="btn" data-a="undo-arrival" data-v="${v}">Undo arrival</button>` : ""}
          ${vis.status === "booked" ? `<button class="btn" data-a="upload" data-v="${v}">Add document</button><button class="btn danger" data-a="cancel" data-v="${v}">Cancel booking</button>` : ""}</div>
          `); break; }
      case "refund": openRefund(Object.values(D.columns).flat().find(x => x.id === Number(v))); break;
      case "rf-reason": $("#rf-why").value = v; document.querySelectorAll('[data-a="rf-reason"]').forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v)); break;
      case "refund-go": { const r = await api(`/visits/${M.v.id}/refund`, { body: { amount: Number($("#rf-amt").value) || null, reason: $("#rf-why").value } }); closeModal(); toast(`Refunded ${rupees(r.refund_amount)}`); refresh(); break; }
      case "q-move": await api(`/visits/${v}/queue?direction=${t.dataset.d}`, { body: {} }); refresh(); break;
      case "late": await api(`/visits/${v}/late`, { body: {} }); refresh(); break;
      case "undo-arrival": { closeModal(); const r = await api(`/visits/${v}/undo-arrival`, { body: {} }); toast(`${r.patient_name} back to Booked${r.refund_amount ? " · refund " + rupees(r.refund_amount) : ""}`); refresh(); break; }
      case "bk-session": M.session = v; M.token = null; await loadAvail(); break;
      case "bk-reason": M.reason = v; renderBooking(); break;
      case "vf-st": S.vf.st = v; document.querySelectorAll('[data-a="vf-st"]').forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v));
        { const r = $("#ops-rows"); if (r && S.data?.visits) r.innerHTML = opsRows(S.data.visits); } break;
      case "cancel": { const vis = D.columns.booked.find(x => x.id === Number(v)); M = { kind: "cancel", id: v, reason: "" };
        modal(`<h2>Cancel booking · ${esc(vis.patient_name)}</h2>${reasonChips(CANCEL_REASONS, "", "cn-reason")}<div class="foot"><button class="btn danger" data-a="cancel-go" data-v="${v}">Cancel booking</button></div>`); break; }
      case "cn-reason": M.reason = v; document.querySelectorAll('[data-a="cn-reason"]').forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v)); break;
      case "cancel-go": await api(`/visits/${v}/cancel`, { body: { reason: M.reason || "" } }); closeModal(); toast("Booking cancelled"); refresh(); break;
      case "end-session": { const r = await api(`/operations/end-session?doctor_id=${v}&date=${S.date}&session=${t.dataset.s || ""}`, { body: {} }); toast(`${r.no_shows} marked as no-show`); refresh(); break; }
      case "ses-add": case "ses-del": { const pp = t.dataset.p, vals = readLimit(pp);
        if (a === "ses-add") { const last = vals.sessions[vals.sessions.length - 1]; const hm = m => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`, st = Math.min(toMin(last.end) + 60, 22 * 60); vals.sessions.push({ start: hm(st), end: hm(Math.min(st + 180, 23 * 60 + 59)) }); }
        else vals.sessions.splice(Number(v), 1);
        $(`#${pp}-lim`).innerHTML = limitBlock(pp, vals); break; }
      case "lv-open": M.leave = { from: M.sel && M.sel >= TODAY ? M.sel : TODAY, to: M.sel && M.sel >= TODAY ? M.sel : TODAY, all: v === "all" }; renderSched(); break;
      case "lv-who": M.leave.from = $("#lv-from").value; M.leave.to = $("#lv-to").value; M.leave.all = v === "all"; renderSched(); break;
      case "lv-save": { const l = M.leave, from = $("#lv-from").value, to = $("#lv-to").value || from;
        const r = await api("/schedules/leave", { body: { start_date: from, end_date: to, doctor_id: l.all ? null : M.doctorId, off: v === "1" } });
        toast(`${r.days} day${r.days > 1 ? "s" : ""} ${v === "1" ? (M.leave.all ? "holiday" : "leave") : "working"}${r.bookings_affected ? ` · ${r.bookings_affected} booking${r.bookings_affected > 1 ? "s" : ""} to move` : ""}`, r.bookings_affected > 0);
        M.leave = null; await loadMonth(); break; }
      case "upload": openUpload(Number(v)); break;
      case "upload-go": { const f = $("#up-file").files[0]; if (!f) return toast("Choose a file first", true); await doUpload(M.visitId, f); closeModal(); location.hash.startsWith("#/consult") ? refreshConsult() : refresh(); break; }
      case "schedules": await openSchedules(D?.doctor?.id); break;
      case "sc-month": { const [y, m] = M.month.split("-").map(Number); const d = new Date(y, m - 1 + Number(v), 1); M.month = iso(d).slice(0, 7); M.sel = null; await loadMonth(); break; }
      case "sc-day": M.sel = v; renderSched(); break;
      case "sc-off": { const d = M.days.find(x => x.date === M.sel); d.off = v === "1"; d.schedule = d.schedule || null; renderSched(); break; }
      case "sc-save": { const d = M.days.find(x => x.date === M.sel);
        await api(`/schedules/${M.doctorId}/${M.sel}`, { method: "PUT", body: d.off ? { is_off: true } : { is_off: false, ...readLimit("so") } }); toast("Saved " + niceDate(M.sel)); await loadMonth(); break; }
      case "sc-reset": await api(`/schedules/${M.doctorId}/${M.sel}`, { method: "DELETE" }); await loadMonth(); break;
      case "member-add": openMember(v); break;
      case "member-edit": { const m = S.members.find(x => x.id === Number(v)); openMember(m.kind, m); break; }
      case "mb-fee-mode": { document.querySelectorAll('[data-a="mb-fee-mode"]').forEach(x => x.setAttribute("aria-pressed", x.dataset.v === v)); $("#mb-fee-wrap").hidden = v !== "own"; break; }
      case "mb-remove": { const m = M.m; const r = await api(`/members/${m.id}`, { method: "DELETE" }); toast(r.removed ? `${m.name} removed` : `${m.name} has visit history, set to inactive`); S.doctors = await api("/doctors"); closeModal(); route(); break; }
      case "mb-save": await saveMember(); break;
      case "ad-tab": go(`#/admin/${v}`); break;
      case "ad-sub": go(`#/admin/${t.dataset.t}/${v}`); break;
      case "att-mark": await api(`/attendance/${t.dataset.m}/${TODAY}`, { method: "PUT", body: { status: v, check_in: v === "absent" ? null : new Date().toTimeString().slice(0, 5) } }); route(); break;
      case "lv-new": if (!S.members) S.members = await api("/members"); openLeave(); break;
      case "lvn-save": { const who = $("#lv-who")?.value;
        const r = await api("/leave", { body: { start_date: $("#lvn-from").value, end_date: $("#lvn-to").value || $("#lvn-from").value, reason: $("#lvn-why").value, member_id: who ? Number(who) : null } });
        closeModal(); toast(r.status === "pending" ? "Leave requested" : r.bookings_affected ? `Leave saved · ${r.bookings_affected} booking${r.bookings_affected > 1 ? "s" : ""} to move` : "Leave saved", r.bookings_affected > 0); route(); break; }
      case "lv-approve": case "lv-reject": case "lv-cancel": { const r = await api(`/leave/${v}/${a.slice(3)}`, { body: {} });
        toast({ approve: "Approved", reject: "Rejected", cancel: "Leave cancelled" }[a.slice(3)] + (r.bookings_affected ? ` · ${r.bookings_affected} booking${r.bookings_affected > 1 ? "s" : ""} to move` : ""), r.bookings_affected > 0);
        M?.kind === "account" ? openAccount() : route(); break; }
      case "reg-print": printRegister(); break;
      case "mr-print": printCollections(); break;
      case "att-in": case "att-out": await api(`/attendance/check-${a === "att-in" ? "in" : "out"}`, { body: {} }); toast(a === "att-in" ? "Checked in" : "Checked out"); openAccount(); break;
      case "my-leave": openLeave({ self: true }); break;
      case "mb-schedule": closeModal(); await openSchedules(Number(v)); break;
      case "ad-details": S.shellFor = null; S.clinic = await api("/clinic", { method: "PUT", body: { name: $("#ad-name").value, phone: $("#ad-phone").value, address: $("#ad-addr").value } }); toast("Saved"); route(); break;
      case "ad-rules": S.clinic = await api("/clinic/rules", { method: "PUT", body: readRules("ad") }); toast("Rules saved."); route(); break;
      case "pt-open": go(`#/patients/${v}`); break;
      case "pt-edit": openPatientEdit(await api(`/patients/${v}`)); break;
      case "pe-save": await api(`/patients/${M.id}`, { method: "PATCH", body: { name: $("#pe-name").value, phone: $("#pe-phone").value, dob: $("#pe-dob").value || null, sex: $("#pe-sex").value, address: $("#pe-addr").value } }); closeModal(); toast("Saved"); route(); break;
      case "cs-tab": await flushText(); if (D.cur?.note && $("#soap-S")) D.cur.note.content = readNote(); S.ctab = v; renderConsult(); break;
      case "cs-side": S.cside = v; renderConsult(); break;
      case "cs-btab": S.btab = v; renderConsult(); break;
      case "cs-allev": S.allEvents = !S.allEvents; renderConsult(); break;
      case "chart-open": openChart(D.cur.brief.charts[Number(v)]); break;
      case "cs-left": S.cleft = v; refreshConsult(); break;
      case "cs-patient": go(`#/consult?doctor=${D.doctorId}&patient=${v}`); break;
      case "cs-draft-go": if (!(await flushText(Number(v)))) break; await api(`/visits/${v}/note/draft`, { body: {} }); S.ctab = "note"; toast("Draft ready."); refreshConsult(); break;
      case "note-sign-ro": await api(`/notes/${v}`, { method: "PUT", body: D.cur.note.content }); await api(`/notes/${v}/sign`, { body: {} }); toast("Signed. Visit complete."); refreshConsult(); break;
      case "cs-next-mic": { const r = await api(`/consultation/next?doctor_id=${v}`, { body: {} }); S.ctab = "dictate"; await new Promise(res => { const once = () => { window.removeEventListener("hashchange", once); setTimeout(res, 300); }; window.addEventListener("hashchange", once); go(`#/consult/${r.id}?doctor=${v}`); }); startMic(r.id); break; }
      case "cs-collapse": S.rightCollapsed = !S.rightCollapsed; renderConsult(); break;
      case "mic-pause": pauseMic(); break;
      case "mic-resume": resumeMic(); break;
      case "mic-stop": await stopMic(); break;
      case "note-edit": S.noteEdit = true; renderConsult(); break;
      case "note-done": { const n = D.cur.note; await api(`/notes/${n.id}`, { method: "PUT", body: readNote() }); S.noteEdit = false; toast("Saved"); refreshConsult(); break; }
      case "cs-mic": {
        const cur = D.cur;
        if (S.recState) { await stopMic(); break; }
        if (S.dictBy === "deepgram") S.audioCtx = audioContext();
        if (cur.status === "waiting") { await api(`/visits/${cur.id}/start`, { body: {} }); }
        if (S.ctab === "brief") S.ctab = "dictate";
        await S.reloadConsult(); startMic(cur.id); break; }
      case "cs-next": { const r = await api(`/consultation/next?doctor_id=${v}`, { body: {} }); S.ctab = "brief"; go(`#/consult/${r.id}?doctor=${v}`); break; }
      case "cs-open": go(`#/consult/${v}?doctor=${D.doctorId}`); break;
      case "cs-start": await api(`/visits/${v}/start`, { body: {} }); refreshConsult(); break;
      case "cs-brief": await api(`/visits/${v}/brief`, { body: {} }); toast("Brief updated"); refreshConsult(); break;
      case "cs-redraft":   // asks first only when the doctor changed the draft by hand
        if (D.cur?.note?.edited) { modal(`<h2>Replace your edits?</h2><div class="foot"><button class="btn danger" data-a="cs-redraft-go" data-v="${v}">Replace</button></div>`); break; }
      // falls through
      case "cs-redraft-go": if (a === "cs-redraft-go") closeModal();
      // falls through
      case "cs-draft": if (!(await flushText(Number(v)))) break; if (S.recState) await stopMic(); S.ctab = "note"; S.drafting = Number(v); S.noteEdit = false; renderConsult();
        try { await Promise.all([api(`/visits/${v}/note/draft`, { body: {} }), new Promise(r => setTimeout(r, 1400))]); } finally { S.drafting = null; S.dictDone = null; } refreshConsult(); break;
      case "mic": if (S.recState) await stopMic(); else { S.ctab = "dictate"; startMic(Number(v)); } break;
      case "spk": S.speaker = v; document.querySelectorAll('[data-a="spk"]').forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v)); break;
      case "rx-add": { const n = D.cur.note; n.content = readNote(); n.content.rx.push({ medicine: "", dose: "", duration: "", instructions: "" }); rerenderNote(); break; }
      case "rx-del": { const n = D.cur.note; n.content = readNote(); n.content.rx.splice(Number(v), 1); rerenderNote(); break; }
      case "note-save": await api(`/notes/${v}`, { method: "PUT", body: readNote() }); toast("Draft saved"); refreshConsult(); break;
      case "note-sign": await api(`/notes/${v}`, { method: "PUT", body: readNote() }); await api(`/notes/${v}/sign`, { body: {} }); toast("Signed. Visit complete."); refreshConsult(); break;
      case "note-view": await openNoteView(Number(v)); break;
      case "note-print": window.open(`/api/notes/${v}/print?auto=1&token=${encodeURIComponent(S.token)}`, "_blank"); break;
      case "print": window.open(`/api/notes/${v}/print?token=${encodeURIComponent(S.token)}`, "_blank"); break;
      case "open-doc": { const res = await fetch(`/api/documents/${v}/file`, { headers: { Authorization: "Bearer " + S.token } }); window.open(URL.createObjectURL(await res.blob()), "_blank"); break; }
      case "cite": if (v.startsWith("T")) { const src = sourceOf(D.cur, v); if (!src) break;
        if (S.ctab !== "dictate") { S.ctab = "dictate"; renderConsult(); }
        const ta = $("#free-text"), at = ta.value.indexOf(src.text); ta.focus(); if (at >= 0) ta.setSelectionRange(at, at + src.text.length); break; }
      if (M?.kind === "chart") closeModal();
      S.cside = "citations"; S.rightCollapsed = false; S.focusSrc = v; renderConsult();
      { const el = document.getElementById("src-" + v); el?.scrollIntoView({ behavior: "smooth", block: "nearest" }); setTimeout(() => { if (S.focusSrc === v) { S.focusSrc = null; document.getElementById("src-" + v)?.classList.remove("hl"); } }, 1800); }
    }
  });
});
function payShow() {
  const w = M?.pay === "waive", disc = Number($("#pay-disc")?.value) || 0, fee = Number($("#pay-disc")?.dataset.fee) || 0;
  const dw = $("#pay-disc-wrap"), rw = $("#pay-why-wrap"), due = $("#pay-due");
  if (dw) dw.hidden = w;
  if (rw) rw.hidden = !(w || disc > 0);
  if (due) due.textContent = rupees(w ? 0 : Math.max(0, fee - disc));
}
function rerenderNote() { const c = $("#cx-center"); if (c) c.innerHTML = center(); restoreFree(); }
document.addEventListener("input", e => {
  const a = e.target.dataset?.a;
  if (a === "bk-q") searchPatients(e.target.value);
  if (a === "pay-disc") payShow();
  if (a === "free-text") { if (S.dict) S.dict = typedOver(S.dict, e.target); edit(Number(e.target.dataset.v), e.target.value); }
  if (a === "up-file") { const f = e.target.files[0]; $("#up-name").textContent = f ? f.name : "No file"; $(".file-drop").classList.toggle("has", !!f); }
  if (a === "mg-q") { M.q = e.target.value; clearTimeout(searchT); searchT = setTimeout(() => run(async () => { if (M?.kind !== "merge") return; M.results = M.q.trim() ? await api(`/patients?q=${encodeURIComponent(M.q)}`) : []; renderMerge(); }), 180); }
  if (a === "vf-q") { S.vf.q = e.target.value; const r = $("#ops-rows"); if (r && S.data?.visits) r.innerHTML = opsRows(S.data.visits); }
  if (a === "cs-q") { S.cq = e.target.value; clearTimeout(S.cqt); S.cqt = setTimeout(async () => { await run(S.reloadConsult); const q = $("#cs-q"); if (q) { q.focus(); q.setSelectionRange(q.value.length, q.value.length); } }, 220); }
  if (a === "pt-q") { S.pq = e.target.value; clearTimeout(S.pqt); S.pqt = setTimeout(async () => { await viewPatients(Number(location.hash.split("/")[2]) || null); const q = $("#pt-q"); q.focus(); q.setSelectionRange(q.value.length, q.value.length); }, 200); }
});
document.addEventListener("change", e => {
  const a = e.target.dataset?.a;
  if (a === "ops-date") { S.date = e.target.value || TODAY; route(); }
  if (a === "mb-admin") { const box = $("#mb-s-administration"); if (box) { box.disabled = !e.target.checked; if (!e.target.checked) box.checked = false; } }
  if (a === "mr-range") { const from = $("#mr-from").value || TODAY, to = $("#mr-to").value || from; Object.assign(S.mon, from <= to ? { from, to } : { from: to, to: from }); route(); }
  if (/^(lvm|rgm)-[my]$/.test(a)) { const [y, m] = S.adm.month.split("-").map(Number); const nm = a.endsWith("-m") ? Number(e.target.value) : m, ny = a.endsWith("-y") ? Number(e.target.value) : y; S.adm.month = `${ny}-${String(nm).padStart(2, "0")}`; route(); }
  if (a === "vf-doc") { S.vf.doc = e.target.value; const r = $("#ops-rows"); if (r && S.data?.visits) r.innerHTML = opsRows(S.data.visits); }
  if (a === "bk-date") { M.date = e.target.value || TODAY; run(loadAvail); }
  if (a === "bk-doc") { M.doctorId = Number(e.target.value); run(loadAvail); }
  if (a === "sc-doc") { M.doctorId = Number(e.target.value); M.sel = null; run(loadMonth); }
  if (a === "sc-month-picker" || a === "sc-year-picker") {
    const month = a === "sc-month-picker" ? Number(e.target.value) : Number(M.month.slice(5, 7));
    const year = a === "sc-year-picker" ? Number(e.target.value) : Number(M.month.slice(0, 4));
    M.month = `${year}-${String(month).padStart(2, "0")}`; M.sel = null; run(loadMonth);
  }
  if (a === "cs-doc") { S.ctab = "brief"; go(`#/consult?doctor=${e.target.value}`); }
  if (a === "lim") { const p = e.target.dataset.p, vals = readLimit(p); $(`#${p}-lim`).innerHTML = limitBlock(p, vals); }
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && M) { closeModal(); if (M === null) refresh(); }
});
