"""Bad dates and times are refused with 422, never saved or crashing."""
from datetime import date

from fastapi.testclient import TestClient

from app.shared.db import connect
from app.main import app
from tests.helpers import clinic, member

TODAY = date.today().isoformat()


def test_bad_dates_and_times_are_422_not_500():
    with TestClient(app) as c:
        h, doc = clinic(c, "a8@x.in")
        assert c.get("/api/team/register", headers=h, params={"month": "2026-13"}).status_code == 422
        assert c.get("/api/collections", headers=h, params={"start": "2026-02-30"}).status_code == 422
        assert c.get(f"/api/schedules/{doc}", headers=h, params={"month": "2026-00"}).status_code == 422
        m = member(c, h, "Desk", "desk8@x.in", "staff", ["operations"])
        assert c.patch(f"/api/members/{m['id']}", headers=h, json={"work_start": "25:99"}).status_code == 422
        assert c.put(f"/api/schedules/{doc}/{TODAY}", headers=h, json={"is_off": False, "sessions": [{"start": "9am", "end": "13:00"}],
                                                                       "limit_by": "patients", "limit_value": 5}).status_code == 422


def test_invalid_dates_are_refused_before_saving():
    with TestClient(app) as c:
        h, doc = clinic(c, "g5@x.in")
        assert c.put(f"/api/schedules/{doc}/not-a-date", headers=h, json={"is_off": True}).status_code == 422
        inv = c.post("/api/members", headers=h, json={"name": "S", "email": "s5@x.in", "kind": "staff", "screens": ["operations"]}).json()
        assert c.patch(f"/api/members/{inv['id']}", headers=h, json={"joined_on": "not-a-date"}).status_code == 422
        assert c.patch(f"/api/members/{inv['id']}", headers=h, json={"joined_on": "2026-02-30"}).status_code == 422
        p = c.post("/api/patients", headers=h, json={"name": "D", "consent": True}).json()
        assert c.post("/api/visits", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": "2999-99-99"}).status_code == 422
        assert c.post("/api/waitlist", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": "soon"}).status_code == 422
        assert c.post("/api/leave", headers=h, json={"start_date": "x", "end_date": "y"}).status_code == 422
        assert c.put(f"/api/attendance/{doc}/{TODAY}", headers=h, json={"status": "present", "check_in": "9am"}).status_code == 422
        db = connect()
        assert db.execute("select count(*) from schedule_overrides where date = 'not-a-date'").fetchone()[0] == 0
        assert db.execute("select joined_on from members where id = ?", (inv["id"],)).fetchone()[0] is None
        db.close()
