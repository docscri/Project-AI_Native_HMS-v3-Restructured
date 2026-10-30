"""Leave rules; approved doctor leave marks the doctor's schedule off."""
import calendar
from datetime import date as Date, timedelta

from app.modules.operations.scheduling.schema import Override
from app.modules.operations.scheduling.service import save_day
from app.shared.audit import log_event
from app.shared.db import now
from app.shared.errors import Conflict, Forbidden, Invalid, NotFound
from app.shared.validate import valid_day
from . import repo


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
    l = repo.one(db, me["clinic_id"], lid)
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
    who = body.member_id if body.member_id and me["is_admin"] else me["id"]
    if not repo.member_in(db, who, me["clinic_id"]):
        raise NotFound("Member not found.")
    if repo.overlaps(db, who, body.start_date, body.end_date):
        raise Conflict("Leave already set for these days.")
    approved = me["is_admin"]
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
    if mine or not me["is_admin"]:
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
        if l["member_id"] != me["id"] and not me["is_admin"]:
            raise Forbidden("Not your leave.")
        if l["status"] == "approved":
            apply_doctor_leave(db, me, l["member_id"], l["start_date"], l["end_date"], False)
        repo.cancel(db, leave_id)
    elif action in ("approve", "reject"):
        if not me["is_admin"]:
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
