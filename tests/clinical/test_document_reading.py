"""Reading uploaded documents: the key stays out of URLs and errors, failed reads show in the brief and can be retried,
and every new report keeps a line in the summary."""
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.modules.clinical.documents import service as documents
from app.shared.ai import llm
from app.shared.ai.llm.providers import gemini
from tests.helpers import clinic, started_visit

KEY = "SECRET-KEY-123"


def upload(c, h, v, name="lab.txt", data=b"Sunrise Diagnostics\nHbA1c 8.1 %", mime="text/plain"):
    return c.post(f"/api/visits/{v['id']}/documents", headers=h, files={"file": (name, data, mime)}).json()


def summary(c, h, v):
    b = c.post(f"/api/visits/{v['id']}/brief", headers=h).json()
    return [s for p in b["summary"] for s in p["sentences"]], b["sources"]


def test_gemini_key_goes_in_a_header_not_the_url(monkeypatch):
    sent = {}
    def fake_post(url, **kw):
        sent.update(url=url, **kw)
        return httpx.Response(200, request=httpx.Request("POST", url),
                              json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    monkeypatch.setattr(httpx, "post", fake_post)
    gemini.generate([{"text": "hi"}], "gemini-2.5-flash-lite")
    assert KEY not in sent["url"] and "params" not in sent and "/models/gemini-2.5-flash-lite:" in sent["url"]
    assert sent["headers"]["x-goog-api-key"] == KEY


def test_failed_read_keeps_the_key_out_shows_in_brief_and_can_be_retried(monkeypatch, caplog):
    def refuse(data, mime, filename):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/x:generateContent?key={KEY}"
        req = httpx.Request("POST", url)
        raise httpx.HTTPStatusError(f"Client error '404 Not Found' for url '{url}'", request=req, response=httpx.Response(404, request=req))
    with TestClient(app) as c:
        h, doc = clinic(c, "docread@x.in")
        v = started_visit(c, h, doc)
        monkeypatch.setattr(documents, "extract_document", refuse)
        d = upload(c, h, v, "InvoiceNo1733.pdf", b"%PDF-1.4", "application/pdf")
        monkeypatch.undo()
        got = c.get(f"/api/visits/{v['id']}", headers=h).json()["documents"][0]
        assert got["ai_status"] == "failed" and KEY not in str(got["extracted"])
        assert got["extracted"]["summary"] == documents.UNREAD                 # staff get plain words
        assert "LLM_MODEL" in caplog.text and KEY not in caplog.text            # the technical reason goes to the server log
        lines, sources = summary(c, h, v)
        assert {"text": "InvoiceNo1733.pdf: couldn't be read.", "cites": [f"D{d['id']}"], "flags": []} in lines
        assert sources[f"D{d['id']}"]["failed"] is True
        assert c.post(f"/api/documents/{d['id']}/retry", headers=h).json()["ai_status"] == "processing"
        again = c.get(f"/api/visits/{v['id']}", headers=h).json()["documents"][0]
        assert again["ai_status"] == "ready"                                   # read again in the background (no AI: plain text)
        assert c.post(f"/api/documents/{d['id']}/retry", headers=h).status_code == 409   # only failed ones


def test_new_report_keeps_a_line_when_the_ai_line_is_dropped(monkeypatch):
    with TestClient(app) as c:
        h, doc = clinic(c, "docline@x.in")
        v = started_visit(c, h, doc)
        d = upload(c, h, v)
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.setattr(llm, "generate", lambda parts, model=None: {     # AI writes a number the report doesn't have
            "new": [{"text": "HbA1c is 9.4 %.", "cites": [f"D{d['id']}"]}], "history": [], "events": []})
        lines, _ = summary(c, h, v)
        assert [s["text"] for s in lines] == ["Sunrise Diagnostics HbA1c 8.1 %."]


def test_brief_with_a_failed_document_is_reused_not_rebuilt(monkeypatch):
    with TestClient(app) as c:
        h, doc = clinic(c, "docbasis@x.in")
        v = started_visit(c, h, doc)
        monkeypatch.setattr(documents, "extract_document", lambda *a: (_ for _ in ()).throw(RuntimeError("no")))
        upload(c, h, v, "scan.pdf", b"%PDF-1.4", "application/pdf")
        monkeypatch.undo()
        c.post(f"/api/visits/{v['id']}/brief", headers=h)
        assert c.get(f"/api/visits/{v['id']}", headers=h).json()["brief"] is not None   # the screen would otherwise rebuild forever


def test_front_desk_lists_and_removes_documents_until_the_note_is_signed():
    from pathlib import Path
    from app.shared.db import connect
    from tests.helpers import join, member
    with TestClient(app) as c:
        h, doc = clinic(c, "docremove@x.in")
        desk = join(c, member(c, h, "Desk", "desk-rm@x.in", "staff", ["operations"])["invite_code"])
        p = c.post("/api/patients", headers=desk, json={"name": "Pat", "consent": True}).json()
        v = c.post("/api/visits/walk-in", headers=desk, json={"patient_id": p["id"], "doctor_id": doc, "payment_method": "cash"}).json()
        wrong, right = upload(c, desk, v, "wrong.txt"), upload(c, desk, v, "right.txt")
        assert [d["filename"] for d in c.get(f"/api/visits/{v['id']}/documents", headers=desk).json()] == ["wrong.txt", "right.txt"]
        db = connect()
        path = db.execute("select path from documents where id = ?", (wrong["id"],)).fetchone()[0]
        db.close()
        assert c.delete(f"/api/documents/{wrong['id']}", headers=desk).json() == {"ok": True}
        assert not Path(path).exists()
        assert [d["filename"] for d in c.get(f"/api/visits/{v['id']}/documents", headers=desk).json()] == ["right.txt"]
        assert c.delete(f"/api/documents/{wrong['id']}", headers=desk).status_code == 404
        c.post(f"/api/visits/{v['id']}/start", headers=h)
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Fever.", "rev": 0})
        n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
        c.post(f"/api/notes/{n['id']}/sign", headers=h)
        assert c.delete(f"/api/documents/{right['id']}", headers=desk).status_code == 409   # a signed note may cite it
        other, _ = clinic(c, "docremove-other@x.in")
        assert c.delete(f"/api/documents/{right['id']}", headers=other).status_code == 404    # other clinics can't touch it


def test_report_filed_under_the_patient_before_a_visit_reaches_the_brief():
    """A doctor files a report on the patient page before any visit; the next visit's brief and sources read it."""
    with TestClient(app) as c:
        h, doc = clinic(c, "docpatient@x.in")
        p = c.post("/api/patients", headers=h, json={"name": "Early", "consent": True}).json()
        d = c.post(f"/api/patients/{p['id']}/documents", headers=h,
                   files={"file": ("lab.txt", b"Sunrise Diagnostics\nHbA1c 8.1 %", "text/plain")}).json()
        filed = c.get(f"/api/patients/{p['id']}", headers=h).json()["documents"]
        assert [(x["id"], x["visit_id"], x["ai_status"]) for x in filed] == [(d["id"], None, "ready")]
        v = c.post("/api/visits/walk-in", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "payment_method": "cash"}).json()
        c.post(f"/api/visits/{v['id']}/start", headers=h)
        assert f"D{d['id']}" in summary(c, h, v)[1]
        other, _ = clinic(c, "docpatient-other@x.in")
        assert c.post(f"/api/patients/{p['id']}/documents", headers=other, files={"file": ("x.txt", b"x", "text/plain")}).status_code == 404
        assert c.delete(f"/api/documents/{d['id']}", headers=h).json() == {"ok": True}   # no signed note relies on it yet
