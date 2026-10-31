"""Pay, refund and undo keep the money totals right."""
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.shared.db import connect
from app.main import app
from tests.helpers import clinic

TODAY = date.today().isoformat()


def test_pay_refund_pay_keeps_correct_totals():
    with TestClient(app) as c:
        h, doc = clinic(c, "a6@x.in")
        p = c.post("/api/patients", headers=h, json={"name": "Twice", "consent": True}).json()
        v = c.post("/api/visits", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": TODAY}).json()
        c.post(f"/api/visits/{v['id']}/arrive", headers=h, json={"payment_method": "cash"})
        c.post(f"/api/visits/{v['id']}/undo-arrival", headers=h, json={"reason": "Wrong patient"})
        c.post(f"/api/visits/{v['id']}/arrive", headers=h, json={"payment_method": "cash"})
        t = c.get("/api/collections", headers=h, params={"start": TODAY}).json()
        assert (t["collected"], t["refunded"], t["net"]) == (600, 300, 300)
        assert c.post(f"/api/visits/{v['id']}/refund", headers=h, json={"amount": 300, "reason": "Asked"}).status_code == 200
        assert c.get("/api/collections", headers=h, params={"start": TODAY}).json()["net"] == 0


def test_refund_offered_after_pay_undo_pay():
    with TestClient(app) as c:
        h, doc = clinic(c, "g3@x.in")
        p = c.post("/api/patients", headers=h, json={"name": "Twice", "consent": True}).json()
        v = c.post("/api/visits", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": TODAY}).json()
        c.post(f"/api/visits/{v['id']}/arrive", headers=h, json={"payment_method": "cash"})
        c.post(f"/api/visits/{v['id']}/undo-arrival", headers=h, json={"reason": "Wrong patient"})
        c.post(f"/api/visits/{v['id']}/arrive", headers=h, json={"payment_method": "cash"})
        q = c.get("/api/operations/queue", headers=h, params={"doctor_id": doc, "date": TODAY}).json()
        assert q["columns"]["waiting"][0]["refundable"] == 300


def test_upgrade_reconciles_old_undone_arrivals():
    with TestClient(app) as c:
        h, doc = clinic(c, "g4@x.in")
        p = c.post("/api/patients", headers=h, json={"name": "Old", "consent": True}).json()
        v = c.post("/api/visits", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": TODAY}).json()
        db = connect()
        # legacy state: payment cleared, only the refund imported
        db.execute("update visits set refund_amount = 300, refund_reason = 'Arrival undone', refunded_at = ? where id = ?", (f"{TODAY}T10:00:00", v["id"]))
        db.execute("insert into payments (clinic_id, visit_id, kind, amount, reason, at) select clinic_id, id, 'refund', 300, 'Arrival undone', ? from visits where id = ?",
                   (f"{TODAY}T10:00:00", v["id"]))
        sql = Path("migrations/011_review_gaps.sql").read_text()
        db.execute(sql[sql.index("insert into payments"):].rstrip().rstrip(";"))
        db.commit()
        held = db.execute("select sum(case when kind = 'payment' then amount else -amount end) from payments where visit_id = ?", (v["id"],)).fetchone()[0]
        db.close()
        assert held == 0
        c.post(f"/api/visits/{v['id']}/arrive", headers=h, json={"payment_method": "cash"})
        q = c.get("/api/operations/queue", headers=h, params={"doctor_id": doc, "date": TODAY}).json()
        assert q["columns"]["waiting"][0]["refundable"] == 300
