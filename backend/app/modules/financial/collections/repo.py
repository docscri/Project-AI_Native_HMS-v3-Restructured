"""Collections SQL."""
from app.shared.db import rows


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
