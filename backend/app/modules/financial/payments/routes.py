"""Refunds and printed receipts."""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.shared import printing as printpage
from app.shared.auth import member_for_token, public_member, require_screen
from app.shared.db import get_db
from app.modules.financial.payments import service
from app.modules.financial.payments.schema import Refund

router = APIRouter(prefix="/api")
front_desk = require_screen("operations")


@router.post("/visits/{visit_id}/refund")
def refund(visit_id: int, body: Refund, me=Depends(front_desk), db=Depends(get_db)):
    return service.refund(db, me, visit_id, body)


@router.get("/visits/{visit_id}/receipt", response_class=HTMLResponse)
def receipt(visit_id: int, token: str, auto: int = 0, db=Depends(get_db)):
    """Token in the query so it opens in a new tab."""
    m = member_for_token(db, token)
    if not m:
        return HTMLResponse(printpage.message("Log in again", "Your session has ended. Open the receipt from the app."), 401)
    me = public_member(m)
    v = service.paid_visit(db, me, visit_id)
    if not v:
        return HTMLResponse(printpage.message("No receipt", "This visit has not been paid yet."), 404)
    return service.receipt_page(db, me, v, bool(auto))
