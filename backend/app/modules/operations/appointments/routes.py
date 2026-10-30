"""Front desk: queues, booking, arrival, reschedule, cancel."""
from fastapi import APIRouter, BackgroundTasks, Depends

from app import brief
from app.shared.auth import current_member, require_screen
from app.shared.db import get_db
from app.core.visit import visit_out
from app.modules.financial.payments.schema import Payment
from app.modules.operations.appointments import service
from app.modules.operations.appointments.schema import Booking, Cancel, Reschedule, WalkIn

router = APIRouter(prefix="/api")
front_desk = require_screen("operations")


@router.get("/operations/day")
def day_view(date: str, me=Depends(front_desk), db=Depends(get_db)):
    return service.day_view(db, me, date)


@router.get("/operations/queue")
def queue(doctor_id: int, date: str, me=Depends(front_desk), db=Depends(get_db)):
    return service.queue(db, me, doctor_id, date)


@router.post("/visits")
def book(body: Booking, me=Depends(front_desk), db=Depends(get_db)):
    return service.book(db, me, body)


@router.post("/visits/walk-in")
def walk_in(body: WalkIn, tasks: BackgroundTasks, me=Depends(front_desk), db=Depends(get_db)):
    vid = service.walk_in(db, me, body)
    db.commit()   # background tasks run before the request's own commit
    tasks.add_task(brief.prebuild, vid)   # ready when the doctor opens the visit
    return visit_out(db, me, vid)


@router.post("/visits/{visit_id}/arrive")
def arrive(visit_id: int, body: Payment, tasks: BackgroundTasks, me=Depends(front_desk), db=Depends(get_db)):
    service.arrive(db, me, visit_id, body)
    db.commit()   # background tasks run before the request's own commit
    tasks.add_task(brief.prebuild, visit_id)
    return visit_out(db, me, visit_id)


@router.post("/visits/{visit_id}/undo-arrival")
def undo_arrival(visit_id: int, body: Cancel, me=Depends(front_desk), db=Depends(get_db)):
    return service.undo_arrival(db, me, visit_id, body)


@router.post("/visits/{visit_id}/queue")
def reorder(visit_id: int, direction: str, me=Depends(front_desk), db=Depends(get_db)):
    return service.reorder(db, me, visit_id, direction)


@router.post("/visits/{visit_id}/late")
def toggle_late(visit_id: int, me=Depends(front_desk), db=Depends(get_db)):
    return service.toggle_late(db, me, visit_id)


@router.post("/visits/{visit_id}/reschedule")
def reschedule(visit_id: int, body: Reschedule, me=Depends(front_desk), db=Depends(get_db)):
    return service.reschedule(db, me, visit_id, body)


@router.post("/visits/{visit_id}/cancel")
def cancel(visit_id: int, body: Cancel, me=Depends(front_desk), db=Depends(get_db)):
    return service.cancel(db, me, visit_id, body)


@router.post("/operations/end-session")
def end_session(doctor_id: int, date: str, session: str | None = None, me=Depends(front_desk), db=Depends(get_db)):
    return service.end_session(db, me, doctor_id, date, session)


@router.get("/doctors")
def list_doctors(me=Depends(current_member), db=Depends(get_db)):
    return service.list_doctors(db, me)
