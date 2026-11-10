"""Administration SQL."""
from app.shared.states import MEMBER
from app.shared.db import row, rows


def update_details(db, clinic_id: int, name, phone, address, prefix) -> None:
    db.execute("update clinics set name = ?, phone = ?, address = ?, uhid_prefix = ? where id = ?",
               (name, phone, address, prefix, clinic_id))


def update_rules(db, clinic_id: int, fee, days: str, start, end, sessions: str, limit_by, limit_value, token_timing) -> None:
    db.execute(
        """update clinics set fee = ?, days = ?, start = ?, "end" = ?, sessions = ?, limit_by = ?, limit_value = ?, token_timing = ?
           where id = ?""",
        (fee, days, start, end, sessions, limit_by, limit_value, token_timing, clinic_id),
    )


def members(db, clinic_id: int) -> list[dict]:
    return rows(db.execute("select * from members where clinic_id = ? order by is_owner desc, kind, name", (clinic_id,)))


def member(db, member_id: int) -> dict | None:
    return row(db.execute("select * from members where id = ?", (member_id,)).fetchone())


def clinic_member(db, clinic_id: int, member_id: int) -> dict | None:
    return row(db.execute("select * from members where id = ? and clinic_id = ?", (member_id, clinic_id)).fetchone())


def active_clinic_member(db, clinic_id: int, member_id: int) -> dict | None:
    return row(db.execute("select * from members where id = ? and clinic_id = ? and status = 'active'", (member_id, clinic_id)).fetchone())


def insert_member(db, clinic_id: int, kind, is_admin: int, name, email, phone, code, expires_at, speciality, designation,
                  fee_override, screens: str) -> int:
    return db.execute(
        """insert into members (clinic_id, kind, is_admin, name, email, phone, invite_code, invite_expires_at, speciality,
           designation, fee_override, screens) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (clinic_id, kind, is_admin, name, email, phone, code, expires_at, speciality, designation, fee_override, screens),
    ).lastrowid


def set_invite(db, member_id: int, code: str, expires_at) -> None:
    db.execute("update members set invite_code = ?, invite_expires_at = ? where id = ?", (code, expires_at, member_id))


def update_member(db, member_id: int, changes: dict) -> None:
    db.execute(f"update members set {', '.join(f'{k} = ?' for k in changes)} where id = ?", (*changes.values(), member_id))


def doctor_has_visits(db, member_id: int) -> bool:
    return bool(db.execute("select 1 from visits where doctor_id = ?", (member_id,)).fetchone())


# Every record that points at a member and must outlive them (sessions and reset links are deleted with the member).
# A member with any of these is deactivated instead of deleted.
HISTORY = [("visits", "doctor_id"), ("notes", "doctor_id"), ("notes", "signed_by"), ("note_addenda", "signed_by"),
           ("waitlist", "doctor_id"), ("attendance", "member_id"), ("leave_requests", "member_id")]


def has_history(db, member_id: int) -> bool:
    sql = " union ".join(f"select 1 from {t} where {c} = ?" for t, c in HISTORY)
    return bool(db.execute(sql, (member_id,) * len(HISTORY)).fetchone())


def deactivate(db, member_id: int, frm: str) -> None:
    if frm != "inactive":
        MEMBER.move(db, member_id, frm, "inactive")


def clear_own_trail(db, member_id: int) -> None:
    db.execute("delete from schedule_overrides where doctor_id = ?", (member_id,))
    db.execute("delete from events where actor_id = ? and entity = 'member' and entity_id = ?", (member_id, member_id))


def delete_member(db, member_id: int) -> None:
    db.execute("delete from members where id = ?", (member_id,))


def invite_view(db, code: str) -> dict | None:
    return row(db.execute(
        """select m.name, m.email, m.invite_expires_at, c.name as clinic from members m join clinics c on c.id = m.clinic_id
           where invite_code = ? and m.status = 'invited'""", (code,)).fetchone())


def invited_member(db, code: str) -> dict | None:
    return row(db.execute("select * from members where invite_code = ? and status = 'invited'", (code,)).fetchone())


def accept_invite(db, member_id: int, code: str, password_hash: str) -> bool:
    """Single use: only the request that still finds the code unused gets True."""
    return db.execute("""update members set password_hash = ?, status = 'active', invite_code = null, invite_expires_at = null
                         where id = ? and invite_code = ? and status = 'invited'""", (password_hash, member_id, code)).rowcount == 1
