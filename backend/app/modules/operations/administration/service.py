"""Clinic settings, members and invites."""
import json

from app.shared import mail as mailer
from app.shared.audit import log_event
from app.shared.auth import (has_admin, INVITE_DAYS, RESET_HOURS, SCREENS, create_session, end_sessions, hash_password, later, new_code,
                             public_member, validate_password)
from app.shared.db import now
from app.shared.errors import BadGateway, Conflict, Gone, Invalid, NotFound
from app.shared.states import MEMBER
from app.shared.validate import clean_email, clean_phone, valid_day
from app.core import departments
from app.core.clinic import clinic_of, public_clinic
from app.core.clinic.schedule import validate_sessions
from app.core.member import allowed_screens
from app.modules.operations.account import service as account
from . import repo


def get_clinic(db, me: dict) -> dict:
    return public_clinic(clinic_of(db, me))


def update_details(db, me: dict, body) -> dict:
    prefix = "".join(w[0] for w in body.name.split()[:3]).upper() or "CL"
    c = clinic_of(db, me)
    if c["next_uhid"] > 1:
        prefix = c["uhid_prefix"]  # keep UHIDs stable once patients exist
    repo.update_details(db, me["clinic_id"], body.name, body.phone, body.address, prefix)
    log_event(db, me["clinic_id"], me["id"], "clinic", me["clinic_id"], "details_updated", body.model_dump())
    return public_clinic(clinic_of(db, me))


def update_rules(db, me: dict, body) -> dict:
    """Clinic-wide defaults for every doctor."""
    days = sorted({d for d in body.days if 0 <= d <= 6})
    if not days:
        raise Invalid("Pick at least one working day.")
    raw = [s.model_dump() for s in body.sessions] or ([{"start": body.start, "end": body.end}] if body.start and body.end else [])
    sessions = validate_sessions(raw)
    if body.limit_by == "minutes" and body.limit_value > 240:
        raise Invalid("Minutes per patient looks too high.")
    repo.update_rules(db, me["clinic_id"], body.fee, json.dumps(days), sessions[0]["start"], sessions[-1]["end"], json.dumps(sessions),
                      body.limit_by, body.limit_value, body.token_timing)
    log_event(db, me["clinic_id"], me["id"], "clinic", me["clinic_id"], "rules_updated", body.model_dump())
    return public_clinic(clinic_of(db, me))


def list_members(db, me: dict) -> list[dict]:
    ms = [public_member(m) for m in repo.members(db, me["clinic_id"])]
    if has_admin(me):
        return ms
    basic = ("id", "name", "kind", "speciality", "designation", "status", "is_owner", "is_admin")
    return [{k: m.get(k) for k in basic} for m in ms]


def add_member(db, me: dict, body) -> dict:
    email = clean_email(body.email)
    if account.email_taken(db, email):
        raise Conflict("Email already a member.")
    if body.fee_override is not None and body.fee_override < 0:
        raise Invalid("Fee cannot be negative.")
    code = new_code()
    mid = repo.insert_member(
        db, me["clinic_id"], body.kind, int(body.is_admin), body.name.strip(), email, clean_phone(body.phone), code, later(days=INVITE_DAYS),
        departments.chosen(body.speciality) if body.kind == "doctor" else None, body.designation if body.kind == "staff" else None,
        body.fee_override if body.kind == "doctor" else None, json.dumps(allowed_screens(body.screens, body.kind, body.is_admin)))
    log_event(db, me["clinic_id"], me["id"], "member", mid, "invited", {"email": email})
    send_invite(db, me, mid, code)
    return public_member(repo.member(db, mid)) | {"invite_code": code}


def send_invite(db, me: dict, member_id: int, code: str) -> bool:
    m = repo.member(db, member_id)
    clinic = clinic_of(db, me)
    link = f"{mailer.app_url()}/#/invite/{code}"
    return mailer.send(m["email"], f"Join {clinic['name']} on Dictate",
                f"Hello {m['name']},\n\n{me['name']} has invited you to {clinic['name']}.\n"
                f"Open this link within {INVITE_DAYS} days to set your password:\n{link}",
                mailer.branded(clinic["name"], f"Join {clinic['name']}",
                               f"Hello {m['name']}, {me['name']} has invited you to the clinic's team on Dictate. Set your password to get started.",
                               "Accept invitation", link, f"The link works for {INVITE_DAYS} days."))


def renew_invite(db, me: dict, member_id: int) -> dict:
    """Old invite link stops working."""
    m = repo.clinic_member(db, me["clinic_id"], member_id)
    if not m or m["status"] != "invited":
        raise Conflict("This person has already joined.")
    code = new_code()
    repo.set_invite(db, member_id, code, later(days=INVITE_DAYS))
    return {"invite_code": code, "email_enabled": mailer.enabled()}


def email_invite(db, me: dict, member_id: int) -> dict:
    m = repo.clinic_member(db, me["clinic_id"], member_id)
    if not m or m["status"] != "invited" or not m["invite_code"]:
        raise Conflict("This person has already joined.")
    if not mailer.enabled():
        raise Conflict("Email isn't set up.")
    if not send_invite(db, me, member_id, m["invite_code"]):
        raise BadGateway("Email couldn't be sent. Copy the link.")
    return {"email": m["email"]}


def admin_reset_link(db, me: dict, member_id: int) -> dict:
    """Admin-shared reset link for when email is not set up."""
    m = repo.clinic_member(db, me["clinic_id"], member_id)
    if not m or m["status"] != "active":
        raise Conflict("Member isn't active.")
    log_event(db, me["clinic_id"], me["id"], "member", member_id, "reset_link_created")
    return {"code": account.make_reset(db, member_id), "email_enabled": mailer.enabled()}


