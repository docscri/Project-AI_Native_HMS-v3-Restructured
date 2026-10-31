"""Fees, discounts, receipt numbers and refunds."""
import html

from app.shared import printing as printpage
from app.shared.audit import log_event
from app.shared.db import now
from app.shared.errors import Conflict, Invalid
from app.core.clinic import clinic_of
from app.core.visit import balance, get_visit, ledger, visit_out
from app.modules.financial.payments import repo
from app.modules.financial.payments.schema import Payment, Refund


def money(n) -> str:
    return f"₹{(n or 0):,}"


def charge(db, me, fee: int, body: Payment) -> dict:
    if body.discount > fee:
        raise Invalid("Discount cannot be more than the fee.")
    amount = fee - body.discount
    if amount > 0 and not body.payment_method:
        raise Invalid("Choose how the patient paid.")
    db.lock(f"receipt:{me['clinic_id']}")
    receipt = repo.take_receipt_no(db, me["clinic_id"])
    ts = now()
    return {"payment_method": body.payment_method if amount > 0 else None, "discount": body.discount,
            "discount_reason": body.discount_reason.strip() or None, "amount_paid": amount, "receipt_no": receipt,
            "paid_at": ts, "arrived_at": ts}


def refund(db, me, visit_id: int, body: Refund) -> dict:
    db.lock(f"visit:{visit_id}")   # parallel refunds must see each other's
    v = get_visit(db, me, visit_id)
    left = balance(db, visit_id)
    amount = body.amount or left
    if not v["paid_at"] or left <= 0:
        raise Conflict("Nothing left to refund on this visit.")
    if amount > left:
        raise Invalid(f"You can refund at most ₹{left}.")
    if not body.reason.strip():
        raise Invalid("Give a reason for the refund.")
    repo.set_refund(db, visit_id, (v["refund_amount"] or 0) + amount, body.reason.strip())
    ledger(db, me, visit_id, "refund", amount, reason=body.reason.strip())
    log_event(db, me["clinic_id"], me["id"], "visit", visit_id, "refunded", {"amount": amount, "reason": body.reason.strip()})
    return visit_out(db, me, visit_id)


def paid_visit(db, me, visit_id: int) -> dict | None:
    v = repo.visit(db, me["clinic_id"], visit_id)
    return v if v and v["paid_at"] else None


def receipt_page(db, me, v: dict, auto: bool):
    c = clinic_of(db, me)
    p = repo.patient(db, v["patient_id"])
    d = repo.doctor(db, v["doctor_id"])
    e = html.escape
    lines = [("Consultation", money(v["fee"]))]
    if v["discount"]:
        lines.append((f"{'Waived' if v['discount'] == v['fee'] else 'Discount'}{' · ' + e(v['discount_reason']) if v['discount_reason'] else ''}", "−" + money(v["discount"])))
    if v["refund_amount"]:
        lines.append((f"Refunded{' · ' + e(v['refund_reason']) if v['refund_reason'] else ''}", "−" + money(v["refund_amount"])))
    paid = balance(db, v["id"])
    method = {"cash": "Cash", "upi": "UPI", "card": "Card"}.get(v["payment_method"] or "", "Waived")
    body = f"""<header><div><h1>{e(c['name'])}</h1><small>{e(' · '.join(x for x in [c['address'], c['phone']] if x))}</small></div>
<div class="r"><b class="lime">Receipt #{v['receipt_no']}</b><small>{printpage.stamp(v['paid_at'])}</small></div></header>
<h2>Patient</h2><table><tr><td><b>{e(p['name'])}</b></td><td class="r">{e(p['uhid'])}</td></tr><tr><td>{e(d['name'])}</td><td class="r">{e(d['speciality'] or '')}</td></tr></table>
<h2>Charges</h2><table>{"".join(f"<tr><td>{a}</td><td class='r'>{b}</td></tr>" for a, b in lines)}</table>
<div class="total"><small>Paid · {method}</small><b>{money(paid)}</b></div>
<footer><div class="s">Thank you.</div></footer>"""
    return printpage.page(f"Receipt {v['receipt_no']}", body, auto=auto, size="A5", narrow=True)
