"""Waitlist endpoints."""
from fastapi import APIRouter, Depends

from app.shared.auth import require_screen
from app.shared.db import get_db
from app.modules.operations.waitlist import service
from app.modules.operations.waitlist.schema import WaitIn

router = APIRouter(prefix="/api")
front_desk = require_screen("operations")


@router.post("/waitlist")
def join_waitlist(body: WaitIn, me=Depends(front_desk), db=Depends(get_db)):
    return service.join(db, me, body)


@router.get("/waitlist")
def waitlist(doctor_id: int, date: str, me=Depends(front_desk), db=Depends(get_db)):
    return service.waitlist(db, me, doctor_id, date)


@router.post("/waitlist/{wait_id}/book")
def book_from_waitlist(wait_id: int, me=Depends(front_desk), db=Depends(get_db)):
    return service.book(db, me, wait_id)


@router.delete("/waitlist/{wait_id}")
def leave_waitlist(wait_id: int, me=Depends(front_desk), db=Depends(get_db)):
    return service.leave(db, me, wait_id)
