"""Doctor workspace."""
from fastapi import APIRouter, Depends

from app.shared.auth import require_any, require_screen
from app.shared.db import get_db
from . import service
from .schema import FollowUp, FreeText, Segment

router = APIRouter(prefix="/api")
doctor_screen = require_screen("consultation")


@router.get("/consultation/today")
def today(doctor_id: int | None = None, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.today(db, me, doctor_id)


@router.post("/consultation/next")
def call_next(doctor_id: int | None = None, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.call_next(db, me, doctor_id)


@router.post("/visits/{visit_id}/start")
def start(visit_id: int, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.start(db, me, visit_id)


@router.get("/visits/{visit_id}")
def workspace(visit_id: int, me=Depends(require_any("consultation", "patients")), db=Depends(get_db)):
    return service.workspace(db, me, visit_id)


@router.put("/visits/{visit_id}/text")
def save_text(visit_id: int, body: FreeText, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.save_text(db, me, visit_id, body.text, body.rev)


@router.post("/visits/{visit_id}/transcript")
def add_segment(visit_id: int, body: Segment, me=Depends(doctor_screen), db=Depends(get_db)):
    """Legacy append endpoint."""
    return service.add_segment(db, me, visit_id, body.text)


@router.post("/visits/{visit_id}/follow-up")
def follow_up(visit_id: int, body: FollowUp, me=Depends(doctor_screen), db=Depends(get_db)):
    """Waitlists when the day is full."""
    return service.follow_up(db, me, visit_id, body.date)
