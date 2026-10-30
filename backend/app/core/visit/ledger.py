"""Payments and refunds: one row each, never changed."""
from app.shared.db import now


def ledger(db, me, visit_id: int, kind: str, amount: int, method=None, receipt=None, reason=None, at=None) -> None:
    """Append-only."""
    db.execute("insert into payments (clinic_id, visit_id, kind, amount, method, receipt_no, reason, at, by_member) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (me["clinic_id"], visit_id, kind, amount, method, receipt, reason, at or now(), me["id"]))


def balance(db, visit_id: int) -> int:
    """Paid minus refunded."""
    return db.execute("select coalesce(sum(case when kind = 'payment' then amount else -amount end), 0) from payments where visit_id = ?",
                      (visit_id,)).fetchone()[0]
