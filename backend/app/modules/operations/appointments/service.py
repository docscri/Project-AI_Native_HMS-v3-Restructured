"""Front desk: queues, booking, arrival, reschedule, cancel."""
from datetime import date as Date

from app.shared.audit import log_event
from app.shared.db import now
from app.shared.errors import Conflict, Invalid, NotFound
from app.shared.validate import valid_day
from app.core.clinic import clinic_of
from app.core.clinic.schedule import day_schedule, doctor_fee, find_session, next_arrival_token, now_hhmm, require_bookable
from app.core.member import clinic_doctor
from app.core.visit import balance, doctor_letters, get_visit, ledger, move, visit_out, visit_rows
from app.modules.financial.payments.schema import Payment
from app.modules.financial.payments.service import charge
from app.modules.operations.appointments import repo
from app.modules.operations.appointments.schema import Booking, Cancel, Reschedule, WalkIn

CANCEL_REASONS = {"Patient request", "Doctor unavailable", "Booked by mistake", "Other"}


def auto_no_show(db, me, day: str) -> None:
    """No-show after session end; "late" patients wait until day end."""
    clinic = clinic_of(db, me)
    today, hhmm = Date.today().isoformat(), now_hhmm()
    for v in repo.booked_until(db, me["clinic_id"], day):
        if v["date"] < today:
            move(db, me, v, "no_show")
            continue
        if v["date"] > today or v["late"]:
            continue
        sess = find_session(day_schedule(db, clinic, v["doctor_id"], v["date"]), v["session_start"])
        if sess and hhmm >= sess["end"]:
            move(db, me, v, "no_show")


def day_view(db, me, date: str) -> dict:
    date = valid_day(date)
    auto_no_show(db, me, date)
    clinic = clinic_of(db, me)
    letters = doctor_letters(db, me["clinic_id"])
    visits = visit_rows(db, me, "v.date = ?", (date,))
    cards = []
    for d in repo.active_doctors(db, me["clinic_id"]):
        s = day_schedule(db, clinic, d["id"], date)
        if not s:
            continue
        mine = [v for v in visits if v["doctor_id"] == d["id"]]
        count = {st: sum(v["status"] == st for v in mine) for st in ("booked", "waiting", "with_doctor", "done", "no_show")}
        cards.append({"id": d["id"], "name": d["name"], "speciality": d["speciality"], "letter": letters[d["id"]],
                      "schedule": s, "used": sum(v["status"] not in ("cancelled", "no_show") for v in mine), "counts": count})
    return {
        "date": date,
        "doctors": cards,
        "stats": {st: sum(v["status"] == st for v in visits) for st in ("booked", "waiting", "with_doctor", "done")},
        "visits": [v for v in visits if v["status"] != "cancelled"],
    }


def queue(db, me, doctor_id: int, date: str) -> dict:
    date = valid_day(date)
    clinic_doctor(db, me, doctor_id)
    auto_no_show(db, me, date)
    clinic = clinic_of(db, me)
    vs = visit_rows(db, me, "v.doctor_id = ? and v.date = ?", (doctor_id, date))
    cols = {k: [v for v in vs if v["status"] == k] for k in ("booked", "waiting", "with_doctor", "done")}
    d = repo.doctor_brief(db, doctor_id)
    return {"doctor": d, "schedule": day_schedule(db, clinic, doctor_id, date), "token_timing": clinic["token_timing"],
            "columns": cols, "not_seen": [v for v in vs if v["status"] in ("cancelled", "no_show")]}


def check_patient_free(db, me, patient_id, doctor_id, day, exclude=None):
    if not repo.patient_exists(db, me["clinic_id"], patient_id):
        raise NotFound("Patient not found.")
    if repo.has_active_visit(db, patient_id, doctor_id, day, exclude):
        raise Conflict("Already booked with this doctor.")


def pick_token(avail: dict, wanted: int | None) -> int | None:
    if avail["token_timing"] != "booking":
        return None
    free = [t["token"] for t in avail["free_tokens"]]
    if wanted is None:
        return free[0]
    if wanted not in free:
        raise Conflict(f"Token {wanted} is taken.")
    return wanted


