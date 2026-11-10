"""A visit: one patient, one doctor, one day; its states, how it is read, and its payments."""
import json

from app.shared.audit import log_event
from app.shared.db import row, rows
from app.shared.errors import NotFound
from app.shared.states import VISIT

from ..clinic import clinic_of
from ..clinic.schedule import day_schedule, find_session, token_time
from .ledger import balance, ledger

def move(db, me, visit: dict, to: str, **fields) -> None:
    # Only from the status we read: if another request moved the visit meanwhile (arrived while being cancelled),
    # this one fails instead of overwriting it.
    VISIT.move(db, visit["id"], visit["status"], to, **fields)
    visit["status"] = to
    log_event(db, me["clinic_id"], me["id"], "visit", visit["id"], to, {k: v for k, v in fields.items() if v is not None} or None)


def get_visit(db, me, visit_id: int) -> dict:
    v = row(db.execute("select * from visits where id = ? and clinic_id = ?", (visit_id, me["clinic_id"])).fetchone())
    if not v:
        raise NotFound("Visit not found.")
    return v


def doctor_letters(db, clinic_id: int) -> dict[int, str]:
    """Per-doctor letter so tokens read A03, B12."""
    ids = [r[0] for r in db.execute("select id from members where clinic_id = ? and kind = 'doctor' order by id", (clinic_id,))]
    return {d: chr(65 + i % 26) for i, d in enumerate(ids)}


# Clinical text must never leave via Operations.
VISIT_FIELDS = ", ".join("v." + c for c in (
    "id", "clinic_id", "patient_id", "doctor_id", "date", "session_start", "token", "status", "is_walk_in", "fee",
    "payment_method", "paid_at", "arrived_at", "started_at", "completed_at", "cancel_reason", "created_at", "discount",
    "discount_reason", "amount_paid", "receipt_no", "refund_amount", "refund_reason", "refunded_at", "queue_order",
    "late", "follow_up_of"))


def visit_rows(db, me, where: str, args: tuple) -> list[dict]:
    clinic = clinic_of(db, me)
    letters = doctor_letters(db, me["clinic_id"])
    vs = rows(db.execute(
        f"""select {VISIT_FIELDS}, (select coalesce(sum(case when kind = 'payment' then amount else -amount end), 0)
                 from payments where visit_id = v.id) as refundable, p.name as patient_name, p.uhid, p.phone, p.dob, p.sex, m.name as doctor_name,
              (select count(*) from documents d where d.visit_id = v.id) as doc_count
            from visits v join patients p on p.id = v.patient_id join members m on m.id = v.doctor_id
            where v.clinic_id = ? and {where}
            order by v.session_start, coalesce(v.queue_order, v.token, 999), v.id""",
        (me["clinic_id"], *args)))
    scheds = {}
    for v in vs:
        key = (v["doctor_id"], v["date"])
        if key not in scheds:
            scheds[key] = day_schedule(db, clinic, *key)
        sess = find_session(scheds[key], v["session_start"])
        hide = v["status"] == "booked" and clinic["token_timing"] == "arrival"
        v["token_label"] = None if hide or not v["token"] else f'{letters.get(v["doctor_id"], "")}{v["token"]:02d}'
        v["expected_time"] = None if hide or not (sess and v["token"]) else token_time(sess, v["token"])
        v["session_label"] = sess["label"] if sess and len(scheds[key]["sessions"]) > 1 else None
        v["session_end"] = sess["end"] if sess else None
        v["late"] = bool(v["late"])
    return vs


def visit_out(db, me, visit_id: int) -> dict:
    return visit_rows(db, me, "v.id = ?", (visit_id,))[0]


def text_of(v: dict) -> str:
    """Legacy visits fall back to their joined dictation lines."""
    if v.get("dictation"):
        return v["dictation"]
    return "\n".join(s["text"] for s in json.loads(v["transcript"] or "[]"))
