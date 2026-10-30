"""Waitlist SQL."""
from app.shared.db import now, row, rows


def is_waiting(db, patient_id, doctor_id, day) -> bool:
    return bool(db.execute("select 1 from waitlist where patient_id = ? and doctor_id = ? and date = ? and status = 'waiting'",
                           (patient_id, doctor_id, day)).fetchone())


def insert(db, clinic_id, patient_id, doctor_id, day, session, added_by) -> int:
    return db.execute("insert into waitlist (clinic_id, patient_id, doctor_id, date, session_start, added_by, created_at) values (?, ?, ?, ?, ?, ?, ?)",
                      (clinic_id, patient_id, doctor_id, day, session, added_by, now())).lastrowid


def waiting(db, clinic_id, doctor_id, day) -> list[dict]:
    return rows(db.execute(
        """select w.*, p.name as patient_name, p.uhid, p.phone from waitlist w join patients p on p.id = w.patient_id
           where w.clinic_id = ? and w.doctor_id = ? and w.date = ? and w.status = 'waiting' order by w.id""",
        (clinic_id, doctor_id, day)))


def get_waiting(db, clinic_id, wait_id) -> dict | None:
    return row(db.execute("select * from waitlist where id = ? and clinic_id = ? and status = 'waiting'", (wait_id, clinic_id)).fetchone())


def remove(db, clinic_id, wait_id) -> None:
    db.execute("update waitlist set status = 'removed' where id = ? and clinic_id = ?", (wait_id, clinic_id))
