"""Upload, read in the background, serve back."""
import logging

from app.core.visit import get_visit
from app.modules.clinical.brief import service as brief
from app.shared import files as storage
from app.shared.ai import tasks
from app.shared.ai.tasks.read_report import task as read_report
from app.shared.audit import log_event
from app.shared.db import connect
from app.shared.errors import Conflict, Invalid, NotFound, TooLarge, Unsupported
from . import repo

log = logging.getLogger(__name__)
UNREAD = "Couldn't be read. Try again, or tell the clinic admin if it keeps failing."


def load_docs(db, patient_id: int) -> list[dict]:
    return repo.for_patient(db, patient_id)


def extract_document(data: bytes, mime: str, filename: str) -> dict:
    """Returns {"title", "summary", "findings": [{"name", "value", "unit", "range", "flag"}]}; raises if the AI can't read it."""
    return tasks.run(read_report, on_failure="raise", data=data, mime=mime, filename=filename)


def run_extraction(doc_id: int) -> None:
    db = connect()
    try:
        d = repo.get(db, doc_id)
        try:
            ex = extract_document(storage.read(d["path"]), d["mime"], d["filename"])
            repo.set_read(db, doc_id, "ready", ex)
        except Exception as e:  # keep the file, flag the failure
            log.warning("Reading document %s failed: %s", doc_id, tasks.reason(e, read_report))   # for whoever runs the server
            repo.set_read(db, doc_id, "failed", {"summary": UNREAD, "findings": []})   # what clinic staff see
        db.commit()
    finally:
        db.close()
    if d and d["visit_id"]:
        brief.prebuild(d["visit_id"])   # a report brought at arrival appears in the brief


def upload(db, me, visit_id: int, filename: str | None, mime: str, data: bytes) -> tuple[dict, int]:
    """Saves the file and commits so the background read sees it; returns the row and its id."""
    v = get_visit(db, me, visit_id)
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime not in storage.ALLOWED:
        raise Unsupported("Use a PDF, photo or text file.")
    if len(data) > storage.MAX_BYTES:
        raise TooLarge("File over 15 MB.")
    if not data:
        raise Invalid("The file is empty.")
    path = storage.save(me["clinic_id"], data, mime)
    did = repo.add(db, me["clinic_id"], v["patient_id"], visit_id, filename or "document", str(path), mime)
    log_event(db, me["clinic_id"], me["id"], "document", did, "uploaded", {"visit": visit_id})
    db.commit()
    return repo.listed(db, did), did


def retry(db, me, doc_id: int) -> dict:
    """Reads a failed document again; the caller commits and runs run_extraction."""
    d = repo.in_clinic(db, me["clinic_id"], doc_id)
    if not d:
        raise NotFound("Document not found.")
    repo.set_processing(db, doc_id, d["ai_status"])
    log_event(db, me["clinic_id"], me["id"], "document", doc_id, "read_again")
    return repo.listed(db, doc_id)


def for_visit(db, me, visit_id: int) -> list[dict]:
    get_visit(db, me, visit_id)
    return repo.for_visit(db, visit_id)


def remove(db, me, doc_id: int) -> dict:
    """Removes a wrongly added document, unless a signed note relies on it: its own visit's note, or any signed note
    of the patient that cites it (reports belong to the patient, so a later visit's note can cite them)."""
    d = repo.in_clinic(db, me["clinic_id"], doc_id)
    if not d:
        raise NotFound("Document not found.")
    db.lock(f"patient:{d['patient_id']}")   # shared with signing, so the checks below can't go stale
    if d["visit_id"] and repo.note_signed(db, d["visit_id"]):
        raise Conflict("The note for this visit is signed, so its documents stay.")
    if repo.cited_by_signed_note(db, d["patient_id"], f"D{doc_id}"):
        raise Conflict("A signed note cites this document, so it stays.")
    repo.delete(db, doc_id)
    repo.uncite_in_drafts(db, d["patient_id"], f"D{doc_id}")
    log_event(db, me["clinic_id"], me["id"], "document", doc_id, "removed", {"visit": d["visit_id"], "filename": d["filename"]})
    db.commit()
    try:
        storage.delete(d["path"])
    except Exception:   # the record is gone; a leftover file is harmless
        log.warning("Couldn't delete the stored file for document %s", doc_id)
    return {"ok": True}


def file_of(db, me, doc_id: int) -> tuple[bytes, dict]:
    d = repo.in_clinic(db, me["clinic_id"], doc_id)
    if not d:
        raise NotFound("Document not found.")
    try:
        return storage.read(d["path"]), d
    except Exception:
        raise NotFound("File not found.")
