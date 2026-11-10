"""Visit booking and queue SQL."""
from app.core.clinic.schedule import ACTIVE
from app.shared.db import now, row, rows


def booked_until(db, clinic_id: int, day: str) -> list[dict]:
    return rows(db.execute("select * from visits where clinic_id = ? and date <= ? and status = 'booked'", (clinic_id, day)))


def booked_on(db, clinic_id: int, doctor_id: int, day: str) -> list[dict]:
    return rows(db.execute("select * from visits where clinic_id = ? and doctor_id = ? and date = ? and status = 'booked'",
                           (clinic_id, doctor_id, day)))


def active_doctors(db, clinic_id: int) -> list[dict]:
    return rows(db.execute("select * from members where clinic_id = ? and kind = 'doctor' and status != 'inactive' order by id",
                           (clinic_id,)))


def doctor_list(db, clinic_id: int) -> list[dict]:
    return rows(db.execute("select id, name, speciality, fee_override, status from members where clinic_id = ? and kind = 'doctor' and status != 'inactive' order by id",
                           (clinic_id,)))


def doctor_brief(db, doctor_id: int) -> dict | None:
    return row(db.execute("select id, name, speciality from members where id = ?", (doctor_id,)).fetchone())


def patient_exists(db, clinic_id: int, patient_id: int) -> bool:
    return bool(db.execute("select 1 from patients where id = ? and clinic_id = ?", (patient_id, clinic_id)).fetchone())


def has_active_visit(db, patient_id, doctor_id, day, exclude=None) -> bool:
    return bool(db.execute(f"select 1 from visits where patient_id = ? and doctor_id = ? and date = ? and {ACTIVE} and id is not ?",
                           (patient_id, doctor_id, day, exclude)).fetchone())


def insert_booking(db, clinic_id, patient_id, doctor_id, day, session, token, fee, follow_up_of) -> int:
    return db.execute(
        "insert into visits (clinic_id, patient_id, doctor_id, date, session_start, token, status, fee, follow_up_of) values (?, ?, ?, ?, ?, ?, 'booked', ?, ?)",
        (clinic_id, patient_id, doctor_id, day, session, token, fee, follow_up_of)).lastrowid


def mark_waitlist_booked(db, visit_id, patient_id, doctor_id, day) -> None:
    db.execute("update waitlist set status = 'booked', visit_id = ? where patient_id = ? and doctor_id = ? and date = ? and status = 'waiting'",
               (visit_id, patient_id, doctor_id, day))


def insert_walk_in(db, clinic_id, patient_id, doctor_id, day, session, token, fee, pay: dict) -> int:
    return db.execute(
        """insert into visits (clinic_id, patient_id, doctor_id, date, session_start, token, status, is_walk_in, fee,
           payment_method, discount, discount_reason, amount_paid, receipt_no, paid_at, arrived_at, queue_order)
           values (?, ?, ?, ?, ?, ?, 'waiting', 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (clinic_id, patient_id, doctor_id, day, session, token, fee, pay["payment_method"],
         pay["discount"], pay["discount_reason"], pay["amount_paid"], pay["receipt_no"], pay["paid_at"], pay["arrived_at"],
         token)).lastrowid


def waiting_line(db, doctor_id, day, session) -> list[dict]:
    return rows(db.execute(
        "select id, queue_order from visits where doctor_id = ? and date = ? and session_start = ? and status = 'waiting' order by queue_order, token, id",
        (doctor_id, day, session)))


def set_queue_order(db, visit_id: int, order: int) -> None:
    db.execute("update visits set queue_order = ? where id = ?", (order, visit_id))


def set_late(db, visit_id: int, late: int) -> None:
    db.execute("update visits set late = ? where id = ?", (late, visit_id))


def move_booking(db, visit_id, doctor_id, day, session, token, fee) -> None:
    db.execute("update visits set doctor_id = ?, date = ?, session_start = ?, token = ?, fee = ?, late = 0 where id = ?",
               (doctor_id, day, session, token, fee, visit_id))


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


def get_entry(db, clinic_id, wait_id) -> dict | None:
    return row(db.execute("select * from waitlist where id = ? and clinic_id = ?", (wait_id, clinic_id)).fetchone())
