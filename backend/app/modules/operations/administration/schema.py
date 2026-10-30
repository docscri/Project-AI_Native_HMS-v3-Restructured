"""Administration request bodies."""
from pydantic import BaseModel, Field


class Details(BaseModel):
    name: str = Field(min_length=1)
    phone: str = ""
    address: str = ""


class SessionTime(BaseModel):
    start: str
    end: str


class Rules(BaseModel):
    fee: int = Field(ge=0, le=100000)
    days: list[int]
    sessions: list[SessionTime] = []
    start: str | None = None    # older single-session form
    end: str | None = None
    limit_by: str = Field(pattern="^(patients|minutes)$")
    limit_value: int = Field(ge=1, le=500)
    token_timing: str = Field(pattern="^(booking|arrival)$")


class NewMember(BaseModel):
    kind: str = Field(pattern="^(doctor|staff)$")
    name: str = Field(min_length=1)
    email: str
    phone: str = ""
    speciality: str | None = None
    designation: str | None = None
    fee_override: int | None = None
    screens: list[str] = []
    is_admin: bool = False


class ResetEmail(BaseModel):
    code: str


class MemberUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    kind: str | None = Field(default=None, pattern="^(doctor|staff)$")
    speciality: str | None = None
    designation: str | None = None
    fee_override: int | None = None
    clear_fee: bool = False
    screens: list[str] | None = None
    is_admin: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")
    joined_on: str | None = Field(default=None, pattern=r"^(\d{4}-\d{2}-\d{2})?$")
    emergency_contact: str | None = None
    address: str | None = None
    id_number: str | None = None
    work_days: list[int] | None = None
    work_start: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    work_end: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class Accept(BaseModel):
    code: str
    password: str
