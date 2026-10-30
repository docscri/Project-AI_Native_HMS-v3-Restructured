"""Patients of one clinic."""
from datetime import date as Date

from app.shared.db import row
from app.shared.errors import NotFound


def get_patient(db, me, patient_id: int) -> dict:
    p = row(db.execute("select * from patients where id = ? and clinic_id = ?", (patient_id, me["clinic_id"])).fetchone())
    if not p:
        raise NotFound("Patient not found.")
    return p


def age(dob: str | None) -> int | None:
    if not dob:
        return None
    b, t = Date.fromisoformat(dob), Date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))
