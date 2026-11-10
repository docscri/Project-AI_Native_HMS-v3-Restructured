"""Solo SQL: the account, its locations, quick visits."""
from app.shared.db import row, rows


def create_solo_clinic(db, name: str) -> int:
    # Fee 0 and open every day: a solo doctor is paid by the clinics they visit, not through the app.
    return db.execute("insert into clinics (name, fee, days, onboarded, solo, uhid_prefix) values (?, 0, '[0,1,2,3,4,5,6]', 1, 1, 'DR')",
                      (name,)).lastrowid


def locations(db, clinic_id: int) -> list[dict]:
    return rows(db.execute("select id, name from locations where clinic_id = ? and archived = 0 order by name", (clinic_id,)))


def location(db, clinic_id: int, location_id: int) -> dict | None:
    return row(db.execute("select id, name, archived from locations where id = ? and clinic_id = ?", (location_id, clinic_id)).fetchone())


def add_location(db, clinic_id: int, name: str) -> int:
    return db.execute("insert into locations (clinic_id, name) values (?, ?)", (clinic_id, name)).lastrowid


def archive_location(db, location_id: int) -> None:
    db.execute("update locations set archived = 1 where id = ?", (location_id,))


def open_visit(db, patient_id: int, doctor_id: int, day: str) -> dict | None:
    """Today's unfinished visit for this patient, if any (opening it again is better than a second one)."""
    return row(db.execute("select id from visits where patient_id = ? and doctor_id = ? and date = ? and status in ('waiting', 'with_doctor')",
                          (patient_id, doctor_id, day)).fetchone())


def insert_quick_visit(db, clinic_id: int, patient_id: int, doctor_id: int, day: str, location_id, at: str) -> int:
    # Straight to "with the doctor": no token, no fee. paid_at marks it settled (nothing to pay), as the visit rules require.
    return db.execute(
        """insert into visits (clinic_id, patient_id, doctor_id, date, token, status, is_walk_in, fee, amount_paid, paid_at,
           arrived_at, started_at, location_id) values (?, ?, ?, ?, null, 'with_doctor', 1, 0, 0, ?, ?, ?, ?)""",
        (clinic_id, patient_id, doctor_id, day, at, at, at, location_id)).lastrowid
