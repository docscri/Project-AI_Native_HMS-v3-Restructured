"""Documents SQL."""
import json

from app.shared.db import now, row, rows
from app.shared.states import DOCUMENT


def for_patient(db, patient_id: int) -> list[dict]:
    ds = rows(db.execute("select * from documents where patient_id = ? order by id desc", (patient_id,)))
    for d in ds:
        d["extracted"] = json.loads(d["extracted"]) if d["extracted"] else None
    return ds


def get(db, doc_id: int) -> dict | None:
    return row(db.execute("select * from documents where id = ?", (doc_id,)).fetchone())


def in_clinic(db, clinic_id: int, doc_id: int) -> dict | None:
    return row(db.execute("select * from documents where id = ? and clinic_id = ?", (doc_id, clinic_id)).fetchone())


def add(db, clinic_id: int, patient_id: int, visit_id: int, filename: str, path: str, mime: str) -> int:
    return db.execute(
        "insert into documents (clinic_id, patient_id, visit_id, filename, path, mime, created_at) values (?, ?, ?, ?, ?, ?, ?)",
        (clinic_id, patient_id, visit_id, filename, path, mime, now())).lastrowid


def listed(db, doc_id: int) -> dict | None:
    return row(db.execute("select id, filename, ai_status, created_at from documents where id = ?", (doc_id,)).fetchone())


def set_processing(db, doc_id: int, frm: str) -> None:
    DOCUMENT.move(db, doc_id, frm, "processing", extracted=None)


def set_read(db, doc_id: int, status: str, extracted: dict) -> None:
    assert DOCUMENT.can("processing", status), status
    db.execute("update documents set ai_status = ?, extracted = ? where id = ? and ai_status = 'processing'", (status, json.dumps(extracted), doc_id))


def for_visit(db, visit_id: int) -> list[dict]:
    return rows(db.execute("select id, filename, ai_status, created_at from documents where visit_id = ? order by id", (visit_id,)))


def note_signed(db, visit_id: int) -> bool:
    return bool(db.execute("select 1 from notes where visit_id = ? and status = 'signed'", (visit_id,)).fetchone())


def delete(db, doc_id: int) -> None:
    db.execute("delete from documents where id = ?", (doc_id,))


def cited_by_signed_note(db, patient_id: int, cite: str) -> bool:
    """A signed note of this patient, at any visit, cites the document."""
    return any(cite in ids for r in db.execute("select citations from notes where patient_id = ? and status = 'signed'", (patient_id,)).fetchall()
               for ids in json.loads(r[0] or "{}").values())


def uncite_in_drafts(db, patient_id: int, cite: str) -> None:
    """Takes a removed document out of every draft note of the patient, so signing can't keep a link to it."""
    for n in rows(db.execute("select id, citations from notes where patient_id = ? and status = 'draft'", (patient_id,))):
        cites = {k: [c for c in ids if c != cite] for k, ids in json.loads(n["citations"] or "{}").items()}
        db.execute("update notes set citations = ? where id = ? and status = 'draft'", (json.dumps(cites), n["id"]))
