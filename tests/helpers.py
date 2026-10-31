"""Shared test helpers: a fresh clinic and a started visit."""


def clinic(c, email):
    h = {"Authorization": "Bearer " + c.post("/api/onboarding/owner", json={"name": "Dr. " + email.split("@")[0], "email": email, "password": "clinic123", "is_doctor": True}).json()["token"]}
    c.put("/api/clinic/rules", headers=h, json={"fee": 300, "days": [0, 1, 2, 3, 4, 5, 6], "limit_by": "patients", "limit_value": 30,
                                                "token_timing": "booking", "sessions": [{"start": "00:00", "end": "23:59"}]})
    return h, c.get("/api/me", headers=h).json()["member"]["id"]


def started_visit(c, h, doc, name="Pat"):
    p = c.post("/api/patients", headers=h, json={"name": name, "consent": True}).json()
    v = c.post("/api/visits/walk-in", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "payment_method": "cash"}).json()
    c.post(f"/api/visits/{v['id']}/start", headers=h)
    return v


def member(c, h, name, email, kind, screens, admin=False):
    return c.post("/api/members", headers=h, json={"name": name, "email": email, "kind": kind, "screens": screens, "is_admin": admin}).json()


def join(c, code, pw="member123"):
    return {"Authorization": "Bearer " + c.post("/api/invites/accept", json={"code": code, "password": pw}).json()["token"]}
