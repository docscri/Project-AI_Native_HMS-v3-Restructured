"""Clinic hours with per-day overrides."""
import calendar
from datetime import date as Date, timedelta

from app.shared.audit import log_event
from app.shared.auth import has_admin
from app.shared.errors import Forbidden, Invalid, NotFound
from app.shared.validate import valid_day
from app.core.clinic import clinic_of
from app.core.clinic.schedule import availability, day_schedule, validate_sessions
from app.core.member import clinic_doctor
from app.modules.operations.scheduling import repo
from app.modules.operations.scheduling.schema import Leave, Override


def can_edit(me: dict, doctor_id: int) -> None:
    if me["id"] != doctor_id and "operations" not in me["screens"] and not has_admin(me):
        raise Forbidden("You can't change this schedule.")


def doctor(db, me, doctor_id: int) -> dict:
    d = repo.doctor(db, me["clinic_id"], doctor_id)
    if not d:
        raise NotFound("Doctor not found.")
    return d


def month(db, me, doctor_id: int, month: str) -> list[dict]:
    doctor(db, me, doctor_id)
    clinic = clinic_of(db, me)
    y, m = map(int, month.split("-"))
    days = []
    for d in range(1, calendar.monthrange(y, m)[1] + 1):
        day = f"{y:04d}-{m:02d}-{d:02d}"
        s = day_schedule(db, clinic, doctor_id, day)
        days.append({"date": day, "off": s is None, "override": repo.has_override(db, doctor_id, day), "schedule": s})
    return days


def save_day(db, me, doctor_id: int, day: str, body: Override) -> None:
    sessions = None
    if not body.is_off:
        raw = [x.model_dump() for x in body.sessions] or ([{"start": body.start, "end": body.end}] if body.start and body.end else [])
        sessions = validate_sessions(raw)
        if not (body.limit_by and body.limit_value):
            raise Invalid("Set the patient limit.")
    repo.upsert_override(db, me["clinic_id"], doctor_id, day, body.is_off, sessions, body.limit_by, body.limit_value)


def set_day(db, me, doctor_id: int, date: str, body: Override) -> dict:
    date = valid_day(date)
    doctor(db, me, doctor_id)
    can_edit(me, doctor_id)
    save_day(db, me, doctor_id, date, body)
    log_event(db, me["clinic_id"], me["id"], "schedule", doctor_id, "day_changed", {"date": date, **body.model_dump()})
    return {"date": date, "schedule": day_schedule(db, clinic_of(db, me), doctor_id, date),
            "bookings_affected": repo.bookings_on(db, [doctor_id], [date]) if body.is_off else 0}


def leave(db, me, body: Leave) -> dict:
    try:
        body.start_date, body.end_date = valid_day(body.start_date), valid_day(body.end_date)
        a, b = Date.fromisoformat(body.start_date), Date.fromisoformat(body.end_date)
    except ValueError:
        raise Invalid("Pick valid dates.")
    if b < a:
        raise Invalid("End date is before start.")
    if (b - a).days > 92:
        raise Invalid("Pick at most three months at a time.")
    if body.doctor_id:
        doctor(db, me, body.doctor_id)
        can_edit(me, body.doctor_id)
        ids = [body.doctor_id]
    else:
        if not has_admin(me):
            raise Forbidden("Only an admin can set holidays.")
        ids = repo.active_doctor_ids(db, me["clinic_id"])
    days = [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]
    for d in ids:
        for day in days:
            if body.off:
                save_day(db, me, d, day, Override(is_off=True))
            else:
                repo.delete_override(db, d, day)
    if body.doctor_id:  # keep Team → Leave in sync
        if body.off:
            repo.add_approved_leave(db, me["clinic_id"], body.doctor_id, body.start_date, body.end_date, me["id"])
        else:
            repo.cancel_approved_leave(db, body.doctor_id, body.start_date, body.end_date)
    log_event(db, me["clinic_id"], me["id"], "schedule", body.doctor_id, "leave" if body.off else "leave_cleared",
              {"from": body.start_date, "to": body.end_date, "all_doctors": not body.doctor_id})
    return {"days": len(days), "doctors": len(ids), "bookings_affected": repo.bookings_on(db, ids, days) if body.off else 0}


def reset_day(db, me, doctor_id: int, date: str) -> dict:
    date = valid_day(date)
    doctor(db, me, doctor_id)
    can_edit(me, doctor_id)
    repo.delete_clinic_override(db, me["clinic_id"], doctor_id, date)
    return {"date": date, "schedule": day_schedule(db, clinic_of(db, me), doctor_id, date)}


def get_availability(db, me, doctor_id: int, date: str, exclude_visit: int | None, session: str | None) -> dict:
    date = valid_day(date)
    clinic_doctor(db, me, doctor_id)
    return availability(db, clinic_of(db, me), doctor_id, date, exclude_visit, session)
