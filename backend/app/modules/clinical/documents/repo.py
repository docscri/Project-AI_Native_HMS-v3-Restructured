"""Documents SQL."""
import json

from app.shared.db import now, row, rows


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


def set_read(db, doc_id: int, status: str, extracted: dict) -> None:
    db.execute("update documents set ai_status = ?, extracted = ? where id = ?", (status, json.dumps(extracted), doc_id))
