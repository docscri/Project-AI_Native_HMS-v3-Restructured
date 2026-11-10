// Consult: what the doctor types and dictates, in one box. Typing works without the microphone;
// clicking into the box of a waiting patient starts the visit, just as the microphone does.
function paneDictate(v) {
  const n = v.note, can = ["waiting", "with_doctor"].includes(v.status) && n?.status !== "signed";
  return `<textarea class="live-text live-edit" id="free-text" data-a="free-text" data-v="${v.id}" spellcheck="true" aria-label="Consult"
    placeholder="${can ? "Type here, or press the microphone to dictate." : ""}" ${can ? "" : "readonly"}>${esc(freeText(v))}</textarea>`;
}
const freeText = v => S.ft?.id === v.id ? S.ft.text : S.drafts?.[v.id]?.saved !== S.drafts?.[v.id]?.text ? S.drafts[v.id].text : (v.text || "");
const SOAP = [["S", "Subjective"], ["O", "Objective"], ["A", "Assessment"], ["P", "Plan"]];
const VITALS = ["BP", "Pulse", "RR", "Temp", "SpO2", "Weight", "Height"];
// Notes are written in the doctor's department format (numbered sections); notes from before that stay S/O/A/P.
const isDept = n => Array.isArray(n?.content?.sections);
const noteParts = n => isDept(n) ? n.content.sections.map(x => [x.key, x.title, x.text || ""]) : SOAP.map(([k, label]) => [k, label, n.content.soap[k] || ""]);
const planKey = n => isDept(n) ? n.content.sections.filter(x => /management/i.test(x.title)).map(x => x.key) : ["P"];
const vitalsLine = n => VITALS.filter(k => (n.content.vitals?.[k] || "").trim()).map(k => `<span class="vit-chip"><small>${k}</small>${esc(n.content.vitals[k])}</span>`).join("");
function paneNote(v) {
  const n = v.note, signed = n?.status === "signed";
  if (S.drafting === v.id) return `<div class="note-gen"><i></i><i></i><i></i></div>`;
  if (!n) return `<div class="note-empty"><p class="muted cx-lead">${v.status === "with_doctor" ? "No note yet. Type or dictate in Consult, then press Generate note." : "No note for this visit."}</p></div>`;
  if (S.noteEdit && !signed) return noteEditor(n, false);
  return soapRead(v, n);
}
function soapRead(v, n, still, skipEmpty = false) {
  let num = 0;
  const sec = (k, label, body) => `<div class="soap-sec"><b class="soap-tile">${k}</b><div><span class="soap-label">${label}</span><div class="soap-body">${body}</div></div></div>`;
  const vit = isDept(n) ? vitalsLine(n) : "";
  let shown = 0;
  const out = (vit ? `<div class="vit-strip" aria-label="Vitals">${vit}</div>` : "") + noteParts(n).map(([k, label, body]) => {
    const text = body.trim();
    if (skipEmpty && !text) return "";   // reading a signed note: leave out sections with nothing in them
    if (skipEmpty && /^\d+$/.test(k)) k = String(++shown);   // and number the rest 1, 2, 3
    const sents = sentences(text).map(x => x.text);
    const srcs = (n.citations?.[k] || []).map(id => ({ id, text: sourceOf(v, id)?.text || "" }));
    return sec(k, esc(label), sents.map(t => `${citeNum(++num, bestSource(t, srcs), still)}${marked(t, srcs, still)}`).join(" ") || `<span class="muted">—</span>`);
  }).join("");
  const rx = n.content.rx.filter(r => r.medicine);
  const planSrcs = planKey(n).flatMap(k => n.citations?.[k] || []).map(id => ({ id, text: sourceOf(v, id)?.text || "" }));   // a medicine links to the plan that prescribes it
  return `<div class="soap-read">${out}${rx.length ? sec("Rx", "Prescription", rx.map(r => `<div class="rx-line">${citeNum(++num, bestSource(r.medicine, planSrcs), still)}<b>${esc(r.medicine)}</b>${[r.dose, r.duration, r.instructions].filter(Boolean).map(x => ` · ${esc(x)}`).join("")}</div>`).join("")) : ""}${addendaRead(n)}</div>`;
}
// Addenda: dated, signed additions under a signed note, shown as written.
const addendaRead = n => (n.addenda || []).length ? `<div class="soap-sec addenda"><b class="soap-tile">+</b><div><span class="soap-label">Addendum</span>
  ${n.addenda.map(x => `<div class="add-line"><small>${stampOf(x.signed_at)} · ${esc(x.signed_by_name)}</small><p>${esc(x.text)}</p></div>`).join("")}</div></div>` : "";