def book(db, me, body: Booking) -> dict:
    body.date = valid_day(body.date)
    clinic_doctor(db, me, body.doctor_id)
    db.lock(f"tokens:{body.doctor_id}:{body.date}")
    if body.date < Date.today().isoformat():
        raise Invalid("Pick today or a later date.")
    return create_booking(db, me, body.patient_id, body.doctor_id, body.date, body.session, body.token)


def create_booking(db, me, patient_id, doctor_id, day, session=None, wanted=None, follow_up_of=None) -> dict:
    """Caller must hold the token lock."""
    day = valid_day(day)
    clinic_doctor(db, me, doctor_id)
    clinic = clinic_of(db, me)
    check_patient_free(db, me, patient_id, doctor_id, day)
    avail = require_bookable(db, clinic, doctor_id, day, session=session)
    token = pick_token(avail, wanted)
    vid = repo.insert_booking(db, me["clinic_id"], patient_id, doctor_id, day, avail["session"], token, avail["fee"], follow_up_of)
    log_event(db, me["clinic_id"], me["id"], "visit", vid, "booked", {"token": token, "session": avail["session"], "follow_up_of": follow_up_of})
    repo.mark_waitlist_booked(db, vid, patient_id, doctor_id, day)
    v = visit_out(db, me, vid)
    s = avail["schedule"]
    v["tell_patient"] = (f"Token {v['token_label']}, come {'at' if s['exact_time'] else 'around'} {v['expected_time']}."
                         if token else f"Booked for {s['start']}–{s['end']}. Token is given on arrival.")
    return v


def walk_in(db, me, body: WalkIn) -> int:
    """Returns the new visit id; the caller commits and queues the brief."""
    today = Date.today().isoformat()
    clinic_doctor(db, me, body.doctor_id)
    db.lock(f"tokens:{body.doctor_id}:{today}")
    clinic = clinic_of(db, me)
    check_patient_free(db, me, body.patient_id, body.doctor_id, today)
    avail = require_bookable(db, clinic, body.doctor_id, today, session=body.session)
    session = avail["session"]
    token = avail["free_tokens"][0]["token"] if clinic["token_timing"] == "booking" else next_arrival_token(db, body.doctor_id, today, session)
    pay = charge(db, me, avail["fee"], body)
    vid = repo.insert_walk_in(db, me["clinic_id"], body.patient_id, body.doctor_id, today, session, token, avail["fee"], pay)
    ledger(db, me, vid, "payment", pay["amount_paid"], pay["payment_method"], pay["receipt_no"], at=pay["paid_at"])
    log_event(db, me["clinic_id"], me["id"], "visit", vid, "walk_in", {"token": token, "paid": pay["amount_paid"]})
    return vid


def arrive(db, me, visit_id: int, body: Payment) -> None:
    """The caller commits and queues the brief."""
    v = get_visit(db, me, visit_id)
    db.lock(f"tokens:{v['doctor_id']}:{v['date']}")
    v = get_visit(db, me, visit_id)
    if v["status"] != "booked":
        raise Conflict("This patient has already arrived.")
    if v["date"] != Date.today().isoformat():
        raise Conflict("Arrival only on the visit day.")
    clinic = clinic_of(db, me)
    token = v["token"]
    if clinic["token_timing"] == "arrival" or token is None:
        token = next_arrival_token(db, v["doctor_id"], v["date"], v["session_start"])
    pay = charge(db, me, v["fee"], body)
    move(db, me, v, "waiting", token=token, late=0, queue_order=token, **pay)
    ledger(db, me, visit_id, "payment", pay["amount_paid"], pay["payment_method"], pay["receipt_no"], at=pay["paid_at"])


