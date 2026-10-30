"""Leave URLs."""
from fastapi import APIRouter, Depends

from app.shared.auth import current_member
from app.shared.db import get_db
from . import service
from .schema import LeaveIn

router = APIRouter(prefix="/api")


@router.post("/leave")
def request_leave(body: LeaveIn, me=Depends(current_member), db=Depends(get_db)):
    return service.request_leave(db, me, body)


@router.get("/leave")
def list_leave(month: str | None = None, mine: bool = False, me=Depends(current_member), db=Depends(get_db)):
    return service.list_leave(db, me, month, mine)


@router.post("/leave/{leave_id}/{action}")
def decide(leave_id: int, action: str, me=Depends(current_member), db=Depends(get_db)):
    return service.decide(db, me, leave_id, action)
