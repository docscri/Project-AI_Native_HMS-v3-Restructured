"""Owner signup and finishing setup."""
from fastapi import APIRouter, Depends

from app.shared.auth import current_member, require_admin
from app.shared.db import get_db
from . import service
from .schema import Owner, OwnerEdit

router = APIRouter(prefix="/api/onboarding")


@router.post("/owner")
def create_owner(body: Owner, db=Depends(get_db)):
    return service.create_owner(db, body)


@router.put("/owner")
def edit_owner(body: OwnerEdit, me=Depends(current_member), db=Depends(get_db)):
    return service.edit_owner(db, me, body)


@router.post("/finish")
def finish(me=Depends(require_admin), db=Depends(get_db)):
    return service.finish(db, me)
