"""Consultation text saves are versioned: an older save never overwrites a newer one."""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import clinic, started_visit


def test_older_save_cannot_overwrite_newer_text():
    with TestClient(app) as c:
        h, doc = clinic(c, "g1@x.in")
        v = started_visit(c, h, doc)
        rev = c.get(f"/api/visits/{v['id']}", headers=h).json()["text_rev"]
        newer = c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Newer clinical text", "rev": rev}).json()
        assert c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Older clinical text", "rev": rev}).status_code == 409
        got = c.get(f"/api/visits/{v['id']}", headers=h).json()
        assert got["text"] == "Newer clinical text" and got["text_rev"] == newer["rev"]


def test_save_without_version_is_refused():
    with TestClient(app) as c:
        h, doc = clinic(c, "t1@x.in")
        v = started_visit(c, h, doc)
        assert c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Newer", "rev": 0}).status_code == 200
        assert c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Older"}).status_code == 422
        assert c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Older", "rev": 0}).status_code == 409
        assert c.get(f"/api/visits/{v['id']}", headers=h).json()["text"] == "Newer"
