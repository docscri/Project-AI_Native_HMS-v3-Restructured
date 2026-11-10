from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.shared.auth import current_member
from app.shared.db import get_db
from . import service

router = APIRouter(prefix="/api")


@router.put("/me/signature")
async def save(file: UploadFile = File(...), me=Depends(current_member), db=Depends(get_db)):
    return service.save(db, me, await file.read(service.MAX + 1))


@router.delete("/me/signature")
def remove(me=Depends(current_member), db=Depends(get_db)):
    return service.remove(db, me)


@router.get("/signatures/{signature_id}")
def image(signature_id: int, me=Depends(current_member), db=Depends(get_db)):
    """Only with the login header, only within the clinic; never cached."""
    return Response(service.image(db, me, signature_id), media_type="image/png", headers={"Cache-Control": "private, no-store"})
