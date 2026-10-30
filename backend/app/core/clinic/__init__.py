"""The clinic: its settings as stored and as the app shows them."""
import json

from app.shared.db import row

from .schedule import limits, parse_sessions


def clinic_of(db, me) -> dict:
    return row(db.execute("select * from clinics where id = ?", (me["clinic_id"],)).fetchone())


def public_clinic(c: dict) -> dict:
    c = dict(c)
    c["days"] = json.loads(c["days"])
    c["onboarded"] = bool(c["onboarded"])
    c["sessions"] = parse_sessions(c.get("sessions"), c["start"], c["end"])
    c["derived"] = limits(c["sessions"][0]["start"], c["sessions"][0]["end"], c["limit_by"], c["limit_value"]) if c["sessions"] else None
    return c
