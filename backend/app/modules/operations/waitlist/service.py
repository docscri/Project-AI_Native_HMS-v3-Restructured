"""Patients waiting for a full day to open up."""
from datetime import date as Date

from app.shared.audit import log_event
from app.shared.errors import Conflict, Invalid, NotFound
from app.shared.validate import valid_day
from app.core.clinic import clinic_of
from app.core.clinic.schedule import availability
from app.core.member import clinic_doctor
from app.modules.operations.appointments.service import check_patient_free, create_booking
from app.modules.operations.waitlist import repo
from app.modules.operations.waitlist.schema import WaitIn


def add_to_waitlist(db, me, patient_id, doctor_id, day, session=None) -> dict:
    check_patient_free(db, me, patient_id, doctor_id, day)
    if repo.is_waiting(db, patient_id, doctor_id, day):
        raise Conflict("Already on the waitlist.")
    wid = repo.insert(db, me["clinic_id"], patient_id, doctor_id, day, session, me["id"])
    log_event(db, me["clinic_id"], me["id"], "visit", None, "waitlisted", {"patient_id": patient_id, "date": day})
    return {"id": wid, "waitlisted": True, "date": day}


def join(db, me, body: WaitIn) -> dict:
    body.date = valid_day(body.date)
    clinic_doctor(db, me, body.doctor_id)
    if body.date < Date.today().isoformat():
        raise Invalid("Pick today or a later date.")
    return add_to_waitlist(db, me, body.patient_id, body.doctor_id, body.date, body.session)


def waitlist(db, me, doctor_id: int, date: str) -> dict:
    date = valid_day(date)
    clinic_doctor(db, me, doctor_id)
    items = repo.waiting(db, me["clinic_id"], doctor_id, date)
    a = availability(db, clinic_of(db, me), doctor_id, date) if items else {"available": False}
    return {"items": items, "open": bool(a.get("available"))}


def book(db, me, wait_id: int) -> dict:
    w = repo.get_waiting(db, me["clinic_id"], wait_id)
    if not w:
        raise NotFound("Not on the waitlist.")
    db.lock(f"tokens:{w['doctor_id']}:{w['date']}")
    return create_booking(db, me, w["patient_id"], w["doctor_id"], w["date"], w["session_start"])


def leave(db, me, wait_id: int) -> dict:
    repo.remove(db, me["clinic_id"], wait_id)
    return {"ok": True}
