"""Collections totals by day and doctor."""
from datetime import date as Date, timedelta

from . import repo


def money_rows(db, me, kind: str, start: str, end: str, doctor_id: int | None) -> list[dict]:
    return repo.money_rows(db, me["clinic_id"], kind, start, end, doctor_id)


def totals(paid: list[dict], refunds: list[dict]) -> dict:
    by = {k: sum(v["amount"] for v in paid if v["payment_method"] == k) for k in ("cash", "upi", "card")}
    refunded, collected = sum(v["amount"] for v in refunds), sum(v["amount"] for v in paid)
    return {"by_method": by, "collected": collected, "refunded": refunded, "net": collected - refunded,
            "discounts": sum(v["discount"] or 0 for v in paid), "waived": sum(1 for v in paid if not v["amount"]),
            "visits": len(paid)}


def collections(db, me, start: str, end: str | None = None, doctor_id: int | None = None) -> dict:
    end = end or start
    paid = money_rows(db, me, "payment", start, end, doctor_id)
    refunds = money_rows(db, me, "refund", start, end, doctor_id)
    days = []
    d = Date.fromisoformat(start)
    while d <= Date.fromisoformat(end) and len(days) < 400:
        k = d.isoformat()
        t = totals([v for v in paid if v["at"][:10] == k], [v for v in refunds if v["at"][:10] == k])
        if t["visits"] or t["refunded"]:
            days.append({"date": k, **t})
        d += timedelta(days=1)
    # Patients by visit date, money by payment date.
    vis = repo.visits_between(db, me["clinic_id"], start, end, doctor_id)
    by_doctor = []
    for d in repo.doctors(db, me["clinic_id"]):
        if doctor_id and d["id"] != doctor_id:
            continue
        mine = [v for v in vis if v["doctor_id"] == d["id"]]
        t = totals([v for v in paid if v["doctor_id"] == d["id"]], [v for v in refunds if v["doctor_id"] == d["id"]])
        row_ = {"id": d["id"], "name": d["name"], "speciality": d["speciality"],
                "seen": sum(v["status"] == "done" for v in mine), "walk_ins": sum(bool(v["is_walk_in"]) and v["status"] != "cancelled" for v in mine),
                "no_shows": sum(v["status"] == "no_show" for v in mine), "collected": t["collected"], "refunded": t["refunded"], "net": t["net"]}
        if any(row_[k] for k in ("seen", "walk_ins", "no_shows", "collected", "refunded")) or doctor_id:
            by_doctor.append(row_)
    return {"start": start, "end": end, **totals(paid, refunds), "days": days, "payments": paid, "refunds": refunds,
            "by_doctor": by_doctor, "seen": sum(r["seen"] for r in by_doctor)}
