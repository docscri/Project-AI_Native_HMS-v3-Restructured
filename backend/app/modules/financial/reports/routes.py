"""Reports URLs: collections and day close."""
import hmac
import os
import re
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException

from app.shared import usage
from app.shared.auth import require_admin
from app.shared.db import get_db

from . import service
from .schema import Close

router = APIRouter(prefix="/api")


@router.get("/collections")
def collections(start: str, end: str | None = None, doctor_id: int | None = None, me=Depends(require_admin), db=Depends(get_db)):
    return service.collections(db, me, start, end, doctor_id)


@router.get("/day-close")
def day_close(date: str, me=Depends(require_admin), db=Depends(get_db)):
    return service.day_summary(db, me, date)


@router.post("/day-close")
def close_day(body: Close, me=Depends(require_admin), db=Depends(get_db)):
    return service.close_day(db, me, body)


# The operator's usage meter, across every clinic: what each one cost in AI and dictation this month.
# Not for clinics (they'd see your costs): only with the OPS_TOKEN set on the server, sent as X-Ops-Token.
@router.get("/ops/usage")
def ops_usage(month: str | None = None, x_ops_token: str = Header(default=""), db=Depends(get_db)):
    want = os.environ.get("OPS_TOKEN", "")
    if not want or not hmac.compare_digest(x_ops_token, want):
        raise HTTPException(404)   # as if it weren't there
    month = month or date.today().strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(422, "month is YYYY-MM")
    rows = usage.report(db, month)
    return {"month": month, "clinics": rows, "total_usd": round(sum(r["usd"] for r in rows), 2), "total_inr": sum(r["inr"] for r in rows)}
