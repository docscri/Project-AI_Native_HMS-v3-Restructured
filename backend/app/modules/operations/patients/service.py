"""Patient rules: field checks, duplicates, register, merge."""
import json
from datetime import date

from app.shared.audit import log_event
from app.shared.db import now
from app.shared.errors import Conflict, Invalid
from app.shared.validate import clean_phone
from app.core.patient import get_patient
from . import repo


def clean(body) -> dict:
    """Returns only the fields that were sent."""
    out = body.model_dump(exclude_none=True)
    if "name" in out:
        out["name"] = " ".join(out["name"].split())
        if not 1 <= len(out["name"]) <= 80:
            raise Invalid("Enter the patient's full name.")
    if "phone" in out:
        out["phone"] = clean_phone(out["phone"])
    if out.get("dob"):
        try:
            dob = date.fromisoformat(out["dob"])
        except ValueError:
            raise Invalid("Enter a valid date of birth.")
        if dob > date.today():
            raise Invalid("Date of birth can't be in the future.")
        if (date.today() - dob).days > 120 * 366:
            raise Invalid("Check the date of birth.")
    elif "dob" in out:
        out["dob"] = None
    if "address" in out:
        out["address"] = " ".join(out["address"].split())
        if len(out["address"]) > 200:
            raise Invalid("Address is too long.")
    if out.get("sex") and out["sex"] not in ("M", "F", "O"):
        raise Invalid("Pick male, female or other.")
    return out


def similar(db, clinic_id: int, name: str, phone: str, dob: str | None, exclude: int | None = None) -> list[dict]:
    """Same phone, or same name (and DOB when both known)."""
    found = repo.same_phone_or_name(db, clinic_id, name, phone, exclude)
    return [p for p in found if p["phone"] == phone and phone or not (dob and p["dob"] and p["dob"] != dob)]


def check(db, me: dict, name: str, phone: str, dob: str | None) -> list[dict]:
    return similar(db, me["clinic_id"], " ".join(name.split()), clean_phone(phone), dob or None)


def register(db, me: dict, body) -> dict:
    if not body.consent:
        raise Invalid("Patient consent is needed.")
    data = clean(body)
    data.pop("consent", None)
    db.lock(f"uhid:{me['clinic_id']}")
    uhid = repo.next_uhid(db, me["clinic_id"])
    pid = repo.insert(db, me["clinic_id"], uhid, data, now())
    log_event(db, me["clinic_id"], me["id"], "patient", pid, "registered")
    return get_patient(db, me, pid) | {"similar": similar(db, me["clinic_id"], data["name"], data.get("phone", ""), data.get("dob"), pid)}


def search(db, me: dict, q: str) -> list[dict]:
    return repo.search(db, me["clinic_id"], f"%{q.strip().lower()}%")


def profile(db, me: dict, patient_id: int) -> dict:
    p = get_patient(db, me, patient_id)
    visits = repo.visits(db, patient_id)
    notes = {n["visit_id"]: n for n in repo.notes(db, patient_id)}
    docs = repo.documents(db, patient_id)
    for d in docs:
        d["extracted"] = json.loads(d["extracted"]) if d["extracted"] else None
    for v in visits:
        n = notes.get(v["id"])
        v["note"] = n and {"id": n["id"], "status": n["status"], **json.loads(n["content"])}
        v["documents"] = [d for d in docs if d["visit_id"] == v["id"]]
    return p | {"visits": visits, "documents": docs}


def edit(db, me: dict, patient_id: int, body) -> dict:
    get_patient(db, me, patient_id)
    changes = clean(body)
    if changes:
        repo.update(db, patient_id, changes)
        log_event(db, me["clinic_id"], me["id"], "patient", patient_id, "edited", changes)
    return get_patient(db, me, patient_id)


def merge(db, me: dict, patient_id: int, other_id: int) -> dict:
    """Move the other record's history here, then delete it."""
    keep = get_patient(db, me, patient_id)
    other = get_patient(db, me, other_id)
    if keep["id"] == other["id"]:
        raise Invalid("Pick a different patient.")
    if repo.same_day_visits(db, keep["id"], other["id"]):
        raise Conflict("Both have a visit that day. Cancel one.")
    repo.move_history(db, keep["id"], other["id"])
    fill = {k: other[k] for k in ("dob", "sex", "phone", "address") if not keep[k] and other[k]}
    if fill:
        repo.update(db, keep["id"], fill)
    repo.delete(db, other["id"])
    log_event(db, me["clinic_id"], me["id"], "patient", keep["id"], "merged", {"removed": other["uhid"], "name": other["name"]})
    return get_patient(db, me, keep["id"])
