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
