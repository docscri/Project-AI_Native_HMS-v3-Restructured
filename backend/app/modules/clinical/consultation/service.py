"""Doctor workspace: today's queue, calling in, free text, follow-up."""
import json
from datetime import date as Date

from app.core.member import clinic_doctor
from app.core.patient import age
from app.core.visit import get_visit, move, text_of, visit_rows
from app.modules.clinical.brief import service as brief
from app.modules.clinical.documents import service as documents
from app.modules.clinical.notes import service as notes
from app.shared.ai import llm
from app.shared.db import now
from app.shared.errors import Conflict, Invalid, NotFound
from app.shared.validate import valid_day
from . import repo


def today(db, me, doctor_id: int | None) -> dict:
    did = doctor_id or (me["id"] if me["kind"] == "doctor" else None)
    if not did:
        raise Invalid("Choose a doctor.")
    clinic_doctor(db, me, did)
    vs = visit_rows(db, me, "v.doctor_id = ? and v.date = ? and v.status in ('waiting', 'with_doctor', 'done')",
                    (did, Date.today().isoformat()))
    return {"doctor_id": did, "visits": vs}


def call_next(db, me, doctor_id: int | None) -> dict:
    did = doctor_id or me["id"]
    clinic_doctor(db, me, did)
    if repo.busy(db, did, Date.today().isoformat()):
        raise Conflict("Finish the current patient first.")
    v = repo.next_waiting(db, did, Date.today().isoformat())
    if not v:
        raise NotFound("No one is waiting.")
    move(db, me, v, "with_doctor", started_at=now())
    return workspace(db, me, v["id"])


def start(db, me, visit_id: int) -> dict:
    v = get_visit(db, me, visit_id)
    if repo.busy(db, v["doctor_id"], v["date"], visit_id):
        raise Conflict("Finish the current patient first.")
    move(db, me, v, "with_doctor", started_at=now())
    return workspace(db, me, visit_id)


def workspace(db, me, visit_id: int) -> dict:
    v = get_visit(db, me, visit_id)
    out = visit_rows(db, me, "v.id = ?", (visit_id,))[0]
    out["age"] = age(out["dob"])
    out["text"] = text_of(v)
    out["text_rev"] = v["dictation_rev"]
    saved = json.loads(v["brief"]) if v["brief"] else None
    out["brief"] = saved if saved and saved.get("basis") == brief.current_basis(db, v) else None   # rebuilt when stale
    out["documents"] = documents.load_docs(db, v["patient_id"])
    out["note"] = notes.load_note(db, visit_id)
    out["ai_enabled"] = llm.enabled()
    return out


def editable(db, v: dict) -> None:
    if v["status"] != "with_doctor":
        raise Conflict("Start the consultation first.")
    n = notes.load_note(db, v["id"])
    if n and n["status"] == "signed":
        raise Conflict("Note is signed.")


def save_text(db, me, visit_id: int, text: str, rev: int) -> dict:
    v = get_visit(db, me, visit_id)
    editable(db, v)
    if not repo.save_text(db, visit_id, text, rev):
        raise Conflict("Newer text was saved. Reloaded.")
    return {"ok": True, "length": len(text), "rev": repo.text_rev(db, visit_id)}


def add_segment(db, me, visit_id: int, segment: str) -> dict:
    v = get_visit(db, me, visit_id)
    editable(db, v)
    text = (text_of(v).rstrip() + "\n" + segment.strip()).strip()
    repo.set_text(db, visit_id, text)
    return {"text": text}


def follow_up(db, me, visit_id: int, day: str) -> dict:
    """Waitlists when the day is full."""
    from app.routes.operations import add_to_waitlist, create_booking
    v = get_visit(db, me, visit_id)
    day = valid_day(day)
    if day <= Date.today().isoformat() or day <= v["date"]:
        raise Invalid("Pick a later date.")
    db.lock(f"tokens:{v['doctor_id']}:{day}")
    try:
        out = create_booking(db, me, v["patient_id"], v["doctor_id"], day, follow_up_of=visit_id)
        return out | {"waitlisted": False}
    except Conflict as e:   # a full or ended day goes to the waitlist instead
        if e.message not in ("Session full.", "Session ended."):
            raise
        return add_to_waitlist(db, me, v["patient_id"], v["doctor_id"], day)
