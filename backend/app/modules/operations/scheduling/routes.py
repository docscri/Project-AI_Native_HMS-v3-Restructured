"""Clinic hours with per-day overrides."""
from fastapi import APIRouter, Depends

from app.shared.auth import current_member
from app.shared.db import get_db
from app.modules.operations.scheduling import service
from app.modules.operations.scheduling.schema import Leave, Override

router = APIRouter(prefix="/api")


@router.get("/schedules/{doctor_id}")
def month(doctor_id: int, month: str, me=Depends(current_member), db=Depends(get_db)):
    return service.month(db, me, doctor_id, month)


@router.put("/schedules/{doctor_id}/{date}")
def set_day(doctor_id: int, date: str, body: Override, me=Depends(current_member), db=Depends(get_db)):
    return service.set_day(db, me, doctor_id, date, body)


@router.post("/schedules/leave")
def leave(body: Leave, me=Depends(current_member), db=Depends(get_db)):
    return service.leave(db, me, body)


@router.delete("/schedules/{doctor_id}/{date}")
def reset_day(doctor_id: int, date: str, me=Depends(current_member), db=Depends(get_db)):
    return service.reset_day(db, me, doctor_id, date)


@router.get("/availability")
def get_availability(doctor_id: int, date: str, exclude_visit: int | None = None, session: str | None = None,
                     me=Depends(current_member), db=Depends(get_db)):
    return service.get_availability(db, me, doctor_id, date, exclude_visit, session)
