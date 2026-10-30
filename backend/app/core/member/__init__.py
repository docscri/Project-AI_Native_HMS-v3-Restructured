"""Members: doctors and staff of one clinic."""
from app.shared.auth import SCREENS
from app.shared.errors import NotFound


def clinic_doctor(db, me: dict, doctor_id: int) -> dict:
    """Other clinics' or inactive doctors look like 404s."""
    d = db.execute("select * from members where id = ? and clinic_id = ? and kind = 'doctor' and status != 'inactive'",
                   (doctor_id, me["clinic_id"])).fetchone()
    if not d:
        raise NotFound("Doctor not found.")
    return dict(d)


def allowed_screens(screens: list[str], kind: str, is_admin: bool) -> list[str]:
    return [x for x in screens if x in SCREENS and (x != "administration" or is_admin) and (x != "consultation" or kind == "doctor")]
