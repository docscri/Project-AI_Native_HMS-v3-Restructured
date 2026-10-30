from fastapi import APIRouter, Depends

from app.shared.auth import require_screen
from app.shared.db import get_db
from . import service

router = APIRouter(prefix="/api")
doctor_screen = require_screen("consultation")


@router.post("/visits/{visit_id}/brief")
def make_brief(visit_id: int, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.make(db, me, visit_id)
