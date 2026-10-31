"""Team: attendance and leave SQL."""
from app.shared.db import row, rows


def members_of(db, clinic_id: int) -> list[dict]:
    return rows(db.execute(
        "select id, kind, name, designation, speciality, work_days, work_start, work_end, is_owner, joined_on, created_at from members "
        "where clinic_id = ? and status = 'active' order by kind, name", (clinic_id,)))


def member(db, member_id: int) -> dict | None:
    return row(db.execute("select * from members where id = ?", (member_id,)).fetchone())


def member_in(db, member_id: int, clinic_id: int) -> bool:
    return bool(db.execute("select 1 from members where id = ? and clinic_id = ?", (member_id, clinic_id)).fetchone())


def attendance_between(db, clinic_id: int, start: str, end: str) -> list[dict]:
    return rows(db.execute("select * from attendance where clinic_id = ? and date between ? and ?", (clinic_id, start, end)))


def consulted_between(db, clinic_id: int, start: str, end: str) -> list[dict]:
    return rows(db.execute(
        """select doctor_id, date, min(started_at) as first, max(completed_at) as last from visits
           where clinic_id = ? and date between ? and ? and started_at is not null group by doctor_id, date""", (clinic_id, start, end)))


def one(db, member_id: int, day: str) -> dict | None:
    return row(db.execute("select * from attendance where member_id = ? and date = ?", (member_id, day)).fetchone())


def checked_in(db, member_id: int, day: str) -> bool:
    return bool(db.execute("select 1 from attendance where member_id = ? and date = ? and check_in is not null", (member_id, day)).fetchone())


def add_check_in(db, clinic_id: int, member_id: int, day: str, status: str, ts: str) -> None:
    db.execute("insert into attendance (clinic_id, member_id, date, status, check_in) values (?, ?, ?, ?, ?)",
               (clinic_id, member_id, day, status, ts))


def set_check_out(db, member_id: int, day: str, ts: str) -> None:
    db.execute("update attendance set check_out = ? where member_id = ? and date = ?", (ts, member_id, day))


def clear(db, member_id: int, day: str) -> None:
    db.execute("delete from attendance where member_id = ? and date = ?", (member_id, day))


def upsert(db, clinic_id: int, member_id: int, day: str, status: str, check_in: str | None, note: str, edited_by: int) -> None:
    db.execute(
        """insert into attendance (clinic_id, member_id, date, status, check_in, note, edited_by) values (?, ?, ?, ?, ?, ?, ?)
           on conflict (member_id, date) do update set status = excluded.status,
             check_in = coalesce(excluded.check_in, attendance.check_in), note = excluded.note, edited_by = excluded.edited_by""",
        (clinic_id, member_id, day, status, check_in, note, edited_by))


def approved_between(db, clinic_id: int, start: str, end: str) -> list[dict]:
    return rows(db.execute(
        "select * from leave_requests where clinic_id = ? and status = 'approved' and start_date <= ? and end_date >= ?",
        (clinic_id, end, start)))


def member_kind(db, member_id: int) -> dict | None:
    return row(db.execute("select kind from members where id = ?", (member_id,)).fetchone())


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


def leave_one(db, clinic_id: int, leave_id: int) -> dict | None:
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
