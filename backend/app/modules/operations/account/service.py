"""Login, passwords, own profile and owner onboarding."""
import json

from app.core import departments
from app.core.clinic import clinic_of, public_clinic
from app.shared import mail as mailer
from app.shared.audit import log_event
from app.shared.auth import (check_password, create_session, end_sessions, hash_password, later, LOCK_MINUTES, MAX_FAILED_LOGINS,
                             new_code, public_member, RESET_HOURS, SCREENS, token_hash, validate_password)
from app.shared.db import now
from app.shared.errors import Conflict, Forbidden, Gone, Invalid, Locked, Unauthorized
from app.shared.validate import clean_email, clean_phone

from . import repo


def login(db, email: str, password: str) -> dict:
    m = repo.member_by_email(db, email.strip())
    if m:
        # One login at a time per account, shared with password change and reset: parallel wrong guesses can't each
        # read the same count and slip past the lockout, and a login checked against the old password can't
        # create its session after the password changed (the change ends sessions only once this one commits).
        db.lock(f"password:{m['id']}")
        m = repo.member(db, m["id"])
    if m and m["locked_until"] and m["locked_until"] > now():
        raise Locked(f"Locked. Try in {LOCK_MINUTES} minutes.")
    if not m or m["status"] != "active" or not check_password(password, m["password_hash"]):
        if m:
            fails = (m["failed_logins"] or 0) + 1
            locked = later(minutes=LOCK_MINUTES) if fails >= MAX_FAILED_LOGINS else None
            repo.set_failed_logins(db, m["id"], 0 if locked else fails, locked)
            db.commit()  # the failed request rolls back; the count must stick
        raise Unauthorized("Email or password is wrong.")
    repo.clear_failed_logins(db, m["id"])
    if not m["password_hash"].startswith("pbkdf2$"):  # upgrade older hashes on login
        repo.set_password(db, m["id"], hash_password(password))
    log_event(db, m["clinic_id"], m["id"], "member", m["id"], "logged_in")
    return {"token": create_session(db, m["id"])}


def logout(db, token: str) -> dict:
    repo.delete_session(db, token_hash(token))
    return {"ok": True}


def change_password(db, me: dict, current: str, new: str, token: str) -> dict:
    db.lock(f"password:{me['id']}")   # shared with reset_password, so neither overwrites the other
    m = repo.member(db, me["id"])
    if not check_password(current, m["password_hash"]):
        raise Invalid("Current password is wrong.")
    validate_password(new)
    repo.set_password(db, me["id"], hash_password(new))
    repo.drop_resets(db, me["id"])   # a link sent before the change must not work after it
    end_sessions(db, me["id"], keep=token)
    log_event(db, me["clinic_id"], me["id"], "member", me["id"], "password_changed")
    return {"ok": True}


def email_taken(db, email: str, except_id: int | None = None) -> bool:
    return repo.email_taken(db, email, except_id)


def make_reset(db, member_id: int) -> str:
    code = new_code()
    repo.replace_reset(db, member_id, token_hash(code), later(hours=RESET_HOURS))
    return code


def reset_is_live(db, code: str, member_id: int) -> bool:
    return repo.live_reset_exists(db, token_hash(code), member_id, now())


def forgot(db, email: str) -> dict:
    """Same answer either way, so emails can't be enumerated."""
    m = repo.member_by_email(db, email.strip(), active_only=True)
    if m:
        code = make_reset(db, m["id"])
        link = f"{mailer.app_url()}/#/reset/{code}"
        mailer.send(m["email"], "Reset your Dictate password",
                    f"Hello {m['name']},\n\nOpen this link within {RESET_HOURS} hours to set a new password:\n"
                    f"{link}\n\nIf you did not ask for this, ignore this email.",
                    mailer.branded(clinic_of(db, m)["name"] or "Dictate", "Reset your password",
                                   f"Hello {m['name']}, tap the button to set a new password.",
                                   "Set new password", link, f"The link works for {RESET_HOURS} hours. If you didn't ask for this, ignore this email."))
    return {"ok": True, "email_sent": mailer.enabled()}


def reset_password(db, code: str, password: str) -> dict:
    r = repo.reset(db, token_hash(code))
    if not r or r["used_at"] or r["expires_at"] < now():
        raise Gone("Link expired. Ask for a new one.")
    validate_password(password)
    db.lock(f"password:{r['member_id']}")
    r = repo.reset(db, token_hash(code))   # look again under the lock: a password change may have cancelled it
    if not r or r["used_at"] or r["expires_at"] < now():
        raise Gone("Link expired. Ask for a new one.")
    repo.reset_password(db, r["member_id"], hash_password(password))
    repo.use_reset(db, r["token_hash"], now())
    repo.drop_resets(db, r["member_id"])
    end_sessions(db, r["member_id"])
    m = repo.member(db, r["member_id"])
    log_event(db, m["clinic_id"], r["member_id"], "member", r["member_id"], "password_reset")
    return {"token": create_session(db, r["member_id"])}


def me(db, me: dict) -> dict:
    return {"member": me, "clinic": public_clinic(clinic_of(db, me))}


def edit_me(db, me: dict, body) -> dict:
    email = clean_email(body.email)
    if repo.email_taken(db, email, me["id"]):
        raise Conflict("Email already registered.")
    repo.update_profile(db, me["id"], " ".join(body.name.split()), email, clean_phone(body.phone),
                        departments.chosen(body.speciality, me.get("speciality")) if me["kind"] == "doctor" else None,
                        body.designation.strip() or None if me["kind"] != "doctor" else me.get("designation"))
    log_event(db, me["clinic_id"], me["id"], "member", me["id"], "updated")
    return public_member(repo.member(db, me["id"]))


def create_owner(db, body) -> dict:
    """Step 1: creator becomes Owner."""
    email = clean_email(body.email)
    validate_password(body.password)
    if email_taken(db, email):
        raise Conflict("Email already registered.")
    clinic_id = repo.create_clinic(db)
    mid = repo.create_owner(db, clinic_id, "doctor" if body.is_doctor else "staff", body.name.strip(), email, clean_phone(body.phone),
                            hash_password(body.password), departments.chosen(body.speciality) if body.is_doctor else None, json.dumps(SCREENS))
    log_event(db, clinic_id, mid, "clinic", clinic_id, "created")
    return {"token": create_session(db, mid)}


def edit_owner(db, me: dict, body) -> dict:
    if not me["is_owner"] or clinic_of(db, me)["onboarded"]:
        raise Forbidden("Change this in your account.")
    email = clean_email(body.email)
    if email_taken(db, email, me["id"]):
        raise Conflict("Email already registered.")
    repo.update_owner(db, me["id"], body.name.strip(), email, clean_phone(body.phone), "doctor" if body.is_doctor else "staff",
                      departments.chosen(body.speciality, me.get("speciality")) if body.is_doctor else None)
    if body.password:
        validate_password(body.password)
        db.lock(f"password:{me['id']}")
        repo.set_password(db, me["id"], hash_password(body.password))
        repo.drop_resets(db, me["id"])
    log_event(db, me["clinic_id"], me["id"], "member", me["id"], "updated")
    return public_member(repo.member(db, me["id"]))


def finish(db, me: dict) -> dict:
    repo.finish(db, me["clinic_id"])
    return public_clinic(clinic_of(db, me))
