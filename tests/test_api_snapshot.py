"""Safety net for refactors: one clinic day through the API. Each call's status and response shape
(field names and types, not values) must match tests/snapshots/api.json. UPDATE_SNAPSHOT=1 rewrites it."""
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SNAP = Path(__file__).parent / "snapshots" / "api.json"
TODAY, TOMORROW = date.today().isoformat(), (date.today() + timedelta(days=1)).isoformat()


def shape(x):
    if isinstance(x, dict):   # keys that are record ids (D12, N3.A, 45) become one placeholder
        return {("<id>" if re.fullmatch(r"[A-Z]?\d+(\.[A-Z])?", k) else k): shape(v) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [shape(x[0])] if x else []
    return type(x).__name__


def routes():
    return sorted(f"{m.upper()} {p}" for p, ops in app.openapi()["paths"].items() for m in ops)


def day(c):
    out = {}

    def call(label, method, path, **kw):
        r = getattr(c, method)(path, **kw)
        try:
            body = shape(r.json())
        except ValueError:
            body = r.headers.get("content-type", "").split(";")[0]
        out[label] = {"status": r.status_code, "body": body}
        if os.environ.get("SHOW_ERRORS") and r.status_code >= 400:
            print("ERR", label, r.status_code, r.text[:300])
        return r

    owner = call("onboarding owner", "post", "/api/onboarding/owner", json={"name": "Dr. Snap", "email": "snap@x.in", "password": "clinic123", "is_doctor": True}).json()
    h = {"Authorization": "Bearer " + owner["token"]}
    call("onboarding owner edit", "put", "/api/onboarding/owner", headers=h, json={"name": "Dr. Snap", "email": "snap@x.in"})
    call("clinic edit", "put", "/api/clinic", headers=h, json={"name": "Snap Clinic", "phone": "0484 000000", "address": "MG Road"})
    call("clinic rules", "put", "/api/clinic/rules", headers=h, json={"fee": 300, "days": [0, 1, 2, 3, 4, 5, 6], "limit_by": "patients", "limit_value": 20,
                                                                      "token_timing": "booking", "sessions": [{"start": "00:00", "end": "23:59"}]})
    call("onboarding finish", "post", "/api/onboarding/finish", headers=h, json={})
    call("clinic", "get", "/api/clinic", headers=h)
    me = call("me", "get", "/api/me", headers=h).json()
    doc = me["member"]["id"]
    call("me edit", "put", "/api/me", headers=h, json={"name": "Dr. Snap", "email": "snap@x.in", "phone": "9847000000"})
    call("doctors", "get", "/api/doctors", headers=h)
    staff = call("member add", "post", "/api/members", headers=h, json={"name": "Desk", "email": "desk@x.in", "kind": "staff", "designation": "Nurse", "screens": ["operations"]}).json()
    call("members", "get", "/api/members", headers=h)
    call("member edit", "patch", f"/api/members/{staff['id']}", headers=h, json={"designation": "Front desk"})
    code = call("member invite", "post", f"/api/members/{staff['id']}/invite", headers=h, json={}).json()["invite_code"]
    call("invite read", "get", f"/api/invites/{code}")
    sh = {"Authorization": "Bearer " + call("invite accept", "post", "/api/invites/accept", json={"code": code, "password": "desk12345"}).json()["token"]}
    call("member reset link", "post", f"/api/members/{staff['id']}/reset-link", headers=h, json={})
    call("availability", "get", "/api/availability", headers=h, params={"doctor_id": doc, "date": TOMORROW})
    call("schedule", "get", f"/api/schedules/{doc}", headers=h, params={"month": TODAY[:7]})
    call("schedule day", "put", f"/api/schedules/{doc}/{TOMORROW}", headers=h, json={"is_off": False, "sessions": [{"start": "00:00", "end": "23:59"}], "limit_by": "patients", "limit_value": 10})
    call("schedule day reset", "delete", f"/api/schedules/{doc}/{TOMORROW}", headers=h)
    p = call("patient add", "post", "/api/patients", headers=sh, json={"name": "Snap Patient", "phone": "9847011111", "dob": "1980-01-02", "sex": "M", "consent": True}).json()
    p2 = call("patient add 2", "post", "/api/patients", headers=sh, json={"name": "Second", "phone": "9847022222", "consent": True}).json()
    call("patients search", "get", "/api/patients", headers=sh, params={"q": "Snap"})
    call("patients check", "get", "/api/patients/check", headers=sh, params={"phone": "9847011111"})
    call("patient", "get", f"/api/patients/{p['id']}", headers=h)
    call("patient edit", "patch", f"/api/patients/{p['id']}", headers=sh, json={"address": "Kochi"})
    b = call("booking", "post", "/api/visits", headers=sh, json={"patient_id": p2["id"], "doctor_id": doc, "date": TODAY}).json()
    call("late", "post", f"/api/visits/{b['id']}/late", headers=sh, json={})
    call("arrive", "post", f"/api/visits/{b['id']}/arrive", headers=sh, json={"payment_method": "upi"})
    call("queue move", "post", f"/api/visits/{b['id']}/queue", headers=sh, params={"direction": "down"})
    call("undo arrival", "post", f"/api/visits/{b['id']}/undo-arrival", headers=sh, json={"reason": "Wrong patient"})
    t = call("booking tomorrow", "post", "/api/visits", headers=sh, json={"patient_id": p2["id"], "doctor_id": doc, "date": TOMORROW}).json()
    call("reschedule", "post", f"/api/visits/{t['id']}/reschedule", headers=sh, json={"date": TOMORROW, "doctor_id": doc, "reason": "Patient asked"})
    call("cancel", "post", f"/api/visits/{t['id']}/cancel", headers=sh, json={"reason": "Patient asked"})
    w = call("walk-in", "post", "/api/visits/walk-in", headers=sh, json={"patient_id": p["id"], "doctor_id": doc, "payment_method": "cash"}).json()
    call("receipt", "get", f"/api/visits/{w['id']}/receipt", params={"token": sh["Authorization"][7:]})
    call("refund", "post", f"/api/visits/{w['id']}/refund", headers=sh, json={"amount": 50, "reason": "Charged twice"})
    call("day view", "get", "/api/operations/day", headers=sh, params={"date": TODAY})
    call("queue", "get", "/api/operations/queue", headers=sh, params={"doctor_id": doc, "date": TODAY})
    call("waitlist add", "post", "/api/waitlist", headers=sh, json={"patient_id": p2["id"], "doctor_id": doc, "date": TOMORROW})
    wl = call("waitlist", "get", "/api/waitlist", headers=sh, params={"doctor_id": doc, "date": TOMORROW}).json()
    call("consultation today", "get", "/api/consultation/today", headers=h, params={"doctor_id": doc})
    call("start", "post", f"/api/visits/{w['id']}/start", headers=h, json={})
    call("dictation provider", "get", "/api/dictation", headers=h)
    v = call("visit", "get", f"/api/visits/{w['id']}", headers=h).json()
    call("text", "put", f"/api/visits/{w['id']}/text", headers=h, json={"text": "Fever for two days. Temp 100.8 F. Likely viral fever. Paracetamol 650 mg three times a day for 3 days.", "rev": v["text_rev"]})
    call("document", "post", f"/api/visits/{w['id']}/documents", headers=h, files={"file": ("Lab.txt", b"Sunrise Diagnostics\nHbA1c: 8.9 %", "text/plain")})
    docs = c.get(f"/api/visits/{w['id']}", headers=h).json()["documents"]
    call("document file", "get", f"/api/documents/{docs[0]['id']}/file", headers=h)
    call("brief", "post", f"/api/visits/{w['id']}/brief", headers=h, json={})
    n = call("note draft", "post", f"/api/visits/{w['id']}/note/draft", headers=h, json={}).json()
    call("note edit", "put", f"/api/notes/{n['id']}", headers=h, json={"soap": n["content"]["soap"], "rx": n["content"]["rx"]})
    call("note sign", "post", f"/api/notes/{n['id']}/sign", headers=h, json={})
    call("note print", "get", f"/api/notes/{n['id']}/print", params={"token": h["Authorization"][7:]})
    call("follow-up", "post", f"/api/visits/{w['id']}/follow-up", headers=h, json={"date": TOMORROW})
    call("visit after", "get", f"/api/visits/{w['id']}", headers=h)
    call("attendance check-in", "post", "/api/attendance/check-in", headers=sh, json={})
    call("attendance me", "get", "/api/attendance/me", headers=sh)
    call("attendance check-out", "post", "/api/attendance/check-out", headers=sh, json={})
    call("attendance mark", "put", f"/api/attendance/{doc}/{TODAY}", headers=h, json={"status": "present", "check_in": "09:00"})
    lv = call("leave request", "post", "/api/leave", headers=sh, json={"start_date": TOMORROW, "end_date": TOMORROW, "reason": "Fever"}).json()
    call("leave list", "get", "/api/leave", headers=h, params={"month": TODAY[:7]})
    call("leave approve", "post", f"/api/leave/{lv['id']}/approve", headers=h, json={})
    call("team today", "get", "/api/team/today", headers=h)
    call("team register", "get", "/api/team/register", headers=h, params={"month": TODAY[:7]})
    call("collections", "get", "/api/collections", headers=h, params={"start": TODAY, "end": TODAY})
    call("day close read", "get", "/api/day-close", headers=h, params={"date": TODAY})
    call("day close", "post", "/api/day-close", headers=h, json={"date": TODAY, "counted_cash": 250})
    call("end session", "post", "/api/operations/end-session", headers=h, params={"doctor_id": doc, "date": TODAY})
    call("merge", "post", f"/api/patients/{p['id']}/merge", headers=h, json={"other_id": p2["id"]})
    call("change password", "post", "/api/auth/change-password", headers=sh, json={"current": "desk12345", "new": "desk67890"})
    call("forgot", "post", "/api/auth/forgot", json={"email": "desk@x.in"})
    call("reset bad code", "post", "/api/auth/reset", json={"code": "nope", "password": "abcd12345"})
    call("login", "post", "/api/auth/login", json={"email": "snap@x.in", "password": "clinic123"})
    call("logout", "post", "/api/auth/logout", headers=h, json={})
    call("health", "get", "/health")
    return out


def test_api_shapes_unchanged():
    with TestClient(app) as c:
        now = {"routes": routes(), "calls": day(c)}
    if os.environ.get("UPDATE_SNAPSHOT") or not SNAP.exists():
        SNAP.write_text(json.dumps(now, indent=1, sort_keys=True) + "\n")
    saved = json.loads(SNAP.read_text())
    assert now["routes"] == saved["routes"]
    if os.environ.get("DUMP_SNAPSHOT"):
        Path(os.environ["DUMP_SNAPSHOT"]).write_text(json.dumps(now, indent=1, sort_keys=True))
    for label, got in now["calls"].items():
        assert got == saved["calls"].get(label), label
    assert set(now["calls"]) == set(saved["calls"])
