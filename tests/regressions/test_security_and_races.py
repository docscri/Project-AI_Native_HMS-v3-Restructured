"""Refund and consultation-start races, reset links after a password change, receipt access, no tokens in print URLs."""
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.shared.db import connect
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


def in_the_gap(module, name, when, action):
    """Wrap module.name so that, the moment `when(args)` holds, `action` runs on another thread inside the gap.
    With the fix the other thread has to wait for our lock, so we give it a second and carry on."""
    real = getattr(module, name)
    def wrapped(*args):
        out = real(*args)
        if when(args):
            t = threading.Thread(target=action)
            t.start()
            t.join(timeout=1)
        return out
    setattr(module, name, wrapped)
    return lambda: setattr(module, name, real)


def test_refund_during_undo_arrival_never_refunds_twice():
    from app.modules.financial.payments import service as payments
    from app.modules.financial.payments.schema import Refund
    from app.modules.operations.appointments import service as appointments
    with TestClient(app) as c:
        h, doc = clinic(c, "race-undo@x.in")
        p = c.post("/api/patients", headers=h, json={"name": "U", "consent": True}).json()
        v = c.post("/api/visits", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": date.today().isoformat()}).json()
        assert c.post(f"/api/visits/{v['id']}/arrive", headers=h, json={"payment_method": "cash"}).status_code == 200
        me = c.get("/api/me", headers=h).json()["member"]
        refund = []
        def refund_now():
            db = connect()
            try:
                payments.refund(db, me, v["id"], Refund(amount=300, reason="Back"))
                db.commit()
                refund.append(200)
            except Exception:
                db.rollback()
                refund.append(409)
            finally:
                db.close()
        undo_back = in_the_gap(appointments, "balance", lambda a: True, refund_now)   # undo has read the balance, not yet refunded it
        try:
            undo = c.post(f"/api/visits/{v['id']}/undo-arrival", headers=h, json={"reason": "Wrong patient"}).status_code
        finally:
            undo_back()
        db = connect()
        held = db.execute("select coalesce(sum(case when kind = 'payment' then amount else -amount end), 0) from payments where visit_id = ?",
                          (v["id"],)).fetchone()[0]
        db.close()
        assert held == 0 and [undo, *refund].count(200) == 1


def test_password_change_during_a_reset_is_not_overwritten():
    from app.modules.operations.account import service as account
    with TestClient(app) as c:
        h, mid = clinic(c, "reset-race@x.in")
        cid = c.get("/api/me", headers=h).json()["member"]["clinic_id"]
        code = c.post(f"/api/members/{mid}/reset-link", headers=h).json()["code"]
        changed = []
        def change():
            db = connect()
            try:
                account.change_password(db, {"id": mid, "clinic_id": cid}, "clinic123", "newpass456", "")
                db.commit()
                changed.append(True)
            except Exception:
                db.rollback()
            finally:
                db.close()
        reset_back = in_the_gap(account, "validate_password", lambda a: a[0] == "hijack789", change)   # reset checked its link
        try:
            reset = c.post("/api/auth/reset", json={"code": code, "password": "hijack789"}).status_code
        finally:
            reset_back()
        assert not (changed and reset == 200)   # both "succeeding" means one silently undid the other
        login = lambda pw: c.post("/api/auth/login", json={"email": "reset-race@x.in", "password": pw}).status_code == 200
        assert login("newpass456") if changed else login("hijack789")
