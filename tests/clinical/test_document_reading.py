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
    gemini.generate([{"text": "hi"}])
    assert KEY not in sent["url"] and "params" not in sent
    assert sent["headers"]["x-goog-api-key"] == KEY


def test_failed_read_keeps_the_key_out_shows_in_brief_and_can_be_retried(monkeypatch):
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
        assert "LLM_MODEL" in got["extracted"]["summary"]
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
        monkeypatch.setattr(llm, "generate", lambda parts: {     # AI writes a number the report doesn't have
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
