"""Solo doctors: their own sign-up, places, visits that start at once, and nothing of the clinic's front desk or money."""
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import clinic


def solo(c, email="solo@x.in"):
    r = c.post("/api/onboarding/solo", json={"name": "Dr. Ravi Shankar", "email": email, "password": "solo1234", "speciality": "Psychiatry"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_a_solo_doctor_sees_only_patients_and_consultation():
    with TestClient(app) as c:
        h = solo(c)
        me = c.get("/api/me", headers=h).json()
        assert me["member"]["screens"] == ["patients", "consultation"] and me["member"]["speciality"] == "Psychiatry"
        assert me["clinic"]["solo"] is True and me["clinic"]["onboarded"] is True
        for method, path, body in [("GET", "/api/operations/day", None), ("GET", "/api/team/today", None), ("PUT", "/api/clinic/rules", {}),
                                   ("GET", "/api/day-close", None), ("POST", "/api/visits/walk-in", {"patient_id": 1, "doctor_id": 1, "payment_method": "cash"})]:
            assert c.request(method, path, headers=h, json=body).status_code in (403, 422), path   # refused, never served


def test_places_and_a_visit_that_starts_at_once():
    with TestClient(app) as c:
        h = solo(c, "solo2@x.in")
        city = c.post("/api/locations", headers=h, json={"name": "City Clinic"}).json()
        c.post("/api/locations", headers=h, json={"name": "Mercy OPD"})
        assert c.post("/api/locations", headers=h, json={"name": "city clinic"}).status_code == 409
        assert [l["name"] for l in c.get("/api/locations", headers=h).json()] == ["City Clinic", "Mercy OPD"]
        p = c.post("/api/patients", headers=h, json={"name": "Asha K", "consent": True, "sex": "F", "dob": "1990-02-01"}).json()   # phone optional
        v = c.post("/api/visits/quick", headers=h, json={"patient_id": p["id"], "location_id": city["id"]}).json()
        assert v["status"] == "with_doctor" and v["token"] is None and v["fee"] == 0 and v["location_id"] == city["id"]
        again = c.post("/api/visits/quick", headers=h, json={"patient_id": p["id"], "location_id": city["id"]}).json()
        assert again["id"] == v["id"]                                                 # the unfinished visit, not a second one
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Low mood for a month. Likely depression.", "rev": 0})
        n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
        assert n["content"]["template"]["department"] == "Psychiatry"
        assert c.post(f"/api/notes/{n['id']}/sign", headers=h).json()["status"] == "signed"
        prof = c.get(f"/api/patients/{p['id']}", headers=h).json()
        assert prof["visits"][0]["status"] == "done" and prof["visits"][0]["location"] == "City Clinic"
        assert c.delete(f"/api/locations/{city['id']}", headers=h).status_code == 200
        assert [l["name"] for l in c.get("/api/locations", headers=h).json()] == ["Mercy OPD"]
        assert c.get(f"/api/patients/{p['id']}", headers=h).json()["visits"][0]["location"] == "City Clinic"   # kept on past visits
        assert c.post("/api/visits/quick", headers=h, json={"patient_id": p["id"], "location_id": city["id"]}).status_code == 422


def test_solo_features_are_not_for_clinics_and_places_are_private():
    with TestClient(app) as c:
        h, _ = clinic(c, "not-solo@x.in")
        assert c.get("/api/locations", headers=h).status_code == 403
        p = c.post("/api/patients", headers=h, json={"name": "Clinic Pat", "consent": True}).json()
        assert c.post("/api/visits/quick", headers=h, json={"patient_id": p["id"]}).status_code == 403
        a, b = solo(c, "solo-a@x.in"), solo(c, "solo-b@x.in")
        place = c.post("/api/locations", headers=a, json={"name": "A's clinic"}).json()
        assert c.delete(f"/api/locations/{place['id']}", headers=b).status_code == 404
        pa = c.post("/api/patients", headers=a, json={"name": "A's patient", "consent": True}).json()
        assert c.post("/api/visits/quick", headers=b, json={"patient_id": pa["id"]}).status_code == 404   # another doctor's patient
