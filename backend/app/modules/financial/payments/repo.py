"""Receipt numbers, refunds and receipt lookups."""
from app.shared.db import now, row


def take_receipt_no(db, clinic_id: int) -> int:
    """Caller must hold the receipt lock."""
    receipt = db.execute("select next_receipt from clinics where id = ?", (clinic_id,)).fetchone()[0]
    db.execute("update clinics set next_receipt = next_receipt + 1 where id = ?", (clinic_id,))
    return receipt


def set_refund(db, visit_id: int, total: int, reason: str) -> None:
    db.execute("update visits set refund_amount = ?, refund_reason = ?, refunded_at = ? where id = ?",
               (total, reason, now(), visit_id))


def visit(db, clinic_id: int, visit_id: int) -> dict | None:
    return row(db.execute("select * from visits where id = ? and clinic_id = ?", (visit_id, clinic_id)).fetchone())


def patient(db, patient_id: int) -> dict | None:
    return row(db.execute("select * from patients where id = ?", (patient_id,)).fetchone())


def doctor(db, doctor_id: int) -> dict | None:
    return row(db.execute("select name, speciality from members where id = ?", (doctor_id,)).fetchone())
