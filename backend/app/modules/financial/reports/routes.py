"""Reports URLs: collections and day close."""
from fastapi import APIRouter, Depends

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
