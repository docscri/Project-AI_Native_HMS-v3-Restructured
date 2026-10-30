"""Onboarding SQL."""
from app.shared.db import row


def create_clinic(db) -> int:
    return db.execute("insert into clinics default values").lastrowid


def create_owner(db, clinic_id: int, kind: str, name, email, phone, password_hash, speciality, screens: str) -> int:
    return db.execute(
        """insert into members (clinic_id, kind, is_owner, is_admin, name, email, phone, password_hash,
           speciality, screens, status) values (?, ?, 1, 1, ?, ?, ?, ?, ?, ?, 'active')""",
        (clinic_id, kind, name, email, phone, password_hash, speciality, screens),
    ).lastrowid


def update_owner(db, member_id: int, name, email, phone, kind, speciality) -> None:
    db.execute("update members set name = ?, email = ?, phone = ?, kind = ?, speciality = ? where id = ?",
               (name, email, phone, kind, speciality, member_id))


def set_password(db, member_id: int, password_hash: str) -> None:
    db.execute("update members set password_hash = ? where id = ?", (password_hash, member_id))


def member(db, member_id: int) -> dict | None:
    return row(db.execute("select * from members where id = ?", (member_id,)).fetchone())


def finish(db, clinic_id: int) -> None:
    db.execute("update clinics set onboarded = 1 where id = ?", (clinic_id,))
