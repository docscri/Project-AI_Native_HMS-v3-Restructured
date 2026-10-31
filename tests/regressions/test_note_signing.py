"""Who signed a note is kept, and signed notes cannot change."""

from fastapi.testclient import TestClient

from app.shared.db import connect
from app.main import app
from tests.helpers import clinic, started_visit, member, join


def test_signer_recorded_and_signed_note_cannot_change():
    with TestClient(app) as c:
        h, doc = clinic(c, "a3@x.in")
        b = join(c, member(c, h, "Dr. B", "drb3@x.in", "doctor", ["consultation", "patients"])["invite_code"])
        p = c.post("/api/patients", headers=h, json={"name": "Sig", "consent": True}).json()
        v = c.post("/api/visits/walk-in", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "payment_method": "cash"}).json()
        c.post(f"/api/visits/{v['id']}/start", headers=h)
        n = c.post(f"/api/visits/{v['id']}/note", headers=h).json()
        signed = c.post(f"/api/notes/{n['id']}/sign", headers=b).json()
        assert signed["signed_by_name"] == "Dr. B"
        page = c.get(f"/api/notes/{n['id']}/print", headers=b).text
        assert "Signed by Dr. B" in page
        assert c.put(f"/api/notes/{n['id']}", headers=h, json={"soap": {"S": "late edit", "O": "", "A": "", "P": ""}, "rx": []}).status_code == 409
        assert c.post(f"/api/notes/{n['id']}/sign", headers=h).status_code == 409
        assert c.get(f"/api/visits/{v['id']}", headers=h).json()["note"]["content"]["soap"]["S"] == ""
        # simulate the race past the earlier read
        db = connect()
        assert db.execute("update notes set content = 'x' where id = ? and status = 'draft'", (n["id"],)).rowcount == 0
        db.close()


def test_signer_survives_removal():
    with TestClient(app) as c:
        h, doc = clinic(c, "g2@x.in")
        inv = c.post("/api/members", headers=h, json={"name": "Dr. Two", "email": "two2@x.in", "kind": "doctor", "screens": ["consultation"]}).json()
        h2 = {"Authorization": "Bearer " + c.post("/api/invites/accept", json={"code": inv["invite_code"], "password": "doctor123"}).json()["token"]}
        v = started_visit(c, h, doc)
        n = c.post(f"/api/visits/{v['id']}/note", headers=h).json()
        c.post(f"/api/notes/{n['id']}/sign", headers=h2)
        r = c.delete(f"/api/members/{inv['id']}", headers=h).json()
        assert r["deactivated"] and not r["removed"]
        db = connect(); db.execute("update notes set signed_by = null where id = ?", (n["id"],)); db.commit(); db.close()
        page = c.get(f"/api/notes/{n['id']}/print", headers=h).text
        assert "Signed by Dr. Two" in page