// Every sentence number links to where it came from: the section source that shares most words with it.
function bestSource(sentence, srcs) {
  const words = s => new Set(s.toLowerCase().match(/[a-z0-9]{3,}/g) || []), mine = words(sentence);
  let best = srcs[0], score = -1;
  for (const s of srcs) { const n = [...words(s.text)].filter(w => mine.has(w)).length; if (n > score) { best = s; score = n; } }
  return best?.id;
}
const citeNum = (n, id, still) => id && !still ? `<button class="nb" data-a="cite" data-v="${id}" title="${esc(id.startsWith("T") ? "From Consult" : citeLabel(id))}">${n}</button>` : `<span class="nb">${n}</span>`;
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
  if (signed) return `<div class="dock"><span class="dock-msg ok">Signed · ${stampOf(n.signed_at)}${n.signed_by_name ? " · " + esc(n.signed_by_name) : ""}</span><span class="grow"></span>${S.me.kind === "doctor" ? `<button class="dock-ghost" data-a="add-addendum" data-v="${n.id}">Add addendum</button>` : ""}<button class="dock-go" data-a="note-print" data-v="${n.id}">Print</button></div>`;
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
  (v.note ? noteParts(v.note).map(([k]) => k) : []).forEach(k => { if (cites[k]?.length) groups.push([k, cites[k]]); });
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
    const src = sourceOf(v, id); return src ? `<button class="${on.trim()}" id="src-${id}" data-a="${id.startsWith("T") ? "cite-go" : "cite"}" data-v="${id}" title="${id.startsWith("T") ? "Show in Consult" : ""}"><small>${src.kind.toUpperCase()} · ${id}</small>${esc(src.text)}</button>` : "";
  };
  return `<div class="cite-list">${groups.map(([k, ids]) => `<div class="cite-item"><b>${k}</b><div class="cite-src">${ids.map(card).join("")}</div></div>`).join("")}</div>`;
}
const fmtClock = ms => { const t = Math.floor(ms / 1000); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`; };
const citeLabel = id => { const bs = S.data?.cur?.brief?.sources?.[id]; return !bs ? id : bs.kind === "note" ? new Date(bs.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: new Date(bs.date).getFullYear() === new Date().getFullYear() ? undefined : "numeric" }) : "Report"; };
// Citations as small dark superscripts: transcript sentence number, R for a report, N for an earlier note.
function citeBtns(ids) { return (ids || []).map(c => `<button class="cite-sup" data-a="cite" data-v="${c}" title="${esc(citeLabel(c))}">${c[0] === "T" ? c.slice(1) : c[0] === "D" ? "R" : "N"}</button>`).join(""); }
function noteEditor(n, ro) {
  const rx = n.content.rx, dept = isDept(n);
  const vit = dept ? `<div class="vit-edit" aria-label="Vitals">${VITALS.map(k => `<label><small>${k}</small>${ro ? `<b>${esc(n.content.vitals?.[k] || "—")}</b>` : `<input data-vital="${k}" value="${esc(n.content.vitals?.[k] || "")}" aria-label="${k}">`}</label>`).join("")}</div>` : "";
  return `<div class="choices" id="note-ed">${vit}${noteParts(n).map(([k, label, text]) => `<div class="soap${dept ? " dept" : ""}"><b>${k}</b><div>${dept ? `<span class="soap-label">${esc(label)}</span>` : ""}${ro ? `<div class="ro">${esc(text || "—")}</div>` : `<textarea data-sec="${k}" data-title="${esc(label)}" aria-label="${esc(label)}">${esc(text)}</textarea>`}<div>${citeBtns(n.citations?.[k])}</div></div></div>`).join("")}</div>
    <div class="scroll"><table class="t" id="rx"><thead><tr><th>Medicine</th><th>Dose</th><th>Duration</th><th>Instructions</th>${ro ? "" : "<th></th>"}</tr></thead><tbody>
      ${rx.map((r, i) => `<tr>${["medicine", "dose", "duration", "instructions"].map(f => `<td>${ro ? esc(r[f]) : `<input data-f="${f}" value="${esc(r[f])}" aria-label="${f}">`}</td>`).join("")}${ro ? "" : `<td><button class="icon-x" data-a="rx-del" data-v="${i}" aria-label="Remove">×</button></td>`}</tr>`).join("") || `<tr><td colspan="5" class="muted">—</td></tr>`}
    </tbody></table></div>${ro ? "" : `<div><button class="btn small" data-a="rx-add">+ Add medicine</button></div>`}`;
}
// The editor's note, in the same shape as the saved content (the server takes it as is).
function readNote() {
  const rx = [...document.querySelectorAll("#rx tbody tr")].filter(tr => tr.querySelector("input")).map(tr => Object.fromEntries([...tr.querySelectorAll("input")].map(i => [i.dataset.f, i.value])));
  const cur = S.data?.cur?.note?.content || {}, boxes = [...document.querySelectorAll("#note-ed [data-sec]")];
  if (!isDept({ content: cur })) return { soap: Object.fromEntries(SOAP.map(([k]) => [k, boxes.find(b => b.dataset.sec === k)?.value || ""])), rx };
  const sections = boxes.map(b => ({ key: b.dataset.sec, title: b.dataset.title, text: b.value }));
  const vitals = Object.fromEntries([...document.querySelectorAll("#note-ed [data-vital]")].map(i => [i.dataset.vital, i.value]));
  return { ...cur, sections, vitals, rx };
}
