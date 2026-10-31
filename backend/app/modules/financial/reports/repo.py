"""Reports SQL: collections and day close."""
from app.shared.db import row, rows

CLOSES = "select c.*, m.name as closed_by_name from day_close c left join members m on m.id = c.closed_by where c.clinic_id = ?"


def money_rows(db, clinic_id: int, kind: str, start: str, end: str, doctor_id: int | None) -> list[dict]:
    doc = " and v.doctor_id = ?" if doctor_id else ""
    return rows(db.execute(
        f"""select pay.id as pay_id, v.id, v.date, pay.at, pay.at as paid_at, pay.at as refunded_at, pay.method as payment_method,
              pay.amount, pay.amount as amount_paid, pay.amount as refund_amount, pay.receipt_no, pay.reason as refund_reason,
              case when pay.receipt_no = v.receipt_no then v.discount else 0 end as discount, v.fee, v.doctor_id,
              p.name as patient_name, p.uhid, m.name as doctor_name
            from payments pay join visits v on v.id = pay.visit_id join patients p on p.id = v.patient_id join members m on m.id = v.doctor_id
            where pay.clinic_id = ? and pay.kind = ? and substr(pay.at, 1, 10) between ? and ?{doc} order by pay.at, pay.id""",
        (clinic_id, kind, start, end, *((doctor_id,) if doctor_id else ()))))


def visits_between(db, clinic_id: int, start: str, end: str, doctor_id: int | None) -> list[dict]:
    doc = " and v.doctor_id = ?" if doctor_id else ""
    return rows(db.execute(
        f"""select v.doctor_id, v.status, v.is_walk_in from visits v where v.clinic_id = ? and v.date between ? and ?{doc}""",
        (clinic_id, start, end, *((doctor_id,) if doctor_id else ()))))


def doctors(db, clinic_id: int) -> list[dict]:
    return rows(db.execute("select id, name, speciality from members where clinic_id = ? and kind = 'doctor' order by name", (clinic_id,)))


def close_on(db, clinic_id: int, day: str) -> dict | None:
    return row(db.execute(CLOSES + " and c.date = ?", (clinic_id, day)).fetchone())


def recent_closes(db, clinic_id: int) -> list[dict]:
    return rows(db.execute(CLOSES + " order by c.date desc limit 14", (clinic_id,)))


def save_close(db, clinic_id: int, day: str, system_cash: int, counted_cash: int, note: str, by: int, at: str) -> None:
    db.execute(
        """insert into day_close (clinic_id, date, system_cash, counted_cash, note, closed_by, closed_at) values (?, ?, ?, ?, ?, ?, ?)
           on conflict (clinic_id, date) do update set system_cash = excluded.system_cash, counted_cash = excluded.counted_cash,
             note = excluded.note, closed_by = excluded.closed_by, closed_at = excluded.closed_at""",
        (clinic_id, day, system_cash, counted_cash, note, by, at))
