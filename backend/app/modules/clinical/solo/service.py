"""Solo doctors: sign-up, the places they see patients, and visits that start at once (no queue, token or payment)."""
import json
from datetime import date

from app.core import departments
from app.core.clinic import clinic_of
from app.core.patient import get_patient
from app.modules.operations.account import repo as account_repo
from app.shared.audit import log_event
from app.shared.auth import create_session, hash_password, validate_password
from app.shared.db import now
from app.shared.errors import Conflict, Forbidden, Invalid, NotFound
from app.shared.validate import clean_email, clean_phone

from . import repo

SOLO_SCREENS = ["patients", "consultation"]


def require_solo(db, me: dict) -> None:
    if not clinic_of(db, me)["solo"]:
        raise Forbidden("Only for solo doctors.")


def sign_up(db, body) -> dict:
    email = clean_email(body.email)
    validate_password(body.password)
    if account_repo.email_taken(db, email):
        raise Conflict("Email already registered.")
    name = " ".join(body.name.split())
    clinic_id = repo.create_solo_clinic(db, name)
    mid = account_repo.create_owner(db, clinic_id, "doctor", name, email, clean_phone(body.phone), hash_password(body.password),
                                    departments.chosen(body.speciality), json.dumps(SOLO_SCREENS))
    log_event(db, clinic_id, mid, "clinic", clinic_id, "created", {"solo": True})
    return {"token": create_session(db, mid)}


def locations(db, me: dict) -> list[dict]:
    require_solo(db, me)
    return repo.locations(db, me["clinic_id"])


def add_location(db, me: dict, name: str) -> dict:
    require_solo(db, me)
    name = " ".join(name.split())
    if not name:
        raise Invalid("Name the place.")
    if any(l["name"].lower() == name.lower() for l in repo.locations(db, me["clinic_id"])):
        raise Conflict("That place is already in your list.")
    lid = repo.add_location(db, me["clinic_id"], name)
    log_event(db, me["clinic_id"], me["id"], "location", lid, "added", {"name": name})
    return {"id": lid, "name": name}


def remove_location(db, me: dict, location_id: int) -> dict:
    """Kept on past visits; only taken off the list."""
    require_solo(db, me)
    if not repo.location(db, me["clinic_id"], location_id):
        raise NotFound("Place not found.")
    repo.archive_location(db, location_id)
    log_event(db, me["clinic_id"], me["id"], "location", location_id, "removed")
    return {"ok": True}


def quick_visit(db, me: dict, patient_id: int, location_id: int | None) -> int:
    """Starts a visit at once; returns its id. An unfinished visit today for the same patient is reopened instead."""
    require_solo(db, me)
    get_patient(db, me, patient_id)
    if location_id is not None:
        loc = repo.location(db, me["clinic_id"], location_id)
        if not loc or loc["archived"]:
            raise Invalid("Choose a place from your list.")
    today = date.today().isoformat()
    db.lock(f"patient:{patient_id}")
    if open_ := repo.open_visit(db, patient_id, me["id"], today):
        return open_["id"]
    vid = repo.insert_quick_visit(db, me["clinic_id"], patient_id, me["id"], today, location_id, now())
    log_event(db, me["clinic_id"], me["id"], "visit", vid, "started", {"solo": True, "location_id": location_id})
    return vid
