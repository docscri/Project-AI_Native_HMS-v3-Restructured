"""The eleven-issue review: PDF.js, login races, arrival vs cancel, addenda as AI evidence, admin access without the
Administration screen, removing staff with attendance, clearing a date of birth."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.clinical.notes import service as notes
from app.modules.operations.account import service as account
from app.shared.db import connect
from tests.helpers import clinic, join, member

ROOT = Path(__file__).resolve().parents[2]
TODAY = date.today().isoformat()


def test_pdf_reader_is_a_version_that_never_runs_pdf_javascript():
    readme = (ROOT / "frontend/vendor/pdfjs/README").read_text()
    major, minor, patch = map(int, re.search(r"PDF\.js (\d+)\.(\d+)\.(\d+)", readme).groups())
    assert (major, minor, patch) >= (4, 2, 67)                                     # CVE-2024-4367 fixed
    assert (ROOT / "frontend/vendor/pdfjs/pdf.min.mjs").exists() and not (ROOT / "frontend/vendor/pdfjs/pdf.min.js").exists()
    assert "isEvalSupported: false" in (ROOT / "frontend/js/shared/viewer.js").read_text()
    with TestClient(app) as c:
        assert "javascript" in c.get("/static/vendor/pdfjs/pdf.min.mjs").headers["content-type"]


def test_parallel_wrong_passwords_still_lock_the_account(monkeypatch):
    real = account.check_password
    def slow(*a):   # widen the gap between reading the count and writing it
        import time; time.sleep(0.05); return real(*a)
    monkeypatch.setattr(account, "check_password", slow)
    with TestClient(app) as c:
        clinic(c, "lock-race@x.in")
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(lambda _: c.post("/api/auth/login", json={"email": "lock-race@x.in", "password": "wrong-one"}), range(8)))
        assert c.post("/api/auth/login", json={"email": "lock-race@x.in", "password": "clinic123"}).status_code == 423


def test_arrival_and_cancellation_cannot_both_win():
    with TestClient(app) as c:
        h, doc = clinic(c, "arrive-cancel@x.in")
        for i in range(4):
            p = c.post("/api/patients", headers=h, json={"name": f"AC {i}", "consent": True}).json()
            v = c.post("/api/visits", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": TODAY}).json()
            calls = [lambda: c.post(f"/api/visits/{v['id']}/arrive", headers=h, json={"payment_method": "cash"}).status_code,
                     lambda: c.post(f"/api/visits/{v['id']}/cancel", headers=h, json={"reason": "x"}).status_code]
            with ThreadPoolExecutor(2) as pool:
                codes = list(pool.map(lambda f: f(), calls))
            got = c.get(f"/api/visits/{v['id']}", headers=h).json()
            assert codes.count(200) == 1
            assert not (got["status"] == "cancelled" and got.get("paid_at"))


def test_signed_corrections_reach_the_ai_with_their_note():
    past = [{"id": 7, "date": "2026-10-01", "content": {"soap": {"A": "Type 2 diabetes.", "P": "Metformin."}},
             "addenda": [{"signed_at": "2026-10-02T10:00:00", "text": "Correction: not diabetic; HbA1c was another patient's."}]}]
    item = notes.evidence("", [], past)[0]
    assert item["id"] == "N7" and "not diabetic" in item["text"] and "Type 2 diabetes" in item["text"]
    for task in ("brief_summary", "visit_lines"):
        assert "N<id>.X" in (ROOT / f"backend/app/shared/ai/tasks/{task}/prompt.md").read_text()


def test_admin_flag_without_the_administration_screen_gives_no_admin_powers():
    with TestClient(app) as c:
        h, _ = clinic(c, "half-admin@x.in")
        m = c.post("/api/members", headers=h, json={"name": "Half", "email": "half@x.in", "kind": "staff", "screens": ["operations"], "is_admin": True}).json()
        hh = join(c, m["invite_code"])
        other = join(c, member(c, h, "Other", "other-lv@x.in", "staff", ["operations"])["invite_code"])
        leave = c.post("/api/leave", headers=other, json={"start_date": TODAY, "end_date": TODAY, "reason": "x"}).json()
        assert c.post(f"/api/leave/{leave['id']}/approve", headers=hh).status_code == 403
        reg = c.get("/api/team/register", headers=hh, params={"month": TODAY[:7]}).json()
        assert {x["id"] for x in reg["people"]} == {m["id"]}                                       # only themselves


def test_staff_with_attendance_are_deactivated_not_a_server_error():
    with TestClient(app) as c:
        h, _ = clinic(c, "rm-att@x.in")
        m = member(c, h, "Clocked In", "clocked@x.in", "staff", ["operations"])
        mh = join(c, m["invite_code"])
        assert c.post("/api/attendance/check-in", headers=mh).status_code == 200
        assert c.delete(f"/api/members/{m['id']}", headers=h).status_code == 200
        assert c.get("/api/me", headers=mh).status_code == 401                                  # signed out
        assert [x["status"] for x in c.get("/api/members", headers=h).json() if x["id"] == m["id"]] == ["inactive"]


def test_clearing_a_date_of_birth_clears_it():
    with TestClient(app) as c:
        h, _ = clinic(c, "dob-clear@x.in")
        p = c.post("/api/patients", headers=h, json={"name": "Dob Pat", "consent": True, "dob": "1990-05-01"}).json()
        assert c.patch(f"/api/patients/{p['id']}", headers=h, json={"name": "Dob Pat", "dob": None}).json()["dob"] is None
        assert c.patch(f"/api/patients/{p['id']}", headers=h, json={"name": "Dob Pat", "dob": "1990-05-01"}).json()["dob"] == "1990-05-01"
        assert c.patch(f"/api/patients/{p['id']}", headers=h, json={"name": "Dob Pat", "dob": ""}).json()["dob"] is None
