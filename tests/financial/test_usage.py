"""The usage meter: Gemini tokens as billed and dictation seconds, per clinic and job, priced; read by the operator only."""
import time

import httpx
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.shared import usage
from app.shared.ai.llm.providers import gemini
from app.shared.ai.speech.providers import deepgram as transcribe
from app.shared.db import connect, rows as db_rows
from tests.clinical.test_consultation_dictation import FakeStream, token
from tests.helpers import clinic, started_visit


def rows(clinic_id):
    db = connect()
    try:
        return db_rows(db.execute("select kind, job, model, tokens_in, tokens_out, seconds, cost_micro_usd as cost from usage_events "
                                  "where clinic_id = ? order by id", (clinic_id,)))
    finally:
        db.close()


def test_prices():
    assert usage.ai_cost("gemini-3.8-flash", 5000, 1200) == 6000              # $0.0015 + $0.0045 = $0.006
    assert usage.ai_cost("gemini-3.8-flash-lite", 6000, 1000) == 4300
    assert usage.speech_cost("nova-3-medical", 180) == 19500                  # 3 min x $0.0065
    assert config.SPEECH_MODEL == "nova-3-medical"


def test_ai_tokens_and_dictation_seconds_are_metered_per_clinic(monkeypatch):
    def fake_post(url, **kw):   # Gemini's reply, with what it billed (thinking tokens count as output)
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
            "usageMetadata": {"promptTokenCount": 5000, "candidatesTokenCount": 1000, "thoughtsTokenCount": 200}})
    with TestClient(app) as c:
        h, doc = clinic(c, "meter@x.in")
        cid = c.get("/api/me", headers=h).json()["clinic"]["id"]
        v = started_visit(c, h, doc)
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Fever for two days.", "rev": 0})
        monkeypatch.setenv("GEMINI_API_KEY", "k")
        monkeypatch.setattr(httpx, "post", fake_post)
        c.post(f"/api/visits/{v['id']}/note/draft", headers=h)                 # the AI reply is bad ({}), so the plain draft is used: still billed
        monkeypatch.delenv("GEMINI_API_KEY")
        ai = [r for r in rows(cid) if r["kind"] == "ai"]
        assert ai and ai[0] == {"kind": "ai", "job": "draft_note", "model": "gemini-3.8-flash", "tokens_in": 5000, "tokens_out": 1200,
                                "seconds": 0, "cost": 6000}
        monkeypatch.setenv("DEEPGRAM_API_KEY", "test")
        monkeypatch.setattr(transcribe, "DeepgramStream", FakeStream)
        with c.websocket_connect(f"/api/visits/{v['id']}/dictate", subprotocols=["dictate", token(h)]) as ws:
            ws.receive_json()
            ws.send_bytes(b"x" * 64000)                                          # 2 s of 16 kHz 16-bit audio
            ws.receive_json()
            ws.send_text("stop")
            ws.receive_json()
        for _ in range(50):   # written as the stream closes, just after the socket does
            speech = [r for r in rows(cid) if r["kind"] == "speech"]
            if speech:
                break
            time.sleep(0.05)
        assert speech == [{"kind": "speech", "job": "dictation", "model": "nova-3-medical", "tokens_in": 0, "tokens_out": 0,
                           "seconds": 2, "cost": usage.speech_cost("nova-3-medical", 2)}]


def test_operator_report_needs_the_ops_token(monkeypatch):
    with TestClient(app) as c:
        h, _ = clinic(c, "meter-ops@x.in")
        cid = c.get("/api/me", headers=h).json()["clinic"]["id"]
        assert c.get("/api/ops/usage", headers=h).status_code == 404            # clinics never see it
        monkeypatch.setenv("OPS_TOKEN", "s3cret")
        ops = {"X-Ops-Token": "s3cret"}
        assert c.get("/api/ops/usage", headers={"X-Ops-Token": "wrong"}).status_code == 404
        assert c.get("/api/ops/usage?month=nov", headers=ops).status_code == 422
        db = connect()
        for job, t_in, t_out, cost in (("draft_note", 5000, 1200, 6000), ("brief_summary", 6000, 1000, 4300)):
            db.execute("insert into usage_events (clinic_id, kind, job, model, tokens_in, tokens_out, seconds, cost_micro_usd, at) "
                       "values (?, 'ai', ?, 'gemini-3.8-flash', ?, ?, 0, ?, ?)", (cid, job, t_in, t_out, cost, "2031-03-15T10:00:00"))
        db.commit()
        db.close()
        r = c.get("/api/ops/usage?month=2031-03", headers=ops).json()
        mine = next(x for x in r["clinics"] if x["clinic_id"] == cid)
        assert (mine["ai_calls"], mine["tokens_in"], mine["tokens_out"], mine["usd"]) == (2, 11000, 2200, 0.01)
        assert mine["jobs"]["draft_note"]["usd"] == 0.006 and mine["inr"] == round(0.0103 * 85)
