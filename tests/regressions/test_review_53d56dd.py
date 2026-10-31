"""Findings from the review of 53d56dd: placeholder-only .env.example, single-use invites, document removal vs
signing, prescriptions only as said, non-Latin download names, tests never loading the developer's .env."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.clinical.documents import repo as documents_repo
from app.modules.clinical.notes import service as notes
from app.modules.operations.administration import service as administration
from app.shared.ai.tasks.draft_note import task as draft_note
from app.shared.auth import member_for_token
from app.shared.db import connect
from tests.helpers import clinic, member, started_visit
from tests.regressions.test_security_and_races import in_the_gap

ROOT = Path(__file__).resolve().parents[2]


def test_env_example_holds_no_real_secrets():
    secret = re.compile(r"^(\w*(KEY|PASSWORD|SECRET|TOKEN)\w*|DATABASE_URL)=(.*)$")
    filled = [m.group(1) for line in (ROOT / ".env.example").read_text().splitlines() if (m := secret.match(line.strip())) and m.group(3).strip()]
    assert filled == [], f"put real values in .env, never .env.example: {filled}"


def test_an_invite_link_works_once_even_when_used_twice_at_the_same_time():
    with TestClient(app) as c:
        h, _ = clinic(c, "inv-race@x.in")
        code = member(c, h, "Nurse", "nurse-race@x.in", "staff", ["operations"])["invite_code"]
        second = []
        def accept_too():
            db = connect()
            try:
                second.append(administration.accept_invite(db, code, "second123"))
                db.commit()
            except Exception as e:
                db.rollback()
                second.append(type(e).__name__)
            finally:
                db.close()
        back = in_the_gap(administration, "validate_password", lambda a: a[0] == "first123", accept_too)
        try:
            first = c.post("/api/invites/accept", json={"code": code, "password": "first123"})
        finally:
            back()
        wins = [first.status_code == 200, isinstance(second[0], dict)]
        assert wins.count(True) == 1                                       # exactly one accept made a login


def test_a_document_never_disappears_from_under_a_signed_note():
    with TestClient(app) as c:
        h, doc = clinic(c, "rm-sign@x.in")
        v = started_visit(c, h, doc)
        d = c.post(f"/api/visits/{v['id']}/documents", headers=h, files={"file": ("lab.txt", b"HbA1c 7.1 %", "text/plain")}).json()
        c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Fever.", "rev": 0})
        n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
        db = connect()
        db.execute("update notes set citations = ? where id = ?", (json.dumps({"O": [f"D{d['id']}"]}), n["id"]))
        db.commit(); db.close()
        me = member_for_token(connect(), h["Authorization"].split()[1])
        signed = []
        def sign_now():
            db = connect()
            try:
                notes.sign(db, me, n["id"]); db.commit(); signed.append(True)
            except Exception:
                db.rollback()
            finally:
                db.close()
        back = in_the_gap(documents_repo, "note_signed", lambda a: True, sign_now)   # removal has just checked "not signed"
        try:
            removed = c.delete(f"/api/documents/{d['id']}", headers=h).status_code
        finally:
            back()
        note = c.get(f"/api/visits/{v['id']}", headers=h).json()["note"]
        files = [x["id"] for x in c.get(f"/api/visits/{v['id']}/documents", headers=h).json()]
        cited = {x for ids in note["citations"].values() for x in ids}
        assert removed in (200, 409)
        assert d["id"] in files or f"D{d['id']}" not in cited                # signed or not, never a link to a removed file


def items(text):
    return [{"id": "T1", "kind": "transcript", "text": text}]


def test_prescriptions_keep_only_what_the_doctor_said():
    said = items("Do not give amoxicillin, she is allergic. Stop metformin, start Glimepiride 2 mg once daily before breakfast. "
                 "Give Dolo 650 mg twice daily. Continue for five days.")
    rx = [{"medicine": "Amoxicillin 500 mg", "dose": "1-1-1"},                                   # told not to give
          {"medicine": "Metformin 500 mg", "dose": "1-0-1"},                                     # stopped
          {"medicine": "Dolo 1000 mg", "dose": "1-0-1"},                                         # strength not said
          {"medicine": "Tab Glimepiride 2 mg", "dose": "1-0-0", "duration": "30 days", "instructions": "before breakfast"},
          {"medicine": "Dolo 650 mg", "dose": "1-1-1", "duration": "5 days", "instructions": "after food"}]
    assert draft_note.keep_said([r | {k: r.get(k, "") for k in ("duration", "instructions")} for r in rx], said) == [
        {"medicine": "Tab Glimepiride 2 mg", "dose": "1-0-0", "duration": "", "instructions": "before breakfast"},   # 30 days invented
        {"medicine": "Dolo 650 mg", "dose": "", "duration": "5 days", "instructions": ""}]                       # thrice, after food invented


def test_the_plain_draft_also_skips_medicines_the_doctor_ruled_out():
    out = draft_note.fallback({}, items("Allergic to Amoxicillin 500 mg before. Give Dolo 650 mg twice daily."))
    assert [r["medicine"] for r in out["rx"]] == ["Dolo 650 mg"]


def test_a_document_with_a_non_latin_name_opens():
    with TestClient(app) as c:
        h, doc = clinic(c, "malayalam@x.in")
        v = started_visit(c, h, doc)
        d = c.post(f"/api/visits/{v['id']}/documents", headers=h, files={"file": ("ലാബ് റിപ്പോർട്ട്.txt", b"HbA1c 7.1 %", "text/plain")}).json()
        r = c.get(f"/api/documents/{d['id']}/file", headers=h)
        assert r.status_code == 200 and r.content == b"HbA1c 7.1 %"
        assert "filename*=UTF-8''%E0%B4%B2" in r.headers["content-disposition"]


def test_tests_never_read_the_developers_env_file():
    probe = ("import dotenv, sys; calls = []; dotenv.load_dotenv = lambda *a, **k: calls.append(a); "
             "sys.path.insert(0, 'backend'); import app; print(len(calls))")
    run = lambda env: subprocess.run([sys.executable, "-c", probe], cwd=ROOT, env=env, capture_output=True, text=True).stdout.strip()
    base = {k: v for k, v in os.environ.items() if k != "CLINIC_DOTENV"}
    assert run(base | {"CLINIC_DOTENV": "0"}) == "0" and run(base) == "1"
    assert os.environ["CLINIC_DOTENV"] == "0"                                  # and conftest switches it off
