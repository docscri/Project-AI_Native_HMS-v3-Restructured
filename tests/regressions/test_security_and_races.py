"""Refund and consultation-start races, reset links after a password change, receipt access, no tokens in print URLs."""
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import clinic, join, member, started_visit


def test_parallel_refunds_never_refund_more_than_was_paid():
    with TestClient(app) as c:
        h, doc = clinic(c, "race-refund@x.in")
        v = started_visit(c, h, doc)
        with ThreadPoolExecutor(6) as pool:
            codes = list(pool.map(lambda _: c.post(f"/api/visits/{v['id']}/refund", headers=h, json={"amount": 300, "reason": "Twice"}).status_code, range(6)))
        assert codes.count(200) == 1
        assert c.get(f"/api/visits/{v['id']}", headers=h).json()["refund_amount"] == 300


def test_parallel_starts_leave_one_patient_with_the_doctor():
    with TestClient(app) as c:
        h, doc = clinic(c, "race-start@x.in")
        visits = []
        for i in range(6):
            p = c.post("/api/patients", headers=h, json={"name": f"P{i}", "consent": True}).json()
            visits.append(c.post("/api/visits/walk-in", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "payment_method": "cash"}).json())
        with ThreadPoolExecutor(6) as pool:
            codes = list(pool.map(lambda v: c.post(f"/api/visits/{v['id']}/start", headers=h).status_code, visits))
        assert codes.count(200) == 1
        q = c.get("/api/consultation/today", headers=h).json()
        assert sum(1 for v in q["visits"] if v["status"] == "with_doctor") == 1


def test_password_change_cancels_old_reset_links():
    with TestClient(app) as c:
        h, _ = clinic(c, "reset-old@x.in")
        code = c.post("/api/members/" + str(c.get("/api/me", headers=h).json()["member"]["id"]) + "/reset-link", headers=h).json()["code"]
        assert c.post("/api/auth/change-password", headers=h, json={"current": "clinic123", "new": "newpass456"}).status_code == 200
        assert c.post("/api/auth/reset", json={"code": code, "password": "hijack789"}).status_code == 410
        assert c.post("/api/auth/login", json={"email": "reset-old@x.in", "password": "newpass456"}).status_code == 200


def test_receipt_needs_operations_access():
    with TestClient(app) as c:
        h, doc = clinic(c, "receipt-acl@x.in")
        v = started_visit(c, h, doc)
        nobody = join(c, member(c, h, "No Screens", "noscreen@x.in", "staff", [])["invite_code"])
        assert c.get(f"/api/visits/{v['id']}/receipt", headers=nobody).status_code == 403
        assert c.get(f"/api/visits/{v['id']}/receipt", headers=h).status_code == 200


def test_print_pages_take_the_login_from_the_header_not_the_url():
    with TestClient(app) as c:
        h, doc = clinic(c, "print-url@x.in")
        v = started_visit(c, h, doc)
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Fever.", "rev": 0})
        n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
        tok = h["Authorization"].split()[1]
        assert c.get(f"/api/visits/{v['id']}/receipt", params={"token": tok}).status_code == 401
        assert c.get(f"/api/notes/{n['id']}/print", params={"token": tok}).status_code == 401
        assert c.get(f"/api/notes/{n['id']}/print", headers=h).status_code == 200
