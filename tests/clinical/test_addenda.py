"""Addenda: dated, signed additions under a signed note. The note never changes; only doctors add them."""
from fastapi.testclient import TestClient

from app.main import app
from app.shared.db import connect
from tests.helpers import clinic, join, member, started_visit


def signed_note(c, h, doc):
    v = started_visit(c, h, doc)
    c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Sugar review. HbA1c awaited.", "rev": 0})
    n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
    return v, n


def test_only_a_signed_note_takes_an_addendum_and_it_never_changes_the_note():
    with TestClient(app) as c:
        h, doc = clinic(c, "addendum@x.in")
        v, n = signed_note(c, h, doc)
        assert c.post(f"/api/notes/{n['id']}/addenda", headers=h, json={"text": "Too early."}).status_code == 409   # still a draft
        signed = c.post(f"/api/notes/{n['id']}/sign", headers=h).json()
        assert c.post(f"/api/notes/{n['id']}/addenda", headers=h, json={"text": "   "}).status_code == 422
        out = c.post(f"/api/notes/{n['id']}/addenda", headers=h, json={"text": "HbA1c received: 7.4%. Same plan."}).json()
        assert [a["text"] for a in out["addenda"]] == ["HbA1c received: 7.4%. Same plan."] and out["addenda"][0]["signed_by_name"]
        assert out["content"] == signed["content"] and out["status"] == "signed"                                # the note is untouched
        assert c.put(f"/api/notes/{n['id']}", headers=h, json={"soap": {"S": "x", "O": "", "A": "", "P": ""}, "rx": []}).status_code == 409
        c.post(f"/api/notes/{n['id']}/addenda", headers=h, json={"text": "Lipids normal."})
        assert [a["text"] for a in c.get(f"/api/visits/{v['id']}", headers=h).json()["note"]["addenda"]] == [
            "HbA1c received: 7.4%. Same plan.", "Lipids normal."]


def test_only_doctors_of_the_clinic_add_addenda():
    with TestClient(app) as c:
        h, doc = clinic(c, "addendum-who@x.in")
        v, n = signed_note(c, h, doc)
        c.post(f"/api/notes/{n['id']}/sign", headers=h)
        desk = join(c, member(c, h, "Desk", "desk-add@x.in", "staff", ["operations", "patients"])["invite_code"])
        assert c.post(f"/api/notes/{n['id']}/addenda", headers=desk, json={"text": "x"}).status_code == 403
        other, _ = clinic(c, "addendum-other@x.in")
        assert c.post(f"/api/notes/{n['id']}/addenda", headers=other, json={"text": "x"}).status_code == 404


def test_addenda_show_on_the_patient_page_the_print_and_the_next_brief():
    with TestClient(app) as c:
        h, doc = clinic(c, "addendum-show@x.in")
        v, n = signed_note(c, h, doc)
        c.post(f"/api/notes/{n['id']}/sign", headers=h)
        c.post(f"/api/notes/{n['id']}/addenda", headers=h, json={"text": "HbA1c received: 7.4%."})
        p = c.get(f"/api/visits/{v['id']}", headers=h).json()["patient_id"]
        assert c.get(f"/api/patients/{p}", headers=h).json()["visits"][0]["note"]["addenda"] == 1
        assert "HbA1c received: 7.4%." in c.get(f"/api/notes/{n['id']}/print", headers=h).text
        db = connect(); db.execute("update visits set date = '2026-01-05' where id = ?", (v["id"],)); db.commit(); db.close()
        today = c.post("/api/visits/walk-in", headers=h, json={"patient_id": p, "doctor_id": doc, "payment_method": "cash"}).json()
        b = c.post(f"/api/visits/{today['id']}/brief", headers=h).json()
        assert [a["text"] for a in b["events"][0]["addenda"]] == ["HbA1c received: 7.4%."]
        c.post(f"/api/notes/{n['id']}/addenda", headers=h, json={"text": "Lipids normal."})
        assert c.get(f"/api/visits/{today['id']}", headers=h).json()["brief"] is None    # a new addendum makes the brief again
