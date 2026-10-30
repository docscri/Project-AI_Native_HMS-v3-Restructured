"""Attendance SQL."""
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
