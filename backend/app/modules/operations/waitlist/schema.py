"""Waitlist body."""
from pydantic import BaseModel


class WaitIn(BaseModel):
    patient_id: int
    doctor_id: int
    date: str
    session: str | None = None
