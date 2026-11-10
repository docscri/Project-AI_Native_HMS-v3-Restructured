from pydantic import BaseModel, Field


class SoloIn(BaseModel):
    name: str = Field(min_length=1)
    email: str
    phone: str = ""
    password: str
    speciality: str = "General Medicine"


class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class QuickVisit(BaseModel):
    patient_id: int
    location_id: int | None = None
