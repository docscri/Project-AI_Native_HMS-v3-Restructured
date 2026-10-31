// Consult: what the doctor types and dictates, in one box. Typing works without the microphone;
// clicking into the box of a waiting patient starts the visit, just as the microphone does.
function paneDictate(v) {
  const n = v.note, can = ["waiting", "with_doctor"].includes(v.status) && n?.status !== "signed";
  return `<textarea class="live-text live-edit" id="free-text" data-a="free-text" data-v="${v.id}" spellcheck="true" aria-label="Consult"
    placeholder="${can ? "Type here, or press the microphone to dictate." : ""}" ${can ? "" : "readonly"}>${esc(freeText(v))}</textarea>`;
}
const freeText = v => S.ft?.id === v.id ? S.ft.text : S.drafts?.[v.id]?.saved !== S.drafts?.[v.id]?.text ? S.drafts[v.id].text : (v.text || "");
const SOAP = [["S", "Subjective"], ["O", "Objective"], ["A", "Assessment"], ["P", "Plan"]];
function paneNote(v) {
  const n = v.note, signed = n?.status === "signed";
  if (S.drafting === v.id) return `<div class="note-gen"><i></i><i></i><i></i></div>`;
  if (!n) return `<div class="note-empty"><p class="muted cx-lead">${v.status === "with_doctor" ? "No note yet. Type or dictate in Consult, then generate it." : "No note for this visit."}</p>${genBtn(v)}</div>`;
  if (S.noteEdit && !signed) return noteEditor(n, false);
  return soapRead(v, n);
}
function soapRead(v, n, still) {
  let num = 0;
  const sec = (k, label, body) => `<div class="soap-sec"><b class="soap-tile">${k}</b><div><span class="soap-label">${label}</span><div class="soap-body">${body}</div></div></div>`;
  const out = SOAP.map(([k, label]) => {
    const text = (n.content.soap[k] || "").trim();
    const sents = sentences(text).map(x => x.text);
    const srcs = (n.citations?.[k] || []).map(id => ({ id, text: sourceOf(v, id)?.text || "" }));
    return sec(k, label, sents.map(t => `<span class="nb">${++num}</span>${marked(t, srcs, still)}`).join(" ") || `<span class="muted">—</span>`);
  }).join("");
  const rx = n.content.rx.filter(r => r.medicine);
  return `<div class="soap-read">${out}${rx.length ? sec("Rx", "Prescription", rx.map(r => `<div class="rx-line"><span class="nb">${++num}</span><b>${esc(r.medicine)}</b>${[r.dose, r.duration, r.instructions].filter(Boolean).map(x => ` · ${esc(x)}`).join("")}</div>`).join("")) : ""}</div>`;
}
const STOP = new Set("a an the and or of to in on at for with by is are was were be been has have had this that it its as from no not patient patients reports reported says said complains denies looks like seems tab tablet order rule out once twice daily mg ml for since".split(" "));
function marked(sentence, srcs, still) {
  const words = sentence.split(/(\s+)/), norm = w => w.toLowerCase().replace(/[^a-z0-9/]/g, "");
  const toks = words.map((w, i) => ({ w, i, n: /\s/.test(w) ? null : norm(w) })).filter(t => t.n !== null);
  // up to 3-word phrases shared with a source; keep the 2 best
  const cands = [];
  for (const src of srcs) {
    const hay = " " + src.text.toLowerCase().split(/\s+/).map(norm).filter(Boolean).join(" ") + " ";
    for (let i = 0; i < toks.length; i++) for (let j = i; j < Math.min(i + 3, toks.length); j++) {
      if (!hay.includes(" " + toks.slice(i, j + 1).map(t => t.n).join(" ") + " ")) break;
      if (STOP.has(toks[i].n) || STOP.has(toks[j].n) || i === 0 && j === toks.length - 1) continue;
      const score = toks.slice(i, j + 1).reduce((n, t) => n + (STOP.has(t.n) ? 0 : t.n.length), 0) + (j - i) * 3;
      if (score >= 8) cands.push({ a: i, b: j, id: src.id, score });
    }
  }
  const marks = [];
  for (const c of cands.sort((x, y) => y.score - x.score)) {
    if (marks.length === 2) break;
    if (!marks.some(m => !(c.b < m.a - 1 || c.a > m.b + 1))) marks.push(c);
  }
  if (!marks.length) return esc(sentence);
  const byTok = new Map(); marks.forEach(m => { byTok.set(toks[m.a].i, { start: true, id: m.id }); byTok.set(toks[m.b].i, { ...(byTok.get(toks[m.b].i) || {}), end: true, id: m.id }); });
  return words.map((w, i) => { const m = byTok.get(i); return (m?.start ? (still ? `<span class="cited">` : `<button class="cited" data-a="cite" data-v="${m.id}">`) : "") + esc(w) + (m?.end ? (still ? "</span>" : "</button>") : ""); }).join("");
}
function noteDock(v) {
  const n = v.note, signed = n?.status === "signed";
  if (S.drafting === v.id) return `<div class="dock"><span class="dock-text">Writing your note…</span></div>`;
  if (!n) return "";   // the empty note carries its own Generate note button
  if (signed) return `<div class="dock"><span class="dock-msg ok">Signed · ${stampOf(n.signed_at)}${n.signed_by_name ? " · " + esc(n.signed_by_name) : ""}</span><span class="grow"></span><button class="dock-go" data-a="note-print" data-v="${n.id}">Print</button></div>`;
  if (S.noteEdit) return `<div class="dock"><span class="dock-msg">Editing.</span><span class="grow"></span><button class="dock-go" data-a="note-done">Save</button></div>`;
  return `<div class="dock"><span class="dock-msg">${S.aiOn ? "Drafted by AI." : "Draft."}</span><span class="grow"></span>
    <button class="dock-ghost" data-a="note-edit">Edit</button>${v.status === "with_doctor" ? `<button class="dock-ghost" data-a="cs-redraft" data-v="${v.id}">Redraft</button>` : ""}<button class="dock-go" data-a="note-sign-ro" data-v="${n.id}">Sign note</button></div>`;
}
function rightCol() {
  const D = S.data, p = D.profile;
  const tabs = `<div class="cx-right-top"><button class="cx-side-btn close" data-a="cs-collapse" aria-label="Hide side panel" title="Hide side panel"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h12M12 6l6 6-6 6"/></svg></button><div class="cx-seg"><button data-a="cs-side" data-v="profile" aria-pressed="${S.cside !== "citations"}">Profile</button><button data-a="cs-side" data-v="citations" aria-pressed="${S.cside === "citations"}">Sources</button></div></div>`;
  if (S.cside === "citations") return `${tabs}${citations(D.cur)}`;
  if (!p) return `${tabs}<div class="cx-empty">—</div>`;
  return `${tabs}<div class="cx-rows">
    ${[["Name", p.name], ["Age", ageOf(p.dob)], ["Date of birth", p.dob ? longDate(p.dob) : "—"], ["Sex", { M: "Male", F: "Female", O: "Other" }[p.sex] || "—"], ["Phone", p.phone || "—"], ["Address", p.address || "—"], ["UHID", p.uhid]].map(([k, val]) => `<div class="cx-row"><span>${k}</span><b>${esc(val)}</b></div>`).join("")}
    <div class="cx-row"><span>Visits</span><b>${p.visits.filter(x => x.status === "done").length}</b></div></div>`;
}
function sourceOf(v, id) {
  if (id.startsWith("T")) { const t = v.note?.sources?.[id] ?? sentences(freeText(v))[Number(id.slice(1)) - 1]?.text; return t && { kind: "Consult", text: t }; }
  const bs = v.brief?.sources?.[id];
  if (bs) return bs.kind === "note" ? { kind: `Note · ${longDate(bs.date)} · ${bs.section}`, text: bs.body } : { kind: `Report · ${longDate(bs.date)}`, text: bs.label + (bs.summary ? " — " + bs.summary : "") };
  if (id.startsWith("D")) { const d = v.documents.find(x => "D" + x.id === id); return d && { kind: "Document", text: d.filename + (d.extracted?.findings?.length ? " — " + d.extracted.findings.slice(0, 3).map(f => `${f.name} ${f.value} ${f.unit || ""}`.trim()).join(", ") : "") }; }
  if (id.startsWith("N")) return { kind: "Earlier note", text: "Signed note from a previous visit" };
  return null;
}
// Sources panel: what the note cites (S/O/A/P) and what the brief's summary and charts cite (notes and reports).
function citations(v) {
  if (!v) return `<div class="cx-empty">—</div>`;
  const groups = [], cites = v.note?.citations || {}, b = v.brief;
  ["S", "O", "A", "P"].forEach(k => { if (cites[k]?.length) groups.push([k, cites[k]]); });
  const briefIds = [...new Set([...(b?.summary || []).flatMap(p => p.sentences.flatMap(x => x.cites)), ...(b?.charts || []).flatMap(c => c.series.flatMap(x => x.points.map(p => p.cite)))])];
  const docIcon = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Reports"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>`;
  const noteIcon = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-label="Notes"><path d="M5 6h14M5 12h14M5 18h9"/></svg>`;
  const reps = briefIds.filter(id => b.sources[id]?.kind === "document"), notes = briefIds.filter(id => !reps.includes(id));
  if (reps.length) groups.push([docIcon, reps]);
  if (notes.length) groups.push([noteIcon, notes]);
  if (!groups.length) return `<div class="cx-empty">No sources</div>`;
  const card = id => {
    const bs = b?.sources?.[id], on = S.focusSrc === id ? " hl" : "", n = briefNums(b).get(id), no = n ? `${n} · ` : "";
    // Brief sources name the report or note; open them for the detail. Consult sentences (below) show their text.
    if (bs?.kind === "document") return `<div class="src-doc${on}" id="src-${id}"><small>${no}REPORT · ${longDate(bs.date).toUpperCase()}</small><b>${esc(bs.label)}</b>${bs.failed ? `<span>Couldn't be read.</span>` : ""}
      <span class="actions" style="gap:6px"><button class="btn small" data-a="open-doc" data-v="${bs.doc_id}">Open file</button>${bs.failed ? `<button class="btn small dark" data-a="doc-retry" data-v="${bs.doc_id}">Try again</button>` : ""}</span></div>`;
    if (bs?.kind === "note") return `<button class="${on.trim()}" id="src-${id}" data-a="note-view" data-v="${bs.visit_id}"><small>${no}NOTE · ${longDate(bs.date).toUpperCase()} · ${bs.section.toUpperCase()}</small>Signed note<em>${esc(bs.doctor)}</em></button>`;
    const src = sourceOf(v, id); return src ? `<button data-a="cite" data-v="${id}"><small>${src.kind.toUpperCase()} · ${id}</small>${esc(src.text)}</button>` : "";
  };
  return `<div class="cite-list">${groups.map(([k, ids]) => `<div class="cite-item"><b>${k}</b><div class="cite-src">${ids.map(card).join("")}</div></div>`).join("")}</div>`;
}
const fmtClock = ms => { const t = Math.floor(ms / 1000); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`; };
const citeLabel = id => { const bs = S.data?.cur?.brief?.sources?.[id]; return !bs ? id : bs.kind === "note" ? new Date(bs.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: new Date(bs.date).getFullYear() === new Date().getFullYear() ? undefined : "numeric" }) : "Report"; };
// Citations as small dark superscripts: transcript sentence number, R for a report, N for an earlier note.
function citeBtns(ids) { return (ids || []).map(c => `<button class="cite-sup" data-a="cite" data-v="${c}" title="${esc(citeLabel(c))}">${c[0] === "T" ? c.slice(1) : c[0] === "D" ? "R" : "N"}</button>`).join(""); }
function noteEditor(n, ro) {
  const soap = n.content.soap, rx = n.content.rx;
  return `<div class="choices">${["S", "O", "A", "P"].map(k => `<div class="soap"><b>${k}</b><div>${ro ? `<div class="ro">${esc(soap[k] || "—")}</div>` : `<textarea id="soap-${k}">${esc(soap[k] || "")}</textarea>`}<div>${citeBtns(n.citations?.[k])}</div></div></div>`).join("")}</div>
    <div class="scroll"><table class="t" id="rx"><thead><tr><th>Medicine</th><th>Dose</th><th>Duration</th><th>Instructions</th>${ro ? "" : "<th></th>"}</tr></thead><tbody>
      ${rx.map((r, i) => `<tr>${["medicine", "dose", "duration", "instructions"].map(f => `<td>${ro ? esc(r[f]) : `<input data-f="${f}" value="${esc(r[f])}" aria-label="${f}">`}</td>`).join("")}${ro ? "" : `<td><button class="icon-x" data-a="rx-del" data-v="${i}" aria-label="Remove">×</button></td>`}</tr>`).join("") || `<tr><td colspan="5" class="muted">—</td></tr>`}
    </tbody></table></div>${ro ? "" : `<div><button class="btn small" data-a="rx-add">+ Add medicine</button></div>`}`;
}
function readNote() {
  const soap = Object.fromEntries(["S", "O", "A", "P"].map(k => [k, $("#soap-" + k)?.value || ""]));
  const rx = [...document.querySelectorAll("#rx tbody tr")].filter(tr => tr.querySelector("input")).map(tr => Object.fromEntries([...tr.querySelectorAll("input")].map(i => [i.dataset.f, i.value])));
  return { soap, rx };
}
