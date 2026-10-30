"""Patients."""
from fastapi import APIRouter, Depends

from app.shared.auth import require_any, require_screen
from app.shared.db import get_db
from . import service
from .schema import Merge, PatientEdit, PatientIn

router = APIRouter(prefix="/api/patients")


@router.get("/check")
def check(name: str = "", phone: str = "", dob: str | None = None, me=Depends(require_any("operations", "patients", "consultation")), db=Depends(get_db)):
    return service.check(db, me, name, phone, dob)


@router.post("")
def register(body: PatientIn, me=Depends(require_any("operations", "patients", "consultation")), db=Depends(get_db)):
    return service.register(db, me, body)


@router.get("")
def search(q: str = "", me=Depends(require_any("operations", "patients", "consultation")), db=Depends(get_db)):
    return service.search(db, me, q)


@router.get("/{patient_id}")
def profile(patient_id: int, me=Depends(require_screen("patients")), db=Depends(get_db)):
    return service.profile(db, me, patient_id)


@router.patch("/{patient_id}")
def edit(patient_id: int, body: PatientEdit, me=Depends(require_any("operations", "patients")), db=Depends(get_db)):
    return service.edit(db, me, patient_id, body)


@router.post("/{patient_id}/merge")
def merge(patient_id: int, body: Merge, me=Depends(require_screen("patients")), db=Depends(get_db)):
    return service.merge(db, me, patient_id, body.other_id)
