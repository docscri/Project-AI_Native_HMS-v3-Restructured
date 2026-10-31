"""Draft from cited evidence, edit, sign."""
import json

from app.core.clinic import clinic_of
from app.core.patient import age
from app.core.visit import get_visit, move, text_of
from app.modules.clinical.documents import service as documents
from app.shared.ai import tasks
from app.shared.ai.tasks.draft_note import task as draft_note_task
from app.shared.audit import log_event
from app.shared.db import now
from app.shared.errors import Conflict, Forbidden, Invalid, NotFound
from app.shared.text import sentences
from . import repo


def load_note(db, visit_id: int) -> dict | None:
    return repo.for_visit(db, visit_id)


def past_notes(db, patient_id: int, before_visit: int) -> list[dict]:
    return repo.past(db, patient_id, before_visit)


def evidence(text: str, documents: list[dict], past_notes: list[dict]) -> list[dict]:
    """Citable sources with stable ids; free text cited by sentence (T1, T2...)."""
    items = [{"id": f"T{i + 1}", "kind": "transcript", "text": t} for i, t in enumerate(sentences(text))]
    for d in documents:
        ex = d.get("extracted") or {}
        vals = ", ".join(f'{f["name"]} {f["value"]} {f.get("unit", "")}'.strip() for f in ex.get("findings", []))
        items.append({"id": f'D{d["id"]}', "kind": "document",
                      "text": f'{d["filename"]} ({d["created_at"][:10]}): {ex.get("summary", "")} {vals}'.strip()})
    for n in past_notes:
        soap = n["content"]["soap"]
        items.append({"id": f'N{n["id"]}', "kind": "note",
                      "text": f'Visit {n["date"]}: A: {soap.get("A", "")} P: {soap.get("P", "")}'})
    return items


def draft_note(patient: dict, items: list[dict]) -> dict:
    """{"soap": {S, O, A, P}, "rx": [...], "citations": {"S": [ids], ...}}"""
    return tasks.run(draft_note_task, patient=patient, items=items)


def evidence_for(db, v: dict) -> tuple[dict, list[dict]]:
    p = repo.patient(db, v["patient_id"])
    patient = {"name": p["name"], "age": age(p["dob"]), "sex": p["sex"]}
    docs = [d for d in documents.load_docs(db, v["patient_id"]) if d["ai_status"] == "ready"]
    return patient, evidence(text_of(v), docs, past_notes(db, v["patient_id"], v["id"]))


def draft(db, me, visit_id: int) -> dict:
    v = get_visit(db, me, visit_id)
    existing = load_note(db, visit_id)
    if existing and existing["status"] == "signed":
        raise Conflict("Note is signed.")
    patient, items = evidence_for(db, v)
    if not any(i["kind"] == "transcript" for i in items) and not any(i["kind"] == "document" for i in items):
        raise Invalid("Dictate or add a document first.")
    d = draft_note(patient, items)
    # Same shape the editor sends back, so saving an untouched draft doesn't count as an edit.
    soap = {k: str((d.get("soap") or {}).get(k) or "") for k in ("S", "O", "A", "P")}
    rx = [{f: str(r.get(f) or "") for f in ("medicine", "dose", "duration", "instructions")} for r in d.get("rx") or [] if isinstance(r, dict)]
    d["citations"] = {k: list((d.get("citations") or {}).get(k) or []) for k in ("S", "O", "A", "P")}
    content = json.dumps({"soap": soap, "rx": rx})
    cited = {c for ids in d["citations"].values() for c in ids}
    # Saved so citations keep pointing at the right words if the transcript changes later.
    sources = json.dumps({i["id"]: i["text"] for i in items if i["kind"] == "transcript" and i["id"] in cited})
    if existing:
        if not repo.redraft(db, existing["id"], content, json.dumps(d["citations"]), sources):
            raise Conflict("Note is signed.")
    else:
        repo.add(db, me["clinic_id"], v["patient_id"], visit_id, v["doctor_id"], content, json.dumps(d["citations"]), sources)
    log_event(db, me["clinic_id"], me["id"], "note", visit_id, "drafted")
    return load_note(db, visit_id)


def blank(db, me, visit_id: int) -> dict:
    v = get_visit(db, me, visit_id)
    if v["status"] != "with_doctor":
        raise Conflict("Start the visit first.")
    if not load_note(db, visit_id):
        repo.add(db, me["clinic_id"], v["patient_id"], visit_id, v["doctor_id"],
                 json.dumps({"soap": {"S": "", "O": "", "A": "", "P": ""}, "rx": []}), "{}")
        log_event(db, me["clinic_id"], me["id"], "note", visit_id, "started")
    return load_note(db, visit_id)


def edit(db, me, note_id: int, soap: dict, rx: list) -> dict:
    n = repo.in_clinic(db, me["clinic_id"], note_id)
    if not n:
        raise NotFound("Note not found.")
    if n["status"] == "signed":
        raise Conflict("Note is signed.")
    new = {"soap": soap, "rx": rx}
    edited = 1 if new != json.loads(n["content"]) else n["edited"]
    if not repo.save(db, note_id, json.dumps(new), edited):
        raise Conflict("Note is signed.")
    return load_note(db, n["visit_id"])


def sign(db, me, note_id: int) -> dict:
    n = repo.in_clinic(db, me["clinic_id"], note_id)
    if not n:
        raise NotFound("Note not found.")
    db.lock(f"patient:{n['patient_id']}")   # shared with document removal: a file can't vanish while a note citing it is signed
    n = repo.in_clinic(db, me["clinic_id"], note_id)
    if n["status"] == "signed":
        raise Conflict("Already signed.")
    if me["kind"] != "doctor":
        raise Forbidden("Only a doctor can sign.")
    ts = now()
    if not repo.sign(db, note_id, ts, me["id"], me["name"]):
        raise Conflict("Already signed.")
    v = get_visit(db, me, n["visit_id"])
    if v["status"] == "with_doctor":
        move(db, me, v, "done", completed_at=ts)
    log_event(db, me["clinic_id"], me["id"], "note", note_id, "signed")
    return load_note(db, n["visit_id"])


def get(db, note_id: int) -> dict | None:
    return repo.get(db, note_id)


def print_parts(db, me, n: dict) -> tuple[dict, dict, dict, dict]:
    """Clinic, visit, patient and doctor for the printed note."""
    return (clinic_of(db, me), repo.visit(db, n["visit_id"]), repo.patient(db, n["patient_id"]), repo.doctor(db, n["doctor_id"]))