def email_reset_link(db, me: dict, member_id: int, code: str) -> dict:
    m = repo.active_clinic_member(db, me["clinic_id"], member_id)
    if not (m and account.reset_is_live(db, code, member_id)):
        raise Conflict("Link expired. Make a new one.")
    if not mailer.enabled():
        raise Conflict("Email isn't set up.")
    link = f"{mailer.app_url()}/#/reset/{code}"
    if not mailer.send(m["email"], "Reset your Dictate password",
                f"Hello {m['name']},\n\nOpen this link within {RESET_HOURS} hours to set a new password:\n{link}",
                mailer.branded(clinic_of(db, me)["name"], "Reset your password", f"Hello {m['name']}, tap the button to set a new password.",
                               "Set new password", link, f"The link works for {RESET_HOURS} hours.")):
        raise BadGateway("Email couldn't be sent. Copy the link.")
    log_event(db, me["clinic_id"], me["id"], "member", member_id, "reset_link_emailed")
    return {"email": m["email"]}


def update_member(db, me: dict, member_id: int, body) -> dict:
    m = repo.clinic_member(db, me["clinic_id"], member_id)
    if not m:
        raise NotFound("Member not found.")
    if m["is_owner"] and body.status == "inactive":
        raise Conflict("The owner cannot be deactivated.")
    if body.email is not None:
        body.email = clean_email(body.email)
    if body.phone is not None:
        body.phone = clean_phone(body.phone)
    if body.fee_override is not None and body.fee_override < 0:
        raise Invalid("Fee cannot be negative.")
    if body.email and account.email_taken(db, body.email, member_id):
        raise Conflict("Someone else already uses this email.")
    if body.kind and body.kind != m["kind"] and m["kind"] == "doctor" and repo.doctor_has_visits(db, member_id):
        raise Conflict("Doctor has visits. Can't change.")
    changes = body.model_dump(exclude_none=True, exclude={"clear_fee"})
    if changes.get("kind", m["kind"]) == "doctor" and ("speciality" in changes or changes.get("kind") == "doctor"):
        changes["speciality"] = departments.chosen(changes.get("speciality"), m["speciality"])   # the department fixes the note template
    if changes.get("joined_on"):
        changes["joined_on"] = valid_day(changes["joined_on"])
    elif "joined_on" in changes:
        changes["joined_on"] = None
    if not m["is_owner"] and ("screens" in changes or "is_admin" in changes or "kind" in changes):
        cur = json.loads(m["screens"]) if "screens" not in changes else changes["screens"]
        changes["screens"] = json.dumps(allowed_screens(cur, changes.get("kind", m["kind"]), changes.get("is_admin", bool(m["is_admin"]))))
    elif "screens" in changes:
        changes["screens"] = json.dumps([s for s in changes["screens"] if s in SCREENS])
    if "work_days" in changes:
        changes["work_days"] = json.dumps(sorted({d for d in changes["work_days"] if 0 <= d <= 6}))
    if "is_admin" in changes:
        changes["is_admin"] = int(changes["is_admin"])
    if body.clear_fee:
        changes["fee_override"] = None
    to = changes.pop("status", None)
    if to == "active" and m["status"] == "inactive" and not m["password_hash"]:
        to = "invited"   # never joined: back to waiting on their invite, not an account with no password
    if to and to != m["status"] and not (to == "active" and m["status"] == "invited"):   # only accepting activates an invite
        MEMBER.move(db, member_id, m["status"], to)
        changes["status"] = to   # for the checks below; already written
    if changes.keys() - {"status"}:
        repo.update_member(db, member_id, {k: v for k, v in changes.items() if k != "status"})
    if changes.get("status") == "inactive":
        end_sessions(db, member_id)
    log_event(db, me["clinic_id"], me["id"], "member", member_id, "updated", body.model_dump(exclude_none=True))
    return public_member(repo.member(db, member_id))


def remove_member(db, me: dict, member_id: int) -> dict:
    """Members with history are deactivated, not deleted."""
    m = repo.clinic_member(db, me["clinic_id"], member_id)
    if not m:
        raise NotFound("Member not found.")
    if m["is_owner"]:
        raise Conflict("The owner cannot be removed.")
    used = repo.has_history(db, member_id)
    if used:
        repo.deactivate(db, member_id, m["status"])
        end_sessions(db, member_id)
    else:
        repo.clear_own_trail(db, member_id)
        end_sessions(db, member_id)
        repo.delete_member(db, member_id)
    log_event(db, me["clinic_id"], me["id"], "member", member_id, "deactivated" if used else "removed")
    return {"removed": not used, "deactivated": bool(used)}


def view_invite(db, code: str) -> dict:
    m = repo.invite_view(db, code)
    if not m:
        raise NotFound("This invitation link is not valid.")
    if m["invite_expires_at"] and m["invite_expires_at"] < now():
        raise Gone("Invite expired. Ask for a new link.")
    m.pop("invite_expires_at")
    return m


def accept_invite(db, code: str, password: str) -> dict:
    m = repo.invited_member(db, code)
    if not m:
        raise NotFound("This invitation link is not valid.")
    if m["invite_expires_at"] and m["invite_expires_at"] < now():
        raise Gone("Invite expired. Ask for a new link.")
    validate_password(password)
    if not repo.accept_invite(db, m["id"], code, hash_password(password)):   # opened twice at once: one wins
        raise Gone("This invitation was already used. Log in instead.")
    log_event(db, m["clinic_id"], m["id"], "member", m["id"], "joined")
    return {"token": create_session(db, m["id"])}
