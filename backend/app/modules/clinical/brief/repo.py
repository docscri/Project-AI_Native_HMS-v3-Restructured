"""Brief SQL."""
import json

from app.shared.db import row, rows


def signed_notes(db, patient_id: int, visit_id: int) -> list[dict]:
    """The patient's other signed notes, newest first."""
    notes = rows(db.execute(
        """select n.*, vv.date, vv.id as vid, m.name as doctor from notes n join visits vv on vv.id = n.visit_id
           join members m on m.id = vv.doctor_id
           where n.patient_id = ? and n.status = 'signed' and n.visit_id != ? order by vv.date desc, n.id desc""",
        (patient_id, visit_id)))
    for n in notes:
        n["content"] = json.loads(n["content"])
        n["addenda"] = rows(db.execute("select text, signed_by_name, signed_at from note_addenda where note_id = ? order by id", (n["id"],)))
    return notes


def finished_documents(db, patient_id: int) -> list[dict]:
    """Documents that were read, or that could not be read (the brief names those so they aren't missed)."""
    docs = rows(db.execute("select * from documents where patient_id = ? and ai_status in ('ready', 'failed') order by id desc", (patient_id,)))
    for d in docs:
        d["extracted"] = json.loads(d["extracted"]) if d["extracted"] else {}
    return docs


def save_values(db, note_id: int, vals: str) -> None:
    db.execute("update notes set vals = ? where id = ?", (vals, note_id))


def patient(db, patient_id: int) -> dict | None:
    return row(db.execute("select dob, sex from patients where id = ?", (patient_id,)).fetchone())


def visit(db, visit_id: int) -> dict | None:
    return row(db.execute("select * from visits where id = ?", (visit_id,)).fetchone())


def save_brief(db, visit_id: int, brief: str) -> None:
    db.execute("update visits set brief = ? where id = ?", (brief, visit_id))
