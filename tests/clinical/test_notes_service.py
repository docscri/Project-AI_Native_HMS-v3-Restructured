"""Notes and brief services called directly, without HTTP."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.clinical.brief.service import checked
from app.modules.clinical.notes import service
from app.shared.auth import member_for_token
from app.shared.db import connect
from app.shared.errors import Conflict
from tests.helpers import clinic, started_visit


def test_edit_flags_change_and_sign_locks():
    with TestClient(app) as c:
        h, doc = clinic(c, "notes-svc@example.com")
        v = started_visit(c, h, doc)
        db = connect()
        try:
            me = member_for_token(db, h["Authorization"].split()[1])
            n = service.blank(db, me, v["id"])
            same = service.edit(db, me, n["id"], {"S": "", "O": "", "A": "", "P": ""}, [])
            assert not same["edited"]
            changed = service.edit(db, me, n["id"], {"S": "Cough", "O": "", "A": "", "P": ""}, [])
            assert changed["edited"]
            signed = service.sign(db, me, n["id"])
            assert signed["status"] == "signed"
            with pytest.raises(Conflict):
                service.edit(db, me, n["id"], {"S": "Late", "O": "", "A": "", "P": ""}, [])
            with pytest.raises(Conflict):
                service.sign(db, me, n["id"])
        finally:
            db.close()


def test_checked_drops_unsupported_sentences():
    sources = {"N1": {"text": "BP 150/95. Sugar 110."}, "N2": {"text": "Sugar 110 fasting."}}
    out = checked([
        {"text": "Sugar was 110.", "cites": ["N1"]},
        {"text": "Sugar was 110.", "cites": ["N2"]},     # repeat: merged
        {"text": "Sugar was 250.", "cites": ["N1"]},     # number not in source
        {"text": "No cites here.", "cites": []},
        {"text": "Unknown source.", "cites": ["X9"]},
        "junk",
    ], sources)
    assert out == [{"text": "Sugar was 110.", "cites": ["N1", "N2"], "flags": []}]
