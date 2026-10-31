"""Findings from the review of f255be4: a report cited by a later visit's signed note can't be removed (even while
it is being signed), and "do not give X" or an invented "10-0-10" never reaches a prescription."""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.modules.clinical.documents import repo as documents_repo
from app.modules.clinical.notes import service as notes
from app.shared.ai.tasks.draft_note import task as draft_note
from app.shared.auth import member_for_token
from app.shared.db import connect
from tests.helpers import clinic, started_visit
from tests.regressions.test_security_and_races import in_the_gap


def report_then_later_visit(c, email):
    """A report uploaded at an earlier visit, and today's visit with a draft note that cites it."""
    h, doc = clinic(c, email)
    first = started_visit(c, h, doc)
    d = c.post(f"/api/visits/{first['id']}/documents", headers=h, files={"file": ("lab.txt", b"HbA1c 7.1 %", "text/plain")}).json()
    db = connect()
    db.execute("update visits set date = '2026-01-05', status = 'done' where id = ?", (first["id"],))
    db.commit(); db.close()
    p = c.get(f"/api/visits/{first['id']}", headers=h).json()["patient_id"]
    v = c.post("/api/visits/walk-in", headers=h, json={"patient_id": p, "doctor_id": doc, "payment_method": "cash"}).json()
    c.post(f"/api/visits/{v['id']}/start", headers=h)
    c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Review of sugar.", "rev": 0})
    n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
    db = connect()
    db.execute("update notes set citations = ? where id = ?", (json.dumps({"O": [f"D{d['id']}"]}), n["id"]))
    db.commit(); db.close()
    return h, d, n


def test_a_report_cited_by_a_later_visits_signed_note_stays():
    with TestClient(app) as c:
        h, d, n = report_then_later_visit(c, "cross-visit@x.in")
        assert c.post(f"/api/notes/{n['id']}/sign", headers=h).status_code == 200
        r = c.delete(f"/api/documents/{d['id']}", headers=h)
        assert r.status_code == 409 and "signed note cites" in r.json()["detail"]


def test_a_report_removed_from_a_draft_is_uncited_everywhere():
    with TestClient(app) as c:
        h, d, n = report_then_later_visit(c, "cross-draft@x.in")
        assert c.delete(f"/api/documents/{d['id']}", headers=h).status_code == 200
        db = connect()
        cites = json.loads(db.execute("select citations from notes where id = ?", (n["id"],)).fetchone()[0])
        db.close()
        assert f"D{d['id']}" not in {x for ids in cites.values() for x in ids}


def test_signing_a_later_visits_note_during_removal_never_leaves_a_dangling_citation():
    with TestClient(app) as c:
        h, d, n = report_then_later_visit(c, "cross-race@x.in")
        me = member_for_token(connect(), h["Authorization"].split()[1])
        def sign_now():
            db = connect()
            try:
                notes.sign(db, me, n["id"]); db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        back = in_the_gap(documents_repo, "cited_by_signed_note", lambda a: True, sign_now)   # removal just checked
        try:
            c.delete(f"/api/documents/{d['id']}", headers=h)
        finally:
            back()
        db = connect()
        r = db.execute("select status, citations from notes where id = ?", (n["id"],)).fetchone()
        status, cites = r[0], r[1]
        exists = db.execute("select 1 from documents where id = ?", (d["id"],)).fetchone()
        db.close()
        cited = f"D{d['id']}" in {x for ids in json.loads(cites).values() for x in ids}
        assert not (status == "signed" and cited and not exists)


def keep(text, rx):
    items = [{"id": "T1", "kind": "transcript", "text": text}]
    full = [r | {k: r.get(k, "") for k in ("dose", "duration", "instructions")} for r in rx]
    return [(r["medicine"], r["dose"]) for r in draft_note.keep_said(full, items)]


def test_do_not_give_rules_a_medicine_out():
    assert keep("Do not give Amoxicillin 500 mg. Give Dolo 650 mg twice daily.",
                [{"medicine": "Amoxicillin 500 mg"}, {"medicine": "Dolo 650 mg", "dose": "1-0-1"}]) == [("Dolo 650 mg", "1-0-1")]
    assert keep("Give Dolo 650 mg, don't give ibuprofen 400 mg.", [{"medicine": "Ibuprofen 400 mg"}]) == []
    assert keep("Stop metformin and start Glimepiride 2 mg once daily.",
                [{"medicine": "Metformin 500 mg"}, {"medicine": "Glimepiride 2 mg", "dose": "1-0-0"}]) == [("Glimepiride 2 mg", "1-0-0")]


def test_an_invented_tablet_schedule_is_left_blank():
    assert keep("Give Dolo 650 mg twice daily.", [{"medicine": "Dolo 650 mg", "dose": "10-0-10"}]) == [("Dolo 650 mg", "")]
    assert keep("Give Dolo 650 mg 1-0-1.", [{"medicine": "Dolo 650 mg", "dose": "1-0-1"}]) == [("Dolo 650 mg", "1-0-1")]
