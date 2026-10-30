"""Attendance rules: who works when, late, the day's status and the register."""
import calendar
import json
import re
from datetime import date as Date, timedelta

from app.core.clinic import clinic_of
from app.core.clinic.schedule import day_schedule
from app.modules.operations.team.leave import service as leave_service
from app.shared.audit import log_event
from app.shared.db import now
from app.shared.errors import Conflict, Invalid, NotFound
from app.shared.validate import valid_day
from . import repo

LATE_AFTER = 10  # minutes after the usual start


def members_of(db, clinic_id: int) -> list[dict]:
    return repo.members_of(db, clinic_id)


def works_on(db, clinic: dict, m: dict, day: str) -> tuple[bool, str | None]:
    if m["kind"] == "doctor":
        s = day_schedule(db, clinic, m["id"], day)
        return (s is not None, s and s["start"])
    days = json.loads(m["work_days"]) if m["work_days"] else json.loads(clinic["days"])
    return (Date.fromisoformat(day).isoweekday() % 7 in days, m["work_start"] or clinic["start"])


def late(check_in: str | None, start: str | None) -> bool:
    if not (check_in and start):
        return False
    h, mi = map(int, start.split(":"))
    return check_in[11:16] > f"{(h * 60 + mi + LATE_AFTER) // 60:02d}:{(h * 60 + mi + LATE_AFTER) % 60:02d}"


def day_status(db, clinic, m, day, att, leave) -> dict:
    working, start = works_on(db, clinic, m, day)
    a = att.get((m["id"], day))
    if (m["id"], day) in leave:
        st = "leave"
    elif a:
        st = a["status"]
    elif not working or day < since(m):
        st = "off"
    elif day < Date.today().isoformat():
        st = "absent"
    else:
        st = "due"          # not checked in yet
    return {"status": st, "working": working, "start": start,
            "check_in": a and a["check_in"], "check_out": a and a["check_out"], "note": a and a["note"]}


def attendance_on(db, clinic_id: int, start: str, end: str) -> dict:
    """Doctors who consulted count as present."""
    out = {(a["member_id"], a["date"]): a for a in repo.attendance_between(db, clinic_id, start, end)}
    for v in repo.consulted_between(db, clinic_id, start, end):
        out.setdefault((v["doctor_id"], v["date"]), {"status": "present", "check_in": v["first"], "check_out": v["last"], "note": "Consultations"})
    return out


def since(m: dict) -> str:
    return m["joined_on"] or (m["created_at"] or "")[:10]


def team_today(db, me, date: str | None) -> dict:
    day = date or Date.today().isoformat()
    clinic = clinic_of(db, me)
    att, leave = attendance_on(db, me["clinic_id"], day, day), leave_service.leave_days(db, me["clinic_id"], day, day)
    return {"date": day, "people": [m | day_status(db, clinic, m, day, att, leave) for m in members_of(db, me["clinic_id"])]}


def my_attendance(db, me) -> dict:
    today = Date.today().isoformat()
    a = repo.one(db, me["id"], today)
    return {"date": today, "check_in": a and a["check_in"], "check_out": a and a["check_out"]}


def check_in(db, me) -> dict:
    today, ts = Date.today().isoformat(), now()
    if repo.one(db, me["id"], today):
        raise Conflict("Already checked in.")
    _, start = works_on(db, clinic_of(db, me), repo.member(db, me["id"]), today)
    repo.add_check_in(db, me["clinic_id"], me["id"], today, "late" if late(ts, start) else "present", ts)
    return my_attendance(db, me)


def check_out(db, me) -> dict:
    today = Date.today().isoformat()
    if not repo.checked_in(db, me["id"], today):
        raise Conflict("Check in first.")
    repo.set_check_out(db, me["id"], today, now())
    return my_attendance(db, me)


def mark(db, me, member_id: int, date: str, body) -> dict:
    date = valid_day(date)
    if body.check_in and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", body.check_in):
        raise Invalid("Use times like 09:30.")
    if not repo.member_in(db, member_id, me["clinic_id"]):
        raise NotFound("Member not found.")
    if date > Date.today().isoformat():
        raise Invalid("Can't mark a future day.")
    if body.status == "clear":
        repo.clear(db, member_id, date)
    else:
        ci = f"{date}T{body.check_in}:00" if body.check_in else None
        repo.upsert(db, me["clinic_id"], member_id, date, body.status, ci, body.note.strip(), me["id"])
    log_event(db, me["clinic_id"], me["id"], "member", member_id, "attendance", {"date": date, "status": body.status})
    return {"ok": True}


def register(db, me, month: str, member_id: int | None) -> dict:
    """Non-admins see only themselves."""
    if not me["is_admin"]:
        member_id = me["id"]
    y, mo = map(int, month.split("-"))
    first, last = Date(y, mo, 1), Date(y, mo, calendar.monthrange(y, mo)[1])
    until = min(last, Date.today())
    clinic = clinic_of(db, me)
    att = attendance_on(db, me["clinic_id"], first.isoformat(), last.isoformat())
    leave = leave_service.leave_days(db, me["clinic_id"], first.isoformat(), last.isoformat())
    out = []
    for m in members_of(db, me["clinic_id"]):
        if member_id and m["id"] != member_id:
            continue
        c = {"working": 0, "present": 0, "late": 0, "half": 0, "leave": 0, "absent": 0}
        d = max(first, Date.fromisoformat(since(m))) if since(m) else first
        while d <= until:
            s = day_status(db, clinic, m, d.isoformat(), att, leave)
            if s["working"] or s["status"] in ("present", "late", "half"):
                c["working"] += s["working"]
                if s["status"] in c:
                    c[s["status"]] += 1
            d += timedelta(days=1)
        c["leave"] = sum(1 for (mid, day) in leave if mid == m["id"] and since(m) <= day <= until.isoformat())
        out.append({"id": m["id"], "name": m["name"], "kind": m["kind"], "role": m["speciality"] if m["kind"] == "doctor" else m["designation"], **c})
    return {"month": month, "people": out}
