"""Notes SQL."""
from app.shared.states import NOTE
import json

from app.shared.db import now, row, rows


def for_visit(db, visit_id: int) -> dict | None:
    n = row(db.execute("select * from notes where visit_id = ?", (visit_id,)).fetchone())
    if n:
        n["content"] = json.loads(n["content"])
        n["citations"] = json.loads(n["citations"])
        n["sources"] = json.loads(n.get("sources") or "{}")
        n["addenda"] = addenda(db, n["id"])
    return n


def past(db, patient_id: int, before_visit: int) -> list[dict]:
    ns = rows(db.execute(
        """select n.*, v.date from notes n join visits v on v.id = n.visit_id
           where n.patient_id = ? and n.status = 'signed' and n.visit_id != ? order by v.date desc limit 5""",
        (patient_id, before_visit)))
    for n in ns:
        n["content"] = json.loads(n["content"])
        n["addenda"] = addenda(db, n["id"])
    return ns


def patient(db, patient_id: int) -> dict | None:
    return row(db.execute("select * from patients where id = ?", (patient_id,)).fetchone())


def get(db, note_id: int) -> dict | None:
    return row(db.execute("select * from notes where id = ?", (note_id,)).fetchone())


def in_clinic(db, clinic_id: int, note_id: int) -> dict | None:
    return row(db.execute("select * from notes where id = ? and clinic_id = ?", (note_id, clinic_id)).fetchone())


def redraft(db, note_id: int, content: str, citations: str, sources: str) -> bool:
    """False when the note was signed meanwhile."""
    return db.execute("update notes set content = ?, citations = ?, sources = ?, edited = 0, updated_at = ? where id = ? and status = 'draft'",
                      (content, citations, sources, now(), note_id)).rowcount == 1


def add(db, clinic_id: int, patient_id: int, visit_id: int, doctor_id: int, content: str, citations: str, sources: str | None = None) -> None:
    if sources is None:
        db.execute("insert into notes (clinic_id, patient_id, visit_id, doctor_id, content, citations) values (?, ?, ?, ?, ?, ?)",
                   (clinic_id, patient_id, visit_id, doctor_id, content, citations))
    else:
        db.execute("insert into notes (clinic_id, patient_id, visit_id, doctor_id, content, citations, sources) values (?, ?, ?, ?, ?, ?, ?)",
                   (clinic_id, patient_id, visit_id, doctor_id, content, citations, sources))


def save(db, note_id: int, content: str, edited: int) -> bool:
    return db.execute("update notes set content = ?, edited = ?, updated_at = ? where id = ? and status = 'draft'",
                      (content, edited, now(), note_id)).rowcount == 1


def sign(db, note_id: int, ts: str, member_id: int, name: str) -> None:
    # Only from draft, in the write itself, to block racing saves/signs.
    # The signer's signature image as it is now: changing it later never changes this note.
    sig = db.execute("select signature_id from members where id = ?", (member_id,)).fetchone()
    NOTE.move(db, note_id, "draft", "signed", signed_at=ts, signed_by=member_id, signed_by_name=name, signature_id=sig[0] if sig else None)


def visit(db, visit_id: int) -> dict | None:
    return row(db.execute("select * from visits where id = ?", (visit_id,)).fetchone())


def doctor(db, member_id: int) -> dict | None:
    return row(db.execute("select name, speciality from members where id = ?", (member_id,)).fetchone())


def document_ids(db, patient_id: int) -> set[int]:
    return {r[0] for r in db.execute("select id from documents where patient_id = ?", (patient_id,)).fetchall()}


def set_citations(db, note_id: int, citations: str) -> None:
    db.execute("update notes set citations = ? where id = ? and status = 'draft'", (citations, note_id))


def addenda(db, note_id: int) -> list[dict]:
    return rows(db.execute("select id, text, signed_by_name, signed_at from note_addenda where note_id = ? order by id", (note_id,)))


def add_addendum(db, clinic_id: int, note_id: int, text: str, member_id: int, name: str, at: str) -> None:
    db.execute("insert into note_addenda (clinic_id, note_id, text, signed_by, signed_by_name, signed_at) values (?, ?, ?, ?, ?, ?)",
               (clinic_id, note_id, text, member_id, name, at))
