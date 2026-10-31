"""Booking, walk-in, reschedule, cancel and waitlist bodies."""
from pydantic import BaseModel

from app.modules.financial.payments.schema import Payment


class Booking(BaseModel):
    patient_id: int
    doctor_id: int
    date: str
    session: str | None = None   # default: first open session
    token: int | None = None     # default: next free


class WalkIn(Payment):
    patient_id: int
    doctor_id: int
    session: str | None = None


class Reschedule(BaseModel):
    doctor_id: int
    date: str
    session: str | None = None
    token: int | None = None
    reason: str = ""


class Cancel(BaseModel):
    reason: str = ""


class WaitIn(BaseModel):
    patient_id: int
    doctor_id: int
    date: str
    session: str | None = None
