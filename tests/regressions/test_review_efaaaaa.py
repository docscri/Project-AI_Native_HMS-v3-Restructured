"""Findings from the review of efaaaaa: a redraft racing a report's removal can't leave a signed note citing it,
and a prescription's strength and tablet count must come from that medicine's own instruction."""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.modules.clinical.notes import service as notes
from app.shared.ai.tasks.draft_note import task as draft_note
from app.shared.db import connect
from tests.helpers import cites_by_letter, clinic, started_visit
from tests.regressions.test_security_and_races import in_the_gap


def test_a_report_removed_while_the_note_is_redrafted_is_never_cited_by_the_signed_note(monkeypatch):
    with TestClient(app) as c:
        h, doc = clinic(c, "redraft-race@x.in")
        v = started_visit(c, h, doc)
        d = c.post(f"/api/visits/{v['id']}/documents", headers=h, files={"file": ("lab.txt", b"HbA1c 7.1 %", "text/plain")}).json()
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Sugar review.", "rev": 0})
        c.post(f"/api/visits/{v['id']}/note/draft", headers=h)
        monkeypatch.setattr(notes, "draft_note", lambda patient, items, sheet=None: {   # the AI read the report and cites it
            "soap": {"S": "Sugar review.", "O": "HbA1c 7.1 %.", "A": "", "P": ""}, "rx": [],
            "citations": {"S": ["T1"], "O": [f"D{d['id']}"]}})
        removed = []
        back = in_the_gap(notes, "draft_note", lambda a: True,      # the report is removed while the AI is writing
                          lambda: removed.append(c.delete(f"/api/documents/{d['id']}", headers=h).status_code))
        try:
            c.post(f"/api/visits/{v['id']}/note/draft", headers=h)
        finally:
            back()
        n = c.get(f"/api/visits/{v['id']}", headers=h).json()["note"]
        assert removed == [200] and f"D{d['id']}" not in cites_by_letter(n)["O"]
        assert c.post(f"/api/notes/{n['id']}/sign", headers=h).status_code == 200
        db = connect()
        signed = json.loads(db.execute("select citations from notes where id = ?", (n["id"],)).fetchone()[0])
        db.close()
        assert f"D{d['id']}" not in {x for ids in signed.values() for x in ids}


def test_signing_drops_a_citation_to_a_report_that_no_longer_exists():
    with TestClient(app) as c:
        h, doc = clinic(c, "sign-check@x.in")
        v = started_visit(c, h, doc)
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Fever.", "rev": 0})
        n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
        db = connect()
        db.execute("update notes set citations = ? where id = ?", (json.dumps({"S": ["T1"], "O": ["D999"]}), n["id"]))
        db.commit(); db.close()
        assert c.post(f"/api/notes/{n['id']}/sign", headers=h).status_code == 200
        db = connect()
        signed = json.loads(db.execute("select citations from notes where id = ?", (n["id"],)).fetchone()[0])
        db.close()
        assert signed == {"S": ["T1"], "O": []}


def keep(text, rx):
    items = [{"id": "T1", "kind": "transcript", "text": text}]
    full = [r | {k: r.get(k, "") for k in ("dose", "duration", "instructions")} for r in rx]
    return [(r["medicine"], r["dose"], r["duration"]) for r in draft_note.keep_said(full, items)]


def test_tablet_count_must_match_what_was_said():
    assert keep("Give Dolo 650 mg, one tablet twice daily.", [{"medicine": "Dolo 650 mg", "dose": "2-0-2"}]) == [("Dolo 650 mg", "", "")]
    assert keep("Give Dolo 650 mg, one tablet twice daily.", [{"medicine": "Dolo 650 mg", "dose": "1-0-1"}]) == [("Dolo 650 mg", "1-0-1", "")]
    assert keep("Give Augmentin 625 mg, half tablet twice daily.", [{"medicine": "Augmentin 625 mg", "dose": "½-0-½"}]) == [("Augmentin 625 mg", "½-0-½", "")]


def test_strength_and_schedule_come_from_that_medicines_own_words():
    said = "Give Dolo 650 mg twice daily and Pantoprazole 40 mg once daily."
    assert keep(said, [{"medicine": "Dolo 40 mg"}, {"medicine": "Pantoprazole 650 mg"}]) == []          # strengths swapped
    assert keep(said, [{"medicine": "Pantoprazole 40 mg", "dose": "1-0-1"}]) == [("Pantoprazole 40 mg", "", "")]   # Dolo's "twice"
    assert keep(said, [{"medicine": "Pantoprazole 40 mg", "dose": "1-0-0"}]) == [("Pantoprazole 40 mg", "1-0-0", "")]
    assert keep("Start Metformin 500 mg twice daily. Give Dolo 650 mg for three days.",
                [{"medicine": "Metformin 500 mg", "duration": "3 days"}]) == [("Metformin 500 mg", "", "")]     # Dolo's duration
    assert keep("Give Cetirizine 10 mg at night. Continue for five days.",
                [{"medicine": "Cetirizine 10 mg", "dose": "0-0-1", "duration": "5 days"}]) == [("Cetirizine 10 mg", "0-0-1", "5 days")]
