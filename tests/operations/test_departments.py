"""Departments: a fixed list of 12, chosen at sign-up, when adding a doctor and in profiles; each has its note template."""
import importlib.util
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import departments
from app.main import app
from app.shared.db import connect
import json

from tests.helpers import clinic, join, member, started_visit

ROOT = Path(__file__).resolve().parents[2]


def test_the_list_and_every_template():
    with TestClient(app) as c:
        listed = c.get("/api/departments").json()["departments"]      # public: sign-up needs it
        assert len(listed) == 12 and listed[0] == "General Medicine"
        h, _ = clinic(c, "dept-list@x.in")
        for d in listed:
            t = c.get("/api/departments/template", headers=h, params={"name": d}).json()
            assert t["department"] == d and t["sections"] and all(s["title"] and s["prompts"] for s in t["sections"])
            assert t["header"]["vitals"][0].startswith("BP")
        assert c.get("/api/departments/template", headers=h).json()["department"] == "General Medicine"   # the doctor's own
        assert c.get("/api/departments/template").status_code == 401


def test_frontend_list_matches_the_server():
    js = (ROOT / "frontend/js/shared/core.js").read_text(encoding="utf-8")
    assert re.findall(r'"([^"]+)"', js[js.index("const DEPARTMENTS"):js.index("];", js.index("const DEPARTMENTS"))]) == departments.DEPARTMENTS


def test_department_is_chosen_from_the_list_everywhere():
    with TestClient(app) as c:
        h = {"Authorization": "Bearer " + c.post("/api/onboarding/owner", json={"name": "Dr. Eye", "email": "dept-own@x.in", "password": "clinic123",
                                                                            "is_doctor": True, "speciality": "Ophthalmology"}).json()["token"]}
        me = c.get("/api/me", headers=h).json()["member"]
        assert me["speciality"] == "Ophthalmology"
        assert c.get("/api/departments/template", headers=h).json()["title"] == "Ophthalmology"
        doc = member(c, h, "Dr. Ear", "dept-ent@x.in", "doctor", ["consultation"]) | {}
        assert c.get("/api/members", headers=h).json()[-1]["speciality"] == "General Medicine"           # none chosen: the default
        r = c.post("/api/members", headers=h, json={"name": "Dr. X", "email": "dept-x@x.in", "kind": "doctor", "speciality": "Cardiology", "screens": []})
        assert r.status_code == 422                                                                        # not on the list
        assert c.patch(f"/api/members/{doc['id']}", headers=h, json={"speciality": "ent"}).json()["speciality"] == "ENT"
        assert c.patch(f"/api/members/{doc['id']}", headers=h, json={"speciality": "Heart"}).status_code == 422
        assert c.put("/api/me", headers=h, json={"name": "Dr. Eye", "email": "dept-own@x.in", "speciality": "Paediatrics"}).json()["speciality"] == "Paediatrics"
        assert c.put("/api/me", headers=h, json={"name": "Dr. Eye", "email": "dept-own@x.in", "speciality": ""}).json()["speciality"] == "Paediatrics"  # kept


def test_old_free_text_specialities_become_departments():
    spec = importlib.util.spec_from_file_location("m018", ROOT / "migrations/018_departments.py")
    m018 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m018)
    with TestClient(app) as c:
        h, doc = clinic(c, "dept-old@x.in")
        db = connect()
        db.execute("update members set speciality = 'Paeds clinic' where id = ?", (doc,)); db.commit()
        m018.run(db); db.commit()
        assert db.execute("select speciality from members where id = ?", (doc,)).fetchone()[0] == "Paediatrics"
        db.close()


def test_notes_follow_the_visit_doctors_department_and_old_notes_stay_soap():
    with TestClient(app) as c:
        h, doc = clinic(c, "dept-note@x.in")
        c.put("/api/me", headers=h, json={"name": "Dr. Bone", "email": "dept-note@x.in", "speciality": "Orthopaedics"})
        v = started_visit(c, h, doc)
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Pain in right knee for two weeks. BP 130/80. Likely osteoarthritis.", "rev": 0})
        n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
        assert n["content"]["template"]["department"] == "Orthopaedics" and n["content"]["vitals"] == {"BP": "130/80"}
        assert [x["title"] for x in n["content"]["sections"]] == [s["title"] for s in departments.template("Orthopaedics")["sections"]]
        assert "osteoarthritis" in n["content"]["soap"]["A"]                       # the S/O/A/P summary the brief reads
        assert c.put(f"/api/notes/{n['id']}", headers=h, json=n["content"]).json()["edited"] == 0   # the saved shape, sent back
        sections = {x["key"]: x["text"] for x in n["content"]["sections"]} | {"7": "Knee brace. Review in 2 weeks."}
        n = c.put(f"/api/notes/{n['id']}", headers=h, json={"sections": sections, "vitals": {"BP": "130/80", "Pulse": "76"}, "rx": []}).json()
        assert n["edited"] == 1 and n["content"]["vitals"]["Pulse"] == "76" and n["content"]["soap"]["P"] == "Knee brace. Review in 2 weeks."
        page = c.get(f"/api/notes/{n['id']}/print", headers=h).text
        assert "Knee brace" in page and "BP 130/80 · Pulse 76" in page
        assert c.post(f"/api/notes/{n['id']}/sign", headers=h).status_code == 200

        old = started_visit(c, h, doc, "Old")                                       # a note written before department formats
        o = c.post(f"/api/visits/{old['id']}/note", headers=h).json()
        db = connect()
        db.execute("update notes set content = ? where id = ?", (json.dumps({"soap": {"S": "Cough.", "O": "", "A": "", "P": ""}, "rx": []}), o["id"]))
        db.commit(); db.close()
        o = c.put(f"/api/notes/{o['id']}", headers=h, json={"soap": {"S": "Cough, dry.", "O": "", "A": "", "P": ""}, "rx": []}).json()
        assert "sections" not in o["content"] and o["content"]["soap"]["S"] == "Cough, dry."
        assert "Subjective" in c.get(f"/api/notes/{o['id']}/print", headers=h).text
