"""Clinical text, invite codes and other clinics' data stay out of reach."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import clinic, member, join

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def test_member_lists_never_leak_invite_codes():
    with TestClient(app) as c:
        h, _ = clinic(c, "a1@x.in")
        rec = join(c, member(c, h, "Desk", "desk1@x.in", "staff", ["operations"])["invite_code"])
        member(c, h, "New Admin", "na1@x.in", "staff", ["operations", "administration"], admin=True)
        for who in (rec, h):
            for m in c.get("/api/members", headers=who).json():
                assert "invite_code" not in m
        basic = c.get("/api/members", headers=rec).json()
        assert all(set(m) <= {"id", "name", "kind", "speciality", "designation", "status", "is_owner", "is_admin"} for m in basic)


def test_operations_never_send_consultation_text():
    with TestClient(app) as c:
        h, doc = clinic(c, "a2@x.in")
        rec = join(c, member(c, h, "Desk", "desk2@x.in", "staff", ["operations"])["invite_code"])
        p = c.post("/api/patients", headers=rec, json={"name": "Secret", "consent": True}).json()
        v = c.post("/api/visits/walk-in", headers=rec, json={"patient_id": p["id"], "doctor_id": doc, "payment_method": "cash"}).json()
        c.post(f"/api/visits/{v['id']}/start", headers=h)
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "CONFIDENTIAL history", "rev": 0})
        for path in ("/api/operations/day", f"/api/operations/queue?doctor_id={doc}"):
            r = c.get(path, headers=rec, params={"date": TODAY})
            assert "CONFIDENTIAL" not in r.text and "dictation" not in r.text


def test_other_clinics_doctor_is_refused_everywhere():
    with TestClient(app) as c:
        ha, da = clinic(c, "g6a@x.in")
        hb, db_ = clinic(c, "g6b@x.in")
        p = c.post("/api/patients", headers=ha, json={"name": "A pat", "consent": True}).json()
        mine = c.post("/api/visits", headers=ha, json={"patient_id": p["id"], "doctor_id": da, "date": TOMORROW}).json()
        p2 = c.post("/api/patients", headers=ha, json={"name": "A pat 2", "consent": True}).json()
        checks = [
            c.post("/api/visits", headers=ha, json={"patient_id": p2["id"], "doctor_id": db_, "date": TODAY}),
            c.post("/api/visits/walk-in", headers=ha, json={"patient_id": p2["id"], "doctor_id": db_, "payment_method": "cash"}),
            c.post(f"/api/visits/{mine['id']}/reschedule", headers=ha, json={"doctor_id": db_, "date": TOMORROW}),
            c.post("/api/waitlist", headers=ha, json={"patient_id": p2["id"], "doctor_id": db_, "date": TOMORROW}),
            c.get("/api/waitlist", headers=ha, params={"doctor_id": db_, "date": TODAY}),
            c.get("/api/operations/queue", headers=ha, params={"doctor_id": db_, "date": TODAY}),
            c.get("/api/availability", headers=ha, params={"doctor_id": db_, "date": TODAY}),
            c.post("/api/operations/end-session", headers=ha, params={"doctor_id": db_, "date": TODAY}),
            c.get("/api/consultation/today", headers=ha, params={"doctor_id": db_}),
            c.post("/api/consultation/next", headers=ha, params={"doctor_id": db_}),
        ]
        assert [r.status_code for r in checks] == [404] * len(checks)
        assert "Dr. g6b" not in checks[5].text
