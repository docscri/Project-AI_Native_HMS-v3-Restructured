"""Upload, read in the background, serve back."""
import base64
import re

from app.core.visit import get_visit
from app.modules.clinical.brief import service as brief
from app.shared import files as storage
from app.shared.ai import llm
from app.shared.audit import log_event
from app.shared.db import connect
from app.shared.errors import Invalid, NotFound, TooLarge, Unsupported
from . import repo


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


def run_extraction(doc_id: int) -> None:
    db = connect()
    try:
        d = repo.get(db, doc_id)
        try:
            ex = extract_document(storage.read(d["path"]), d["mime"], d["filename"])
            repo.set_read(db, doc_id, "ready", ex)
        except Exception as e:  # keep the file, flag the failure
            repo.set_read(db, doc_id, "failed", {"summary": f"Could not read: {e}", "findings": []})
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


def file_of(db, me, doc_id: int) -> tuple[bytes, dict]:
    d = repo.in_clinic(db, me["clinic_id"], doc_id)
    if not d:
        raise NotFound("Document not found.")
    try:
        return storage.read(d["path"]), d
    except Exception:
        raise NotFound("File not found.")
