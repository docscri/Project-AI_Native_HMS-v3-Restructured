"""Onboarding request bodies."""
from pydantic import BaseModel, Field


class Owner(BaseModel):
    name: str = Field(min_length=1)
    email: str
    phone: str = ""
    password: str
    is_doctor: bool = True
    speciality: str = "General medicine"


class OwnerEdit(BaseModel):
    name: str = Field(min_length=1)
    email: str
    phone: str = ""
    password: str = ""            # empty = keep the current one
    is_doctor: bool = True
