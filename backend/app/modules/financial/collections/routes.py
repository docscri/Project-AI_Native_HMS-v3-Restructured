"""Collections URL."""
from fastapi import APIRouter, Depends

from app.shared.auth import require_admin
from app.shared.db import get_db
from . import service

router = APIRouter(prefix="/api")


@router.get("/collections")
def collections(start: str, end: str | None = None, doctor_id: int | None = None, me=Depends(require_admin), db=Depends(get_db)):
    return service.collections(db, me, start, end, doctor_id)
