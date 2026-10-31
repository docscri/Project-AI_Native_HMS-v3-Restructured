"""Departments: a fixed list of 12, chosen at sign-up, when adding a doctor and in profiles; each has its note template."""
import importlib.util
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import departments
from app.main import app
from app.shared.db import connect
from tests.helpers import clinic, join, member

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
