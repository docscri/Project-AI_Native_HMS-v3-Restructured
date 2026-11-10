"""A doctor's own signature: drawn or uploaded in the browser (cleaned to a transparent PNG there), shown on signed notes."""
from app.shared import files as storage
from app.shared.audit import log_event
from app.shared.errors import Forbidden, Invalid, NotFound, TooLarge
from . import repo

MAX = 300 * 1024
PNG = b"\x89PNG\r\n\x1a\n"


def _doctor(me) -> None:
    if me["kind"] != "doctor":
        raise Forbidden("Only doctors have a signature.")


def save(db, me, data: bytes) -> dict:
    _doctor(me)
    if len(data) > MAX:
        raise TooLarge("Signature image is too large.")
    if not data.startswith(PNG):
        raise Invalid("Signature must be a PNG image.")
    sid = repo.add(db, me["clinic_id"], me["id"], storage.save(me["clinic_id"], data, "image/png"))
    repo.set_current(db, me["id"], sid)
    log_event(db, me["clinic_id"], me["id"], "member", me["id"], "signature_updated")
    return {"signature_id": sid}


def remove(db, me) -> dict:
    """Stops using it on new notes; the image stays for the notes already signed with it."""
    _doctor(me)
    repo.set_current(db, me["id"], None)
    log_event(db, me["clinic_id"], me["id"], "member", me["id"], "signature_removed")
    return {"signature_id": None}


def image(db, me, signature_id: int) -> bytes:
    s = repo.get(db, me["clinic_id"], signature_id)
    if not s:
        raise NotFound("Signature not found.")
    return storage.read(s["path"])


def image_or_none(db, clinic_id: int, signature_id: int | None) -> bytes | None:
    """For printing: a missing file never stops a note from printing."""
    if not signature_id:
        return None
    s = repo.get(db, clinic_id, signature_id)
    try:
        return storage.read(s["path"]) if s else None
    except Exception:
        return None
