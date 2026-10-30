"""Patient request bodies."""
from pydantic import BaseModel, Field


class PatientIn(BaseModel):
    name: str = Field(min_length=1)
    dob: str | None = None
    sex: str | None = None
    phone: str = ""
    address: str = ""
    consent: bool = False   # agreed to record keeping


class PatientEdit(BaseModel):
    name: str | None = None
    dob: str | None = None
    sex: str | None = None
    phone: str | None = None
    address: str | None = None


class Merge(BaseModel):
    other_id: int
