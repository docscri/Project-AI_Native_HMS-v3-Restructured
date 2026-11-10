"""Signature SQL."""
from app.shared.db import now, row


def add(db, clinic_id: int, member_id: int, path: str) -> int:
    return db.execute("insert into signatures (clinic_id, member_id, path, created_at) values (?, ?, ?, ?)",
                      (clinic_id, member_id, path, now())).lastrowid


def set_current(db, member_id: int, signature_id: int | None) -> None:
    db.execute("update members set signature_id = ? where id = ?", (signature_id, member_id))


def current(db, member_id: int) -> dict | None:
    return row(db.execute("select s.* from signatures s join members m on m.signature_id = s.id where m.id = ?", (member_id,)).fetchone())


def get(db, clinic_id: int, signature_id: int) -> dict | None:
    return row(db.execute("select * from signatures where id = ? and clinic_id = ?", (signature_id, clinic_id)).fetchone())
