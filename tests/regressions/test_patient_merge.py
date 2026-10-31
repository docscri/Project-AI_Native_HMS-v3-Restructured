"""Merging patients carries their waitlist entries."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import clinic


def test_merge_moves_waitlist_entries():
    with TestClient(app) as c:
        h, doc = clinic(c, "a7@x.in")
        a = c.post("/api/patients", headers=h, json={"name": "Keep", "consent": True}).json()
        b = c.post("/api/patients", headers=h, json={"name": "Dup", "consent": True}).json()
        c.post("/api/waitlist", headers=h, json={"patient_id": b["id"], "doctor_id": doc, "date": (date.today() + timedelta(days=1)).isoformat()})
        assert c.post(f"/api/patients/{a['id']}/merge", headers=h, json={"other_id": b["id"]}).status_code == 200
