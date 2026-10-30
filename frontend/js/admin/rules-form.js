/* clinic rules form */
const sessionsOf = v => v.sessions?.length ? v.sessions.map(x => ({ start: x.start, end: x.end })) : [{ start: v.start || "09:00", end: v.end || "13:00" }];
function limitBlock(p, v) {
  const ss = sessionsOf(v), f = ss[0];
  const l = limitsOf(f.start, f.end, v.limit_by, v.limit_value);
  const patientValue = v.limit_by === "patients" ? v.limit_value : Math.max(1, l.max);
  const minuteValue = v.limit_by === "minutes" ? v.limit_value : Math.max(1, l.per);
  const byP = v.limit_by === "patients";
  return `${ss.map((x, i) => `<div class="sess-row"><div class="grid2"><label class="field">${ss.length > 1 ? `Session ${i + 1} start` : "Start"}<input type="time" id="${p}-s${i}" value="${x.start}" data-a="lim" data-p="${p}"></label><label class="field">End<input type="time" id="${p}-e${i}" value="${x.end}" data-a="lim" data-p="${p}"></label></div>
      ${ss.length > 1 ? `<button class="icon-x" data-a="ses-del" data-p="${p}" data-v="${i}" aria-label="Remove session">×</button>` : ""}</div>`).join("")}
    ${ss.length < 3 ? `<div><button class="btn small" data-a="ses-add" data-p="${p}">+ Add session</button></div>` : ""}
    <div class="rule-row"><div class="pick-seg">
      <label><input type="radio" name="${p}-by" value="patients" ${byP ? "checked" : ""} data-a="lim" data-p="${p}"><span>By patients</span></label>
      <label><input type="radio" name="${p}-by" value="minutes" ${byP ? "" : "checked"} data-a="lim" data-p="${p}"><span>By time</span></label></div>
      <label class="field" ${byP ? "" : "hidden"}>Patients per session<input type="number" min="1" id="${p}-patients-val" value="${patientValue}" data-a="lim" data-p="${p}"></label>
      <label class="field" ${byP ? "hidden" : ""}>Minutes per patient<input type="number" min="1" id="${p}-minutes-val" value="${minuteValue}" data-a="lim" data-p="${p}"></label>
      <span class="rule-hint">${byP ? `≈ ${l.per} min each` : `${l.max} patients max`}</span></div>`;
}
function readLimit(p) {
  const by = $(`input[name="${p}-by"]:checked`).value;
  const el = $(`#${p}-${by}-val`);
  const sessions = [];
  for (let i = 0; $(`#${p}-s${i}`); i++) sessions.push({ start: $(`#${p}-s${i}`).value, end: $(`#${p}-e${i}`).value });
  return { sessions, limit_by: by, limit_value: Number(el?.value) || 1 };
}
function rulesForm(p, c) {
  const dn = ["S", "M", "T", "W", "T", "F", "S"], full = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  return `<label class="field">Consultation fee (₹)<input type="number" min="0" id="${p}-fee" value="${c.fee}"></label>
    <div class="rule-group"><span class="rule-label">Working days</span><div class="day-dots">${dn.map((d, i) => `<label title="${full[i]}"><input type="checkbox" id="${p}-d${i}" ${c.days.includes(i) ? "checked" : ""} aria-label="${full[i]}"><span>${d}</span></label>`).join("")}</div></div>
    <div class="rule-group"><span class="rule-label">Sessions</span><div id="${p}-lim" class="rule-stack">${limitBlock(p, c)}</div></div>
    <div class="rule-group"><span class="rule-label">Token</span><div class="pick-seg">
      <label><input type="radio" name="${p}-tok" value="booking" ${c.token_timing === "booking" ? "checked" : ""}><span>At booking</span></label>
      <label><input type="radio" name="${p}-tok" value="arrival" ${c.token_timing === "arrival" ? "checked" : ""}><span>On arrival</span></label></div></div>`;
}
const readRules = p => ({ fee: Number($(`#${p}-fee`).value) || 0, days: [0, 1, 2, 3, 4, 5, 6].filter(i => $(`#${p}-d${i}`).checked),
  ...readLimit(p), token_timing: $(`input[name="${p}-tok"]:checked`).value });
