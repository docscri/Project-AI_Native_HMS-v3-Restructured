"""Owner signup creates the clinic; finish marks it ready."""
import json

from app.shared.audit import log_event
from app.shared.auth import SCREENS, create_session, hash_password, public_member, validate_password
from app.shared.errors import Conflict, Forbidden
from app.shared.validate import clean_email, clean_phone
from app.core.clinic import clinic_of, public_clinic
from app.modules.operations.account import service as account
from . import repo


def create_owner(db, body) -> dict:
    """Step 1: creator becomes Owner."""
    email = clean_email(body.email)
    validate_password(body.password)
    if account.email_taken(db, email):
        raise Conflict("Email already registered.")
    clinic_id = repo.create_clinic(db)
    mid = repo.create_owner(db, clinic_id, "doctor" if body.is_doctor else "staff", body.name.strip(), email, clean_phone(body.phone),
                            hash_password(body.password), body.speciality if body.is_doctor else None, json.dumps(SCREENS))
    log_event(db, clinic_id, mid, "clinic", clinic_id, "created")
    return {"token": create_session(db, mid)}


def edit_owner(db, me: dict, body) -> dict:
    if not me["is_owner"] or clinic_of(db, me)["onboarded"]:
        raise Forbidden("Change this in your account.")
    email = clean_email(body.email)
    if account.email_taken(db, email, me["id"]):
        raise Conflict("Email already registered.")
    repo.update_owner(db, me["id"], body.name.strip(), email, clean_phone(body.phone), "doctor" if body.is_doctor else "staff",
                      (me.get("speciality") or "General medicine") if body.is_doctor else None)
    if body.password:
        validate_password(body.password)
        repo.set_password(db, me["id"], hash_password(body.password))
    log_event(db, me["clinic_id"], me["id"], "member", me["id"], "updated")
    return public_member(repo.member(db, me["id"]))


def finish(db, me: dict) -> dict:
    repo.finish(db, me["clinic_id"])
    return public_clinic(clinic_of(db, me))
