"""Account request bodies."""
from pydantic import BaseModel, Field


class Login(BaseModel):
    email: str
    password: str


class ChangePassword(BaseModel):
    current: str
    new: str


class Forgot(BaseModel):
    email: str


class Reset(BaseModel):
    code: str
    password: str


class MyProfile(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str
    phone: str = ""
    speciality: str = ""
    designation: str = ""


class Owner(BaseModel):
    name: str = Field(min_length=1)
    email: str
    phone: str = ""
    password: str
    is_doctor: bool = True
    speciality: str = "General Medicine"


class OwnerEdit(BaseModel):
    name: str = Field(min_length=1)
    email: str
    phone: str = ""
    password: str = ""            # empty = keep the current one
    speciality: str = ""          # department; empty = keep the current one
    is_doctor: bool = True