def undo_arrival(db, me, visit_id: int, body: Cancel) -> dict:
    """Undo arrival and refund."""
    v = get_visit(db, me, visit_id)
    if v["status"] != "waiting" or v["is_walk_in"]:
        raise Conflict("This arrival can't be undone.")
    clinic = clinic_of(db, me)
    token = None if clinic["token_timing"] == "arrival" else v["token"]
    held, reason = balance(db, visit_id), body.reason.strip() or "Arrival undone"
    move(db, me, v, "booked", token=token, queue_order=None, arrived_at=None, paid_at=None, payment_method=None,
         amount_paid=None, discount=0, discount_reason=None, receipt_no=None,
         refund_amount=(v["refund_amount"] or 0) + held, refund_reason=reason,
         refunded_at=now() if held else v["refunded_at"])
    if held:
        ledger(db, me, visit_id, "refund", held, reason=reason)
    return visit_out(db, me, visit_id)


def reorder(db, me, visit_id: int, direction: str) -> dict:
    v = get_visit(db, me, visit_id)
    if v["status"] != "waiting":
        raise Conflict("Only waiting patients can be moved.")
    db.lock(f"tokens:{v['doctor_id']}:{v['date']}")
    line = repo.waiting_line(db, v["doctor_id"], v["date"], v["session_start"])
    for i, x in enumerate(line):
        x["queue_order"] = i + 1
    i = next(i for i, x in enumerate(line) if x["id"] == visit_id)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(line):
        line[i], line[j] = line[j], line[i]
    for k, x in enumerate(line):
        repo.set_queue_order(db, x["id"], k + 1)
    log_event(db, me["clinic_id"], me["id"], "visit", visit_id, "queue_moved", {"direction": direction})
    return {"ok": True}


def toggle_late(db, me, visit_id: int) -> dict:
    """Exempt from the session-end no-show rule."""
    v = get_visit(db, me, visit_id)
    if v["status"] != "booked":
        raise Conflict("Only booked patients can be late.")
    repo.set_late(db, visit_id, 0 if v["late"] else 1)
    log_event(db, me["clinic_id"], me["id"], "visit", visit_id, "late_off" if v["late"] else "late_on")
    return visit_out(db, me, visit_id)


def reschedule(db, me, visit_id: int, body: Reschedule) -> dict:
    body.date = valid_day(body.date)
    clinic_doctor(db, me, body.doctor_id)
    db.lock(f"tokens:{body.doctor_id}:{body.date}")
    v = get_visit(db, me, visit_id)
    if v["status"] != "booked":
        raise Conflict("Already arrived. Can't reschedule.")
    if body.date < Date.today().isoformat():
        raise Invalid("Pick today or a later date.")
    clinic = clinic_of(db, me)
    check_patient_free(db, me, v["patient_id"], body.doctor_id, body.date, exclude=visit_id)
    avail = require_bookable(db, clinic, body.doctor_id, body.date, exclude_visit=visit_id, session=body.session)
    token = pick_token(avail, body.token)
    repo.move_booking(db, visit_id, body.doctor_id, body.date, avail["session"], token, doctor_fee(db, clinic, body.doctor_id))
    log_event(db, me["clinic_id"], me["id"], "visit", visit_id, "rescheduled",
              {"from": v["date"], "to": body.date, "token": token, "reason": body.reason.strip() or None})
    return visit_out(db, me, visit_id)


def cancel(db, me, visit_id: int, body: Cancel) -> dict:
    v = get_visit(db, me, visit_id)
    move(db, me, v, "cancelled", cancel_reason=body.reason.strip() or None)
    return {"ok": True}


def end_session(db, me, doctor_id: int, date: str, session: str | None) -> dict:
    date = valid_day(date)
    clinic_doctor(db, me, doctor_id)
    n = 0
    for v in repo.booked_on(db, me["clinic_id"], doctor_id, date):
        if session and v["session_start"] != session:
            continue
        move(db, me, v, "no_show")
        n += 1
    return {"no_shows": n}


def list_doctors(db, me) -> list[dict]:
    letters = doctor_letters(db, me["clinic_id"])
    return [d | {"letter": letters[d["id"]]} for d in repo.doctor_list(db, me["clinic_id"])]
