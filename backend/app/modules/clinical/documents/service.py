"""Upload, read in the background, serve back."""
import base64
import logging
import re

import httpx

from app.core.visit import get_visit
from app.modules.clinical.brief import service as brief
from app.shared import files as storage
from app.shared.ai import llm
from app.shared.audit import log_event
from app.shared.db import connect
from app.shared.errors import Conflict, Invalid, NotFound, TooLarge, Unsupported
from . import repo

log = logging.getLogger(__name__)


def load_docs(db, patient_id: int) -> list[dict]:
    return repo.for_patient(db, patient_id)


def extract_document(data: bytes, mime: str, filename: str) -> dict:
    """Returns {"summary": str, "findings": [{"name", "value", "unit"}]}."""
    if llm.enabled() and (mime or "").split("/")[0] in ("image", "application"):
        return llm.generate([{"text": llm.prompt("extract.txt")}, {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}])
    text = data.decode(errors="ignore")[:4000] if (mime or "").startswith("text") else ""
    head = next((x.strip() for x in text.splitlines() if x.strip()), "")
    findings = [{"name": n.strip(), "value": v, "unit": u.strip()}
                for n, v, u in re.findall(r"([A-Za-z][A-Za-z0-9 ]{1,20})[:\s]+(\d+(?:\.\d+)?)\s*([a-zA-Z/%]*)", text)][:10]
    return {"summary": text[:300] or f"Uploaded document: {filename}", "findings": findings, "title": head if 0 < len(head) <= 60 and not re.search(r"\d", head) else ""}


def reading_error(e: Exception) -> str:
    """A short reason for the person who uploaded; never the request URL, which can hold a key."""
    status = getattr(getattr(e, "response", None), "status_code", None)
    if status == 404:
        return "The AI model wasn't found. Check LLM_MODEL in backend/app/config.py."
    if status in (400, 401, 403):
        return f"The AI service refused the request ({status}). Check the API key."
    if status == 429:
        return "The AI service is busy or over its limit. Try again in a minute."
    if status:
        return f"The AI service answered {status}. Try again."
    if isinstance(e, httpx.TimeoutException):
        return "The AI service took too long. Try again."
    if isinstance(e, httpx.HTTPError):
        return "Couldn't reach the AI service. Check the internet connection."
    return "The file couldn't be read."


def run_extraction(doc_id: int) -> None:
    db = connect()
    try:
        d = repo.get(db, doc_id)
        try:
            ex = extract_document(storage.read(d["path"]), d["mime"], d["filename"])
            repo.set_read(db, doc_id, "ready", ex)
        except Exception as e:  # keep the file, flag the failure
            log.warning("Reading document %s failed: %s", doc_id, type(e).__name__)
            repo.set_read(db, doc_id, "failed", {"summary": reading_error(e), "findings": []})
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
    if d["ai_status"] != "failed":
        raise Conflict("This document isn't waiting for another try.")
    repo.set_processing(db, doc_id)
    log_event(db, me["clinic_id"], me["id"], "document", doc_id, "read_again")
    return repo.listed(db, doc_id)


def for_visit(db, me, visit_id: int) -> list[dict]:
    get_visit(db, me, visit_id)
    return repo.for_visit(db, visit_id)


def remove(db, me, doc_id: int) -> dict:
    """Removes a wrongly added document, until the visit's note is signed (a signed note may cite it)."""
    d = repo.in_clinic(db, me["clinic_id"], doc_id)
    if not d:
        raise NotFound("Document not found.")
    if d["visit_id"] and repo.note_signed(db, d["visit_id"]):
        raise Conflict("The note for this visit is signed, so its documents stay.")
    repo.delete(db, doc_id)
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
