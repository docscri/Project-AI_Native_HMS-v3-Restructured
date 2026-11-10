from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.visit import get_visit
from app.modules.clinical.brief import service as brief
from app.shared.auth import require_screen
from app.shared.db import get_db
from . import service
from .schema import LocationIn, QuickVisit, SoloIn

router = APIRouter(prefix="/api")
doctor_screen = require_screen("consultation")


@router.post("/onboarding/solo")
def sign_up(body: SoloIn, db=Depends(get_db)):
    return service.sign_up(db, body)


@router.get("/locations")
def locations(me=Depends(doctor_screen), db=Depends(get_db)):
    return service.locations(db, me)


@router.post("/locations")
def add_location(body: LocationIn, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.add_location(db, me, body.name)


@router.delete("/locations/{location_id}")
def remove_location(location_id: int, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.remove_location(db, me, location_id)


@router.post("/visits/quick")
def quick_visit(body: QuickVisit, tasks: BackgroundTasks, me=Depends(doctor_screen), db=Depends(get_db)):
    vid = service.quick_visit(db, me, body.patient_id, body.location_id)
    db.commit()   # background tasks run before the request's own commit
    tasks.add_task(brief.prebuild, vid)   # the history brief, ready by the time the doctor looks
    return get_visit(db, me, vid)
