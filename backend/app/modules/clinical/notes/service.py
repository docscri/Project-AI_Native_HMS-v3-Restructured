"""Draft from cited evidence, edit, sign."""
import json

from app.shared import usage
from app.core import departments
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
        fixes = " ".join(f'{a["signed_at"][:10]}: {a["text"].strip()}' for a in n.get("addenda") or [])
        items.append({"id": f'N{n["id"]}', "kind": "note",   # signed corrections go with the note, or the old wording lives on
                      "text": f'Visit {n["date"]}: A: {soap.get("A", "")} P: {soap.get("P", "")}' + (f" Addenda (corrections): {fixes}" if fixes else "")})
    return items


def draft_note(patient: dict, items: list[dict], sheet: dict | None = None) -> dict:
    """{"sections": [{key, title, text}], "vitals": {...}, "rx": [...], "citations": {"1": [ids], ...}, ...}"""
    return tasks.run(draft_note_task, patient=patient, items=items, sheet=sheet)


def sheet_of(db, doctor_id: int) -> dict:
    """The visit doctor's department template: their notes are written in its format."""
    return departments.template((repo.doctor(db, doctor_id) or {}).get("speciality"))


def rx_of(rx) -> list[dict]:
    return [{f: str(r.get(f) or "") for f in ("medicine", "dose", "duration", "instructions")} for r in rx or [] if isinstance(r, dict)]


def vitals_of(vitals) -> dict:
    vitals = vitals if isinstance(vitals, dict) else {}
    return {k: str(vitals[k]).strip() for k in departments.VITALS if str(vitals.get(k) or "").strip()}


def formatted(sheet: dict, texts: dict, vitals: dict, rx) -> dict:
    """A department-format note as saved (and as the editor sends it back): sections in the template's order,
    vitals, prescription and the S/O/A/P summary the brief and past-visit lines read."""
    sections = [{"key": str(i + 1), "title": s["title"], "text": str(texts.get(str(i + 1)) or "")} for i, s in enumerate(sheet["sections"])]
    vitals = vitals_of(vitals)
    return {"template": {"department": sheet["department"], "version": sheet["version"]}, "sections": sections,
            "vitals": vitals, "soap": departments.soap_of(sections, vitals), "rx": rx_of(rx)}


def evidence_for(db, v: dict) -> tuple[dict, list[dict]]:
    p = repo.patient(db, v["patient_id"])
    patient = {"name": p["name"], "age": age(p["dob"]), "sex": p["sex"]}
    docs = [d for d in documents.load_docs(db, v["patient_id"]) if d["ai_status"] == "ready"]
    return patient, evidence(text_of(v), docs, past_notes(db, v["patient_id"], v["id"]))


def existing_reports_only(db, patient_id: int, citations: dict) -> dict:
    """Citations without reports that have since been removed (D ids that no longer exist)."""
    have = {f"D{i}" for i in repo.document_ids(db, patient_id)}
    return {k: [c for c in ids if not c.startswith("D") or c in have] for k, ids in citations.items()}


def draft(db, me, visit_id: int) -> dict:
    v = get_visit(db, me, visit_id)
    existing = load_note(db, visit_id)
    if existing and existing["status"] == "signed":
        raise Conflict("Note is signed.")
    patient, items = evidence_for(db, v)
    if not any(i["kind"] == "transcript" for i in items) and not any(i["kind"] == "document" for i in items):
        raise Invalid("Dictate or add a document first.")
    sheet = sheet_of(db, v["doctor_id"])
    with usage.clinic(me["clinic_id"]):
        d = draft_note(patient, items, sheet)
    if isinstance(d.get("sections"), list):
        texts = {str(x.get("key")): x.get("text") for x in d["sections"] if isinstance(x, dict)}
        cites = d.get("citations") or {}
    else:   # an S/O/A/P draft: placed in the department's sections
        texts, cites = draft_note_task.into_sections(sheet, {k: str(t or "") for k, t in (d.get("soap") or {}).items()}, d.get("citations"))
    # Same shape the editor sends back, so saving an untouched draft doesn't count as an edit.
    note = formatted(sheet, texts, d.get("vitals"), d.get("rx"))
    d["citations"] = {x["key"]: [str(c) for c in cites.get(x["key"]) or []] for x in note["sections"]}
    db.lock(f"patient:{v['patient_id']}")   # shared with document removal: a report removed while the AI wrote stays uncited
    d["citations"] = existing_reports_only(db, v["patient_id"], d["citations"])
    content = json.dumps(note)
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
                 json.dumps(formatted(sheet_of(db, v["doctor_id"]), {}, {}, [])), "{}")
        log_event(db, me["clinic_id"], me["id"], "note", visit_id, "started")
    return load_note(db, visit_id)


