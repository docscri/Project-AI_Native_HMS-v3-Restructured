"""Patient SQL."""
from app.shared.db import row, rows


def same_phone_or_name(db, clinic_id: int, name: str, phone: str, exclude: int | None) -> list[dict]:
    return rows(db.execute(
        """select id, uhid, name, phone, dob, sex from patients where clinic_id = ? and id is not ?
           and ((phone = ? and phone != '') or lower(name) = lower(?)) order by id""",
        (clinic_id, exclude, phone, name)))


def next_uhid(db, clinic_id: int) -> str:
    """Takes the clinic's next UHID; caller holds the uhid lock."""
    c = row(db.execute("select uhid_prefix, next_uhid from clinics where id = ?", (clinic_id,)).fetchone())
    db.execute("update clinics set next_uhid = next_uhid + 1 where id = ?", (clinic_id,))
    return f'{c["uhid_prefix"]}-{c["next_uhid"]:04d}'


def insert(db, clinic_id: int, uhid: str, data: dict, consent_at) -> int:
    return db.execute("insert into patients (clinic_id, uhid, name, dob, sex, phone, address, consent_at) values (?, ?, ?, ?, ?, ?, ?, ?)",
                      (clinic_id, uhid, data["name"], data.get("dob"), data.get("sex"), data.get("phone", ""), data.get("address", ""),
                       consent_at)).lastrowid


def search(db, clinic_id: int, like: str) -> list[dict]:
    return rows(db.execute(
        """select * from patients where clinic_id = ? and (lower(name) like ? or phone like ? or lower(uhid) like ?)
           order by created_at desc, id desc limit 50""",
        (clinic_id, like, like, like)))


def visits(db, patient_id: int) -> list[dict]:
    return rows(db.execute(
        """select v.id, v.date, v.status, v.token, m.name as doctor from visits v join members m on m.id = v.doctor_id
           where v.patient_id = ? order by v.date desc, v.id desc""", (patient_id,)))


def notes(db, patient_id: int) -> list[dict]:
    return rows(db.execute("select id, visit_id, status, content from notes where patient_id = ?", (patient_id,)))


def documents(db, patient_id: int) -> list[dict]:
    return rows(db.execute(
        "select id, visit_id, filename, ai_status, extracted, created_at from documents where patient_id = ? order by id desc",
        (patient_id,)))


def update(db, patient_id: int, changes: dict) -> None:
    db.execute(f"update patients set {', '.join(f'{k} = ?' for k in changes)} where id = ?", (*changes.values(), patient_id))


def same_day_visits(db, keep_id: int, other_id: int) -> bool:
    return bool(db.execute(
        """select 1 from visits a join visits b on a.doctor_id = b.doctor_id and a.date = b.date
           where a.patient_id = ? and b.patient_id = ? and a.status not in ('cancelled', 'no_show') and b.status not in ('cancelled', 'no_show')""",
        (keep_id, other_id)).fetchone())


def move_history(db, keep_id: int, other_id: int) -> None:
    for table in ("visits", "notes", "documents", "waitlist"):
        db.execute(f"update {table} set patient_id = ? where patient_id = ?", (keep_id, other_id))


def delete(db, patient_id: int) -> None:
    db.execute("delete from patients where id = ?", (patient_id,))
