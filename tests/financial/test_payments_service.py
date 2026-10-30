"""Payments service called directly, without HTTP."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.financial.payments import service
from app.modules.financial.payments.schema import Refund
from app.shared.auth import member_for_token
from app.shared.db import connect
from app.shared.errors import Conflict, Invalid
from tests.helpers import clinic, started_visit


def test_refund_rules():
    with TestClient(app) as c:
        h, doc = clinic(c, "refund-svc@example.com")
        v = started_visit(c, h, doc)
        db = connect()
        try:
            me = member_for_token(db, h["Authorization"].split()[1])
            with pytest.raises(Invalid):
                service.refund(db, me, v["id"], Refund(amount=301, reason="too much"))
            with pytest.raises(Invalid):
                service.refund(db, me, v["id"], Refund(amount=100, reason="  "))
            out = service.refund(db, me, v["id"], Refund(amount=100, reason="Left early"))
            assert out["refund_amount"] == 100
            out = service.refund(db, me, v["id"], Refund(reason="Rest of it"))
            assert out["refund_amount"] == 300
            with pytest.raises(Conflict):
                service.refund(db, me, v["id"], Refund(reason="Again"))
        finally:
            db.close()
