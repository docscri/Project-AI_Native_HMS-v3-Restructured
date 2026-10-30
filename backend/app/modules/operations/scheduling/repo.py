"""Schedule SQL."""
import json

from app.shared.db import now, row


def doctor(db, clinic_id: int, doctor_id: int) -> dict | None:
    return row(db.execute("select * from members where id = ? and clinic_id = ? and kind = 'doctor'",
                          (doctor_id, clinic_id)).fetchone())


def has_override(db, doctor_id: int, day: str) -> bool:
    return bool(db.execute("select 1 from schedule_overrides where doctor_id = ? and date = ?", (doctor_id, day)).fetchone())


def upsert_override(db, clinic_id, doctor_id, day, is_off, sessions, limit_by, limit_value) -> None:
    db.execute(
        """insert into schedule_overrides (clinic_id, doctor_id, date, is_off, start, "end", sessions, limit_by, limit_value)
           values (?, ?, ?, ?, ?, ?, ?, ?, ?)
           on conflict (doctor_id, date) do update set is_off = excluded.is_off, start = excluded.start,
             "end" = excluded."end", sessions = excluded.sessions, limit_by = excluded.limit_by, limit_value = excluded.limit_value""",
        (clinic_id, doctor_id, day, int(is_off), sessions and sessions[0]["start"], sessions and sessions[-1]["end"],
         json.dumps(sessions) if sessions else None, limit_by, limit_value),
    )


def delete_override(db, doctor_id: int, day: str) -> None:
    db.execute("delete from schedule_overrides where doctor_id = ? and date = ?", (doctor_id, day))


def delete_clinic_override(db, clinic_id: int, doctor_id: int, day: str) -> None:
    db.execute("delete from schedule_overrides where doctor_id = ? and date = ? and clinic_id = ?",
               (doctor_id, day, clinic_id))


def bookings_on(db, doctor_ids: list[int], days: list[str]) -> int:
    if not doctor_ids or not days:
        return 0
    return db.execute(
        f"""select count(*) from visits where status = 'booked' and doctor_id in ({','.join('?' * len(doctor_ids))})
            and date in ({','.join('?' * len(days))})""", (*doctor_ids, *days)).fetchone()[0]


def active_doctor_ids(db, clinic_id: int) -> list[int]:
    return [r[0] for r in db.execute("select id from members where clinic_id = ? and kind = 'doctor' and status != 'inactive'",
                                     (clinic_id,))]


def add_approved_leave(db, clinic_id, member_id, start_date, end_date, decided_by) -> None:
    db.execute("""insert into leave_requests (clinic_id, member_id, start_date, end_date, type, status, decided_by, decided_at, created_at)
                  values (?, ?, ?, ?, 'other', 'approved', ?, ?, ?)""",
               (clinic_id, member_id, start_date, end_date, decided_by, now(), now()))


def cancel_approved_leave(db, member_id, start_date, end_date) -> None:
    db.execute("update leave_requests set status = 'cancelled' where member_id = ? and status = 'approved' and start_date >= ? and end_date <= ?",
               (member_id, start_date, end_date))
