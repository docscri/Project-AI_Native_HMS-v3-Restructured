"""Leave SQL."""
from app.shared.db import row, rows


def approved_between(db, clinic_id: int, start: str, end: str) -> list[dict]:
    return rows(db.execute(
        "select * from leave_requests where clinic_id = ? and status = 'approved' and start_date <= ? and end_date >= ?",
        (clinic_id, end, start)))


def member_kind(db, member_id: int) -> dict | None:
    return row(db.execute("select kind from members where id = ?", (member_id,)).fetchone())


def member_in(db, member_id: int, clinic_id: int) -> bool:
    return bool(db.execute("select 1 from members where id = ? and clinic_id = ?", (member_id, clinic_id)).fetchone())


def drop_off_day(db, doctor_id: int, day: str) -> None:
    db.execute("delete from schedule_overrides where doctor_id = ? and date = ? and is_off = 1", (doctor_id, day))


def bookings_between(db, member_id: int, start: str, end: str) -> int:
    return db.execute("select count(*) from visits where doctor_id = ? and status = 'booked' and date between ? and ?",
                      (member_id, start, end)).fetchone()[0]


def overlaps(db, member_id: int, start: str, end: str) -> bool:
    return bool(db.execute(
        "select 1 from leave_requests where member_id = ? and status in ('pending', 'approved') and start_date <= ? and end_date >= ?",
        (member_id, end, start)).fetchone())


def add(db, clinic_id: int, member_id: int, start: str, end: str, type_: str, reason: str, status: str,
        decided_by: int | None, decided_at: str | None, created_at: str) -> int:
    return db.execute(
        """insert into leave_requests (clinic_id, member_id, start_date, end_date, type, reason, status, decided_by, decided_at, created_at)
           values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (clinic_id, member_id, start, end, type_, reason, status, decided_by, decided_at, created_at)).lastrowid


def one(db, clinic_id: int, leave_id: int) -> dict | None:
    return row(db.execute(
        """select l.*, m.name, m.kind from leave_requests l join members m on m.id = l.member_id
           where l.id = ? and l.clinic_id = ?""", (leave_id, clinic_id)).fetchone())


def ids(db, where: str, args: list) -> list[int]:
    return [r[0] for r in db.execute(
        f"select l.id from leave_requests l where {where} and l.status != 'cancelled' order by l.start_date desc, l.id desc", args)]


def cancel(db, leave_id: int) -> None:
    db.execute("update leave_requests set status = 'cancelled' where id = ?", (leave_id,))


def decide(db, leave_id: int, status: str, by: int, at: str) -> None:
    db.execute("update leave_requests set status = ?, decided_by = ?, decided_at = ? where id = ?", (status, by, at, leave_id))
