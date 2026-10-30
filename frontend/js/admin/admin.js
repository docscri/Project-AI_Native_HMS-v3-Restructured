/* administration */
async function viewAdmin(tab, sub) {
  const g = S.gen;
  const editable = S.me.is_admin;
  const tabs = [["clinic", "Clinic details"], ["rules", "Clinic rules"], ["team", "Team"], ...(editable ? [["money", "Collections"]] : [])];
  let body = "";
  if (tab === "clinic") body = `<section class="panel" style="max-width:640px"><label class="field">Clinic name<input id="ad-name" value="${esc(S.clinic.name)}"></label>
    <label class="field">Phone<input id="ad-phone" value="${esc(S.clinic.phone)}"></label><label class="field">Address<input id="ad-addr" value="${esc(S.clinic.address)}"></label>
        ${editable ? `<div class="save-row"><button class="btn primary" data-a="ad-details">Save</button></div>` : ""}</section>`;
  if (tab === "rules") body = `<section class="panel" style="max-width:700px">${rulesForm("ad", S.clinic)}
    ${editable ? `<div class="save-row"><button class="btn primary" data-a="ad-rules">Save</button></div>` : ""}</section>`;
  if (tab === "team" && editable && sub && sub !== "members") body = await teamView(sub);
  else if (tab === "money" && editable) body = await moneyView();
  else if (tab === "team") {
    const ms = await api("/members");
    body = `<section class="panel scroll"><table class="t members"><thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Role</th><th>Department</th><th>Status</th></tr></thead><tbody>
      ${ms.map(m => `<tr class="${editable ? "click" : ""}" ${editable ? `data-a="member-edit" data-v="${m.id}"` : ""}>
        <td><span class="mname"><span class="avatar sm">${esc(initials(m.name))}</span><b>${esc(m.name)}</b></span></td>
        <td>${esc(m.phone || "—")}</td><td class="muted">${esc(m.email)}</td>
        <td>${m.is_owner ? "Owner" : m.kind === "doctor" ? "Doctor" : "Staff"}</td>
        <td>${esc((m.kind === "doctor" ? m.speciality : m.designation) || "—")}</td>
        <td><span class="pill ${m.status === "active" ? "s-paid" : m.status === "invited" ? "s-waiting" : "s-no_show"}">${{ active: "Active", invited: "Invited", inactive: "Inactive" }[m.status]}</span></td></tr>`).join("")}
    </tbody></table></section>${editable ? `<div class="actions"><button class="btn primary" data-a="member-add" data-v="doctor">Add doctor</button><button class="btn" data-a="member-add" data-v="staff">Add staff</button></div>` : ""}`;
    if (editable) body = subTabs("team", "members") + body;
    S.members = ms;
  }
  if (stale(g)) return;
  view(`<div class="head"><div><h1>Administration</h1></div></div>
    <div class="actions admin-tabs">${tabs.map(([k, l]) => `<button class="btn" data-a="ad-tab" data-v="${k}" aria-pressed="${k === tab}">${l}</button>`).join("")}</div>${body}`);
}
