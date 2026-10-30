function scheduleSave(visitId) { clearTimeout(S.ftT); S.ftT = setTimeout(() => saveText(visitId), 700); }
// Each snapshot keeps its first rev so stale retries are refused by the server.
function edit(visitId, text) {
  const { base, tries, ...was } = S.ft?.id === visitId ? S.ft : (S.drafts?.[visitId] || {});
  S.ft = { ...was, id: visitId, text };
  (S.drafts = S.drafts || {})[visitId] = S.ft;
  scheduleSave(visitId);
}
// Serialise saves per visit.
function saveText(visitId, ft = S.ft) {
  clearTimeout(S.ftT);
  S.saving = S.saving || {};
  const run = (S.saving[visitId] || Promise.resolve()).then(() => saveOnce(visitId, ft));
  S.saving[visitId] = run.catch(() => {});
  return run;
}
async function saveOnce(visitId, ft, again) {
  if (!ft || ft.id !== visitId || S.drafts?.[visitId] !== ft) return true;   // superseded
  if (ft.saved === ft.text) return true;
  const text = ft.text;
  S.textRev = S.textRev || {}; S.sent = S.sent || {};
  if (ft.base == null) ft.base = S.textRev[visitId] ?? 0;
  (S.sent[visitId] = S.sent[visitId] || new Set()).add(text);
  try {
    const r = await api(`/visits/${visitId}/text`, { method: "PUT", body: { text, rev: ft.base } });
    S.textRev[visitId] = r.rev;
  } catch (e) {
    if (e.status === 409 && !again && S.drafts[visitId] === ft) {
      // A lost reply may hide our own save: if the server holds text we sent, continue from it.
      const now = await api(`/visits/${visitId}`).catch(() => null);
      if (now?.text === text) { S.textRev[visitId] = now.text_rev; return done(visitId, ft, text); }
      if (now && S.sent[visitId].has(now.text)) { ft.base = now.text_rev; return saveOnce(visitId, ft, true); }
    }
    if (e.status === 409) {
      if (S.drafts[visitId] !== ft) return true;
      // Someone else saved newer text: keep theirs.
      delete S.drafts[visitId]; if (S.ft?.id === visitId) S.ft = null;
      toast(e.message, true); refreshConsult(); return false;
    }
    toast(`Not saved · ${e.message}`, true);
    ft.tries = (ft.tries || 0) + 1;
    if (ft.tries < 6) setTimeout(() => saveText(visitId, ft), 5000);
    return false;
  }
  return done(visitId, ft, text);
}
function done(visitId, ft, text) {
  ft.saved = text; ft.tries = 0;
  if (S.drafts[visitId] === ft && S.data?.cur?.id === visitId) S.data.cur.text = text;
  return true;
}
const unsaved = () => Object.values(S.drafts || {}).some(d => d.saved !== d.text);
// false if unsaved text couldn't be saved.
const flushText = async (visitId = S.ft?.id ?? S.data?.cur?.id) => {
  const d = S.drafts?.[visitId];
  return !d || d.saved === d.text || (await saveText(visitId, d)) !== false;
};
window.addEventListener("beforeunload", e => { if (unsaved()) { e.preventDefault(); e.returnValue = ""; } });
