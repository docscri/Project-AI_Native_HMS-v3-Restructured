"""Team URLs: attendance, the register and leave."""
from fastapi import APIRouter, Depends

from app.shared.auth import current_member, require_admin
from app.shared.db import get_db

from . import service
from .schema import LeaveIn, Mark


router = APIRouter(prefix="/api")


@router.get("/team/today")
def team_today(date: str | None = None, me=Depends(require_admin), db=Depends(get_db)):
    return service.team_today(db, me, date)


@router.get("/attendance/me")
def my_attendance(me=Depends(current_member), db=Depends(get_db)):
    return service.my_attendance(db, me)


@router.post("/attendance/check-in")
def check_in(me=Depends(current_member), db=Depends(get_db)):
    return service.check_in(db, me)


@router.post("/attendance/check-out")
def check_out(me=Depends(current_member), db=Depends(get_db)):
    return service.check_out(db, me)


@router.put("/attendance/{member_id}/{date}")
def mark(member_id: int, date: str, body: Mark, me=Depends(require_admin), db=Depends(get_db)):
    return service.mark(db, me, member_id, date, body)


@router.get("/team/register")
def register(month: str, member_id: int | None = None, me=Depends(current_member), db=Depends(get_db)):
    return service.register(db, me, month, member_id)


@router.post("/leave")
def request_leave(body: LeaveIn, me=Depends(current_member), db=Depends(get_db)):
    return service.request_leave(db, me, body)


@router.get("/leave")
def list_leave(month: str | None = None, mine: bool = False, me=Depends(current_member), db=Depends(get_db)):
    return service.list_leave(db, me, month, mine)


@router.post("/leave/{leave_id}/{action}")
def decide(leave_id: int, action: str, me=Depends(current_member), db=Depends(get_db)):
    return service.decide(db, me, leave_id, action)
