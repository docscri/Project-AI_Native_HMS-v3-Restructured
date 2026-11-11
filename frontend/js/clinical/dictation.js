// Deepgram when the server has a key, else the browser's own speech recognition.
function startMic(visitId) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (S.dictBy !== "deepgram" && !SR) { refreshConsult(); return toast("Use Chrome to dictate", true); }
  const box = $("#free-text");   // what Consult held before this recording, so Cancel can put it back
  Object.assign(S, { recState: "on", recVisit: visitId, recAcc: 0, recStart: Date.now(), dict: null, dictDone: null, recCancelled: false,
                     recBase: box && Number(box.dataset.v) === visitId ? box.value : freeText(S.data.cur) });
  listen(visitId);
  clearInterval(S.recT); S.recT = setInterval(() => { const t = $("#dock-timer"); if (t) t.textContent = fmtClock(recElapsed()); }, 500);
  renderConsult();
}
const recElapsed = () => (S.recAcc || 0) + (S.recState === "on" && S.recStart ? Date.now() - S.recStart : 0);
function listen(visitId) {
  if (S.dictBy === "deepgram") return streamMic(visitId);
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const r = new SR(); r.lang = "en-IN"; r.continuous = true; r.interimResults = true;
  S.dict = null;
  r.onresult = e => {
    const el = $("#free-text"); if (!el || el.readOnly || S.recCancelled) return;
    if (!S.dict || (!S.dict.len && document.activeElement === el)) S.dict = { start: document.activeElement === el ? el.selectionEnd : el.value.length, len: 0 };
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const said = e.results[i][0].transcript.trim();
      if (e.results[i].isFinal) { if (said) putSpeech(el, said + " ", true); } else interim += (interim ? " " : "") + said;
    }
    if (interim) putSpeech(el, interim, false);
    edit(visitId, el.value);
    paintCaption();
  };
  // Chrome stops after silence; restart until the doctor stops.
  r.onend = () => { if (S.rec === r && S.recState === "on") { try { r.start(); } catch { listen(visitId); } } };
  r.onerror = e => !["no-speech", "aborted"].includes(e.error) && toast("Mic: " + e.error, true);
  S.rec = r; r.start();
}
// Pause, resume, stop and cancel repaint only the bottom bar, at once; the slow parts (the speech service's
// last words, saving) carry on after. Redrawing the whole consultation made the buttons feel stuck on phones.
function paintDock() {
  const f = $(".cx-float"), v = S.data?.cur;
  if (f && v && v.id === S.recVisit && (S.recState || S.ctab !== "note")) { f.innerHTML = dock(v); sizeCaption(); } else renderConsult();
}
function pauseMic() {
  if (S.recState !== "on") return;
  S.recAcc = recElapsed(); S.recState = "paused";
  if (S.rec?.pause) { S.rec.pause().catch(() => {}); return paintDock(); }   // Deepgram: soft pause, link kept
  const r = S.rec; S.rec = null;
  // Deepgram's last words arrive after the pause, so keep the insertion point until they have.
  if (r?.finish) S.finishing = r.finish().catch(() => {}).finally(() => { if (S.recState !== "on") S.dict = null; });
  else { try { r?.stop(); } catch {} S.dict = null; }
  paintDock();
}
function resumeMic() {
  if (S.recState !== "paused") return;
  S.recState = "on"; S.recStart = Date.now(); paintDock();
  if (S.dict && !S.dict.len) S.dict = null;   // new words go where the cursor is now
  if (!S.rec?.resume?.()) { const old = S.rec; S.rec = null; try { old?.stop(); } catch {} listen(S.recVisit); }   // link lost while paused: reconnect
}
async function stopMic() {
  const id = S.recVisit, r = S.rec;
  S.rec = null; S.recState = null; clearInterval(S.recT);
  paintDock();
  try {
    if (r?.finish) await r.finish();
    else if (r) await new Promise(ok => { r.onend = ok; r.stop(); setTimeout(ok, 1500); });   // browser speech: its last words come after stop
  } catch {}
  S.dict = null; S.dictDone = id;
  try { await saveText(id); } catch {}   // a slow or failed save must not cost the note (the draft saves the text again)
  autoNote(id); refreshConsult();
}
// Cancel: stop listening, ignore words still on their way, and put Consult back as it was before the recording.
async function cancelMic() {
  const id = S.recVisit, r = S.rec, base = S.recBase ?? "";
  Object.assign(S, { rec: null, recState: null, recCancelled: true, dict: null, dictDone: null }); clearInterval(S.recT);
  const put = () => { const el = $("#free-text"); if (el && Number(el.dataset.v) === id) el.value = base; edit(id, base); };
  put(); paintDock(); toast("Dictation cancelled.");
  try { r?.abort ? r.abort() : r?.finish ? await r.finish() : r?.stop(); } catch {}
  await S.finishing;
  put(); await saveText(id); refreshConsult();   // again, in case late words slipped in while it closed
}
function speech(visitId, text, final) {
  const el = $("#free-text"); if (!el || el.readOnly || Number(el.dataset.v) !== visitId || S.recCancelled) return;
  if (!S.dict || (!S.dict.len && !S.dict.kept && document.activeElement === el)) S.dict = { start: document.activeElement === el ? el.selectionEnd : el.value.length, len: 0 };
  const kept = S.dict.kept;   // words already left in the box when the doctor typed
  if (kept && text.toLowerCase().startsWith(kept.toLowerCase())) text = text.slice(kept.length).trimStart();
  if (final) S.dict.kept = "";
  if (!text) return;
  putSpeech(el, final ? text + " " : text, final);
  edit(visitId, el.value);
  paintCaption();
}
// Note tab: the words being heard, live, in light italics above the recording bar (Consult shows them in its box).
// Settled words in the caption's colour, words still being worked out fainter; only the last line or two.
function captionHtml() {
  const el = $("#free-text"); if (!el || S.ctab !== "note") return "";
  const all = el.value, base = (S.recBase || "").length, d = S.dict;
  const live = d?.len ? all.slice(d.start, d.start + d.len) : "", said = (d?.len ? all.slice(0, d.start) + all.slice(d.start + d.len) : all).slice(base).trim();
  const tail = s => s.length > 140 ? s.slice(-140).replace(/^\S*\s/, "") : s;
  const shown = tail((said + (live ? " " + live.trim() : "")).trim());
  if (!shown) return `<div class="rec-caption" id="rec-caption"><span class="wait">Listening</span></div>`;
  const cut = shown.length - (live ? live.trim().length : 0);
  return `<div class="rec-caption" id="rec-caption">${esc(shown.slice(0, cut))}${live ? `<span class="live">${esc(shown.slice(cut))}</span>` : ""}</div>`;
}
function sizeCaption() {   // the caption as wide as the recording bar under it
  const bar = $(".cx-float .dock.rec"), f = $(".cx-float"); if (bar && f) f.style.setProperty("--rec-w", bar.getBoundingClientRect().width / 2 + "px");
}
function paintCaption() {
  sizeCaption();
  const c = $("#rec-caption"); if (!c) return;
  const tmp = document.createElement("div"); tmp.innerHTML = captionHtml();
  c.replaceWith(tmp.firstElementChild || document.createTextNode(""));
}
// Mic → 16 kHz PCM frames (ported from Project-Dictate). The AudioContext is made at the click, before any await.
const audioContext = () => { const C = window.AudioContext || window.webkitAudioContext; const c = new C({ latencyHint: "interactive" }); c.resume().catch(() => {}); return c; };
async function micCapture(onFrame, onLost) {
  const ctx = S.audioCtx || audioContext(); S.audioCtx = null;
  let stream, node, src, mute, on = false, stopped = false, flushed;
  const stop = async ({ flush = false } = {}) => {
    if (stopped) return; stopped = true;
    if (flush && node && on) await new Promise(r => { flushed = r; node.port.postMessage("flush"); setTimeout(r, 150); });
    on = false;
    if (node) { node.port.onmessage = null; node.disconnect(); node.port.close(); }
    src?.disconnect(); mute?.disconnect();
    stream?.getTracks().forEach(t => { t.onended = null; t.stop(); });
    if (ctx.state !== "closed") await ctx.close().catch(() => {});
  };
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    await ctx.resume();
    await ctx.audioWorklet.addModule("/static/pcm-worklet.js");
    node = new AudioWorkletNode(ctx, "dictate-pcm", { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1] });
    node.port.onmessage = ({ data }) => { if (data.type === "audio" && on) onFrame(data.frame); if (data.type === "flushed") flushed?.(); };
    src = ctx.createMediaStreamSource(stream); mute = ctx.createGain(); mute.gain.value = 0;
    src.connect(node); node.connect(mute); mute.connect(ctx.destination);
    stream.getTracks().forEach(t => { t.onended = () => { if (!stopped) { stop(); onLost(); } }; });
  } catch (e) { await stop(); throw e; }
  const hold = async () => { if (on && node && !stopped) await new Promise(r => { flushed = r; node.port.postMessage("flush"); setTimeout(r, 150); }); on = false; };
  return { start: () => { on = true; }, hold, go: () => { if (!stopped) on = true; }, stop };
}
// Deepgram via the server. Text lands in the writing box and is saved by the normal autosave.
async function streamMic(visitId) {
  const rec = { stop() {}, async finish() {} };
  S.rec = rec; S.dict = null;
  const fail = msg => { if (S.rec !== rec) return; toast(msg, true); stopMic(); };
  let ws, mic;
  try { mic = await micCapture(f => ws?.readyState === 1 && ws.send(f), () => fail("Microphone disconnected")); }
  catch { S.audioCtx = null; return fail("Allow the microphone to dictate"); }
  await S.finishing;   // a paused stream must close before the next one opens
  if (S.rec !== rec) return mic.stop();
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/visits/${visitId}/dictate`, ["dictate", S.token]);
  let closed; const done = new Promise(r => { closed = r; });
  const timer = setTimeout(() => fail("Dictation couldn't connect"), 10000);
  ws.onmessage = ({ data }) => {
    const m = JSON.parse(data);
    if (m.type === "ready") { clearTimeout(timer); if (S.recState === "on") mic.start(); }   // paused while connecting: wait for resume
    else if (m.type === "transcript") speech(visitId, m.text, m.final);
    else if (m.type === "error") { clearTimeout(timer); fail(m.message); }
  };
  ws.onclose = () => { clearTimeout(timer); closed(); fail("Dictation stopped. Try again."); };
  rec.stop = () => { clearTimeout(timer); mic.stop(); ws.close(); };
  // Pause keeps the mic and the link open and just stops sending sound, so resume is instant.
  rec.pause = async () => { await mic.hold(); if (ws.readyState === 1) ws.send("pause"); };
  rec.resume = () => { if (ws.readyState !== 1) return false; ws.send("resume"); mic.go(); return true; };
  rec.finish = async () => {   // send the last audio, then wait for Deepgram's last words
    clearTimeout(timer); await mic.stop({ flush: true });
    if (ws.readyState === 1) { ws.send("stop"); await Promise.race([done, new Promise(r => setTimeout(r, 8000))]); }
    ws.close();   // no-op once closed; ends a stream the server never closed
  };
}
// The doctor typed while words were still being recognised: keep those words, and let the rest of
// the phrase continue right after them (shifted if the typing happened before them).
function typedOver(d, el) {
  if (!d.len && !d.kept) return { start: el.selectionEnd, len: 0 };
  const was = S.ft?.id === Number(el.dataset.v) ? S.ft.text : null, shift = was == null ? 0 : el.value.length - was.length;
  const after = el.selectionEnd - shift >= d.start + d.len;
  return { start: d.start + d.len + (after ? 0 : shift), len: 0, kept: d.len ? d.said || "" : d.kept };
}
function putSpeech(el, text, final) {
  const d = S.dict, before = el.value.slice(0, d.start);
  const pad = before && !/\s$/.test(before) ? " " : "";
  if (!before.trim() || /[.!?]\s*$/.test(before)) text = text.charAt(0).toUpperCase() + text.slice(1);
  el.setRangeText(pad + text, d.start, d.start + d.len, "end");
  if (final) { d.start += pad.length + text.length; d.len = 0; } else { d.len = pad.length + text.length; d.said = (d.kept ? d.kept + " " : "") + text; }
  if (document.activeElement === el) el.setSelectionRange(d.start + d.len, d.start + d.len);
}
// Same split as the server's ai.sentences(): T1, T2… are sentences; 100.8 stays whole.
const sentences = text => {
  const out = []; let at = 0;
  for (const line of text.split("\n")) {
    for (const m of line.matchAll(/[^.!?\s].*?(?:[.!?]+(?=\s|$)|$)/g)) { const t = m[0].trim(); if (t) out.push({ text: t, from: at + m.index, to: at + m.index + m[0].trimEnd().length }); }
    at += line.length + 1;
  }
  return out;
};

// After Stop: write the note on its own (Account setting, on by default), after a 3 s countdown that can be cancelled.
// Never over the doctor's own edits (asks instead), never on a signed note, never for a few stray words.
function autoNote(id) {
  const v = S.data?.cur;
  if (!v || v.id !== id || S.me.kind !== "doctor" || S.me.auto_note === false || v.status !== "with_doctor" || v.note?.status === "signed") return;
  const box = $("#free-text"), text = box && Number(box.dataset.v) === id ? box.value : freeText(v);
  if (text.trim() === (S.recBase || "").trim() || text.trim().split(/\s+/).length < 5) return;
  clearInterval(S.autoNote?.timer);
  if (v.note?.edited) { S.autoNote = { id, ask: true }; return; }
  S.autoNote = { id, left: 3 };
  S.autoNote.timer = setInterval(() => {
    const a = S.autoNote; if (!a || a.id !== id) return;
    if (S.data?.cur?.id !== id || S.recState) { cancelAutoNote(); return; }   // moved to another patient, or dictating again
    if (--a.left > 0) { const el = $("#auto-left"); if (el) el.textContent = a.left; return; }
    clearInterval(a.timer); S.autoNote = null;
    run(async () => { if (await flushText(id)) await draftNow(id); });   // the latest words saved first, as Generate note does
  }, 1000);
}
function cancelAutoNote() { clearInterval(S.autoNote?.timer); S.autoNote = null; }
async function draftNow(id) {
  cancelAutoNote();
  S.ctab = "note"; S.drafting = id; S.noteEdit = false; renderConsult();
  try { await Promise.all([api(`/visits/${id}/note/draft`, { body: {} }), new Promise(r => setTimeout(r, 1400))]); }
  finally { S.drafting = null; S.dictDone = null; }
  refreshConsult();
}
document.addEventListener("click", e => {
  const t = e.target.closest('[data-a="auto-cancel"], [data-a="auto-redraft"]'); if (!t) return;
  e.preventDefault(); e.stopPropagation();
  if (t.dataset.a === "auto-cancel") { cancelAutoNote(); renderConsult(); }
  else run(async () => { if (await flushText(Number(t.dataset.v))) await draftNow(Number(t.dataset.v)); });
}, true);