def edit(db, me, note_id: int, soap: dict | None, rx: list, sections: dict | list | None = None, vitals: dict | None = None) -> dict:
    """Saves the editor's note. A department-format note takes section texts by key and vitals; S/O/A/P text sent
    for one is placed in its sections. Notes written before the department formats stay S/O/A/P."""
    n = repo.in_clinic(db, me["clinic_id"], note_id)
    if not n:
        raise NotFound("Note not found.")
    if n["status"] == "signed":
        raise Conflict("Note is signed.")
    old = json.loads(n["content"])
    if "sections" in old:
        sheet = departments.template(old["template"]["department"])
        sheet = sheet | {"version": old["template"]["version"],
                         "sections": [{"title": x["title"]} for x in old["sections"]]}   # the format the note was drafted in
        if isinstance(sections, list):   # the saved shape, sent back as is
            sections = {str(x.get("key")): str(x.get("text") or "") for x in sections if isinstance(x, dict)}
        if sections is None:
            sections, _ = draft_note_task.into_sections(sheet, soap or {})
        new = formatted(sheet, {str(k): t for k, t in sections.items()}, old.get("vitals") if vitals is None else vitals, rx)
    else:
        new = {"soap": {k: str((soap or {}).get(k) or "") for k in ("S", "O", "A", "P")}, "rx": rx_of(rx)}
    edited = 1 if new != old else n["edited"]
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
    cites = json.loads(n["citations"] or "{}")
    if (kept := existing_reports_only(db, n["patient_id"], cites)) != cites:   # a report removed since the draft was made
        repo.set_citations(db, note_id, json.dumps(kept))
    ts = now()
    repo.sign(db, note_id, ts, me["id"], me["name"])
    v = get_visit(db, me, n["visit_id"])
    if v["status"] == "with_doctor":
        move(db, me, v, "done", completed_at=ts)
    log_event(db, me["clinic_id"], me["id"], "note", note_id, "signed")
    return load_note(db, n["visit_id"])


def add_addendum(db, me, note_id: int, text: str) -> dict:
    """A dated, signed addition under a signed note; the note itself stays as signed."""
    n = repo.in_clinic(db, me["clinic_id"], note_id)
    if not n:
        raise NotFound("Note not found.")
    if n["status"] != "signed":
        raise Conflict("Sign the note first; until then, edit it.")
    if me["kind"] != "doctor":
        raise Forbidden("Only a doctor can add an addendum.")
    text = text.strip()
    if not text:
        raise Invalid("Write the addendum first.")
    if len(text) > 4000:
        raise Invalid("Keep the addendum under 4000 characters.")
    repo.add_addendum(db, me["clinic_id"], note_id, text, me["id"], me["name"], now())
    log_event(db, me["clinic_id"], me["id"], "note", note_id, "addendum_added")
    return load_note(db, n["visit_id"])


def addenda(db, note_id: int) -> list[dict]:
    return repo.addenda(db, note_id)


def get(db, note_id: int) -> dict | None:
    return repo.get(db, note_id)


def print_parts(db, me, n: dict) -> tuple[dict, dict, dict, dict]:
    """Clinic, visit, patient and doctor for the printed note."""
    return (clinic_of(db, me), repo.visit(db, n["visit_id"]), repo.patient(db, n["patient_id"]), repo.doctor(db, n["doctor_id"]))
