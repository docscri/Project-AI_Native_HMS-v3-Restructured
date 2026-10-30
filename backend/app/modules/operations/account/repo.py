"""Account SQL."""
from app.shared.db import row


def member_by_email(db, email: str, active_only: bool = False) -> dict | None:
    sql = "select * from members where lower(email) = lower(?)" + (" and status = 'active'" if active_only else "")
    return row(db.execute(sql, (email,)).fetchone())


def member(db, member_id: int) -> dict | None:
    return row(db.execute("select * from members where id = ?", (member_id,)).fetchone())


def email_taken(db, email: str, except_id: int | None = None) -> bool:
    if except_id is None:
        return bool(db.execute("select 1 from members where lower(email) = lower(?)", (email,)).fetchone())
    return bool(db.execute("select 1 from members where lower(email) = lower(?) and id != ?", (email, except_id)).fetchone())


def set_failed_logins(db, member_id: int, fails: int, locked_until) -> None:
    db.execute("update members set failed_logins = ?, locked_until = ? where id = ?", (fails, locked_until, member_id))


def clear_failed_logins(db, member_id: int) -> None:
    db.execute("update members set failed_logins = 0, locked_until = null where id = ?", (member_id,))


def set_password(db, member_id: int, password_hash: str) -> None:
    db.execute("update members set password_hash = ? where id = ?", (password_hash, member_id))


def reset_password(db, member_id: int, password_hash: str) -> None:
    db.execute("update members set password_hash = ?, failed_logins = 0, locked_until = null where id = ?",
               (password_hash, member_id))


def update_profile(db, member_id: int, name, email, phone, speciality, designation) -> None:
    db.execute("update members set name = ?, email = ?, phone = ?, speciality = ?, designation = ? where id = ?",
               (name, email, phone, speciality, designation, member_id))


def delete_session(db, token_hash: str) -> None:
    db.execute("delete from sessions where token_hash = ?", (token_hash,))


def replace_reset(db, member_id: int, token_hash: str, expires_at) -> None:
    db.execute("delete from password_resets where member_id = ?", (member_id,))
    db.execute("insert into password_resets (token_hash, member_id, expires_at) values (?, ?, ?)",
               (token_hash, member_id, expires_at))


def reset(db, token_hash: str) -> dict | None:
    return row(db.execute("select * from password_resets where token_hash = ?", (token_hash,)).fetchone())


def live_reset_exists(db, token_hash: str, member_id: int, at) -> bool:
    return bool(db.execute("select 1 from password_resets where token_hash = ? and member_id = ? and used_at is null and expires_at > ?",
                           (token_hash, member_id, at)).fetchone())


def use_reset(db, token_hash: str, at) -> None:
    db.execute("update password_resets set used_at = ? where token_hash = ?", (at, token_hash))
