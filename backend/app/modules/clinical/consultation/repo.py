"""Consultation SQL."""
from app.shared.db import row


def busy(db, doctor_id: int, day: str, other_than: int = 0) -> bool:
    """A patient is already with this doctor that day."""
    return bool(db.execute("select 1 from visits where doctor_id = ? and date = ? and status = 'with_doctor' and id != ?",
                           (doctor_id, day, other_than)).fetchone())


def next_waiting(db, doctor_id: int, day: str) -> dict | None:
    return row(db.execute(
        "select * from visits where doctor_id = ? and date = ? and status = 'waiting' order by session_start, queue_order, token limit 1",
        (doctor_id, day)).fetchone())


def save_text(db, visit_id: int, text: str, rev: int) -> bool:
    """False when another save got there first."""
    return db.execute("update visits set dictation = ?, dictation_rev = dictation_rev + 1 where id = ? and dictation_rev = ?",
                      (text, visit_id, rev)).rowcount == 1


def text_rev(db, visit_id: int) -> int:
    return db.execute("select dictation_rev from visits where id = ?", (visit_id,)).fetchone()[0]


def set_text(db, visit_id: int, text: str) -> None:
    db.execute("update visits set dictation = ?, dictation_rev = dictation_rev + 1 where id = ?", (text, visit_id))
