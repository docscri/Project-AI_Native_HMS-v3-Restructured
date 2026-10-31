"""Team rules: who works when, late, the day's status, the register and leave."""
import calendar
import json
import re
from datetime import date as Date, timedelta

from app.core.clinic import clinic_of
from app.core.clinic.schedule import day_schedule
from app.modules.operations.scheduling.schema import Override
from app.modules.operations.scheduling.service import save_day
from app.shared.audit import log_event
from app.shared.auth import has_admin
from app.shared.db import now
from app.shared.errors import Conflict, Forbidden, Invalid, NotFound
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
    att, leave = attendance_on(db, me["clinic_id"], day, day), leave_days(db, me["clinic_id"], day, day)
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
    if not has_admin(me):
        member_id = me["id"]
    y, mo = map(int, month.split("-"))
    first, last = Date(y, mo, 1), Date(y, mo, calendar.monthrange(y, mo)[1])
    until = min(last, Date.today())
    clinic = clinic_of(db, me)
    att = attendance_on(db, me["clinic_id"], first.isoformat(), last.isoformat())
    leave = leave_days(db, me["clinic_id"], first.isoformat(), last.isoformat())
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


def leave_days(db, clinic_id: int, start: str, end: str) -> dict[tuple[int, str], dict]:
    out = {}
    for l in repo.approved_between(db, clinic_id, start, end):
        d = max(Date.fromisoformat(l["start_date"]), Date.fromisoformat(start))
        while d <= min(Date.fromisoformat(l["end_date"]), Date.fromisoformat(end)):
            out[(l["member_id"], d.isoformat())] = l
            d += timedelta(days=1)
    return out


def apply_doctor_leave(db, me, member_id: int, start: str, end: str, off: bool) -> None:
    m = repo.member_kind(db, member_id)
    if not m or m["kind"] != "doctor":
        return
    d = Date.fromisoformat(start)
    while d <= Date.fromisoformat(end):
        if off:
            save_day(db, me, member_id, d.isoformat(), Override(is_off=True))
        else:
            repo.drop_off_day(db, member_id, d.isoformat())
        d += timedelta(days=1)


def bookings_between(db, member_id: int, start: str, end: str) -> int:
    return repo.bookings_between(db, member_id, start, end)


def leave_one(db, me, lid: int) -> dict:
    l = repo.leave_one(db, me["clinic_id"], lid)
    if not l:
        raise NotFound("Leave not found.")
    l["days"] = (Date.fromisoformat(l["end_date"]) - Date.fromisoformat(l["start_date"])).days + 1
    return l


def request_leave(db, me, body) -> dict:
    try:
        body.start_date, body.end_date = valid_day(body.start_date), valid_day(body.end_date)
        a, b = Date.fromisoformat(body.start_date), Date.fromisoformat(body.end_date)
    except ValueError:
        raise Invalid("Pick valid dates.")
    if b < a:
        raise Invalid("End date is before start.")
    if (b - a).days > 92:
        raise Invalid("Pick at most three months.")
    who = body.member_id if body.member_id and has_admin(me) else me["id"]
    if not repo.member_in(db, who, me["clinic_id"]):
        raise NotFound("Member not found.")
    if repo.overlaps(db, who, body.start_date, body.end_date):
        raise Conflict("Leave already set for these days.")
    approved = has_admin(me)
    lid = repo.add(db, me["clinic_id"], who, body.start_date, body.end_date, body.type, body.reason.strip(),
                   "approved" if approved else "pending", me["id"] if approved else None, now() if approved else None, now())
    if approved:
        apply_doctor_leave(db, me, who, body.start_date, body.end_date, True)
    log_event(db, me["clinic_id"], me["id"], "member", who, "leave_" + ("approved" if approved else "requested"),
              {"from": body.start_date, "to": body.end_date})
    return leave_one(db, me, lid) | {"bookings_affected": bookings_between(db, who, body.start_date, body.end_date) if approved else 0}


def list_leave(db, me, month: str | None, mine: bool) -> list[dict]:
    """Non-admins see only their own."""
    where, args = "l.clinic_id = ?", [me["clinic_id"]]
    if mine or not has_admin(me):
        where += " and l.member_id = ?"
        args.append(me["id"])
    if month:
        y, mo = map(int, month.split("-"))
        where += " and (l.status = 'pending' or (l.start_date <= ? and l.end_date >= ?))"
        args += [f"{month}-{calendar.monthrange(y, mo)[1]:02d}", f"{month}-01"]
    return [leave_one(db, me, i) for i in repo.ids(db, where, args)]


def decide(db, me, leave_id: int, action: str) -> dict:
    l = leave_one(db, me, leave_id)
    if action == "cancel":
        if l["member_id"] != me["id"] and not has_admin(me):
            raise Forbidden("Not your leave.")
        if l["status"] == "approved":
            apply_doctor_leave(db, me, l["member_id"], l["start_date"], l["end_date"], False)
        repo.cancel(db, leave_id)
    elif action in ("approve", "reject"):
        if not has_admin(me):
            raise Forbidden("Only an admin can decide.")
        if l["status"] != "pending":
            raise Conflict("Already decided.")
        st = "approved" if action == "approve" else "rejected"
        repo.decide(db, leave_id, st, me["id"], now())
        if st == "approved":
            apply_doctor_leave(db, me, l["member_id"], l["start_date"], l["end_date"], True)
    else:
        raise NotFound("Unknown action.")
    log_event(db, me["clinic_id"], me["id"], "member", l["member_id"], "leave_" + action, {"from": l["start_date"], "to": l["end_date"]})
    return leave_one(db, me, leave_id) | {"bookings_affected": bookings_between(db, l["member_id"], l["start_date"], l["end_date"]) if action == "approve" else 0}
