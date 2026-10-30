"""Schedule request bodies."""
from pydantic import BaseModel, Field


class Session(BaseModel):
    start: str
    end: str


class Override(BaseModel):
    is_off: bool = False
    sessions: list[Session] = []
    start: str | None = None      # legacy single-session form
    end: str | None = None
    limit_by: str | None = Field(default=None, pattern="^(patients|minutes)$")
    limit_value: int | None = Field(default=None, ge=1)


class Leave(BaseModel):
    start_date: str
    end_date: str
    doctor_id: int | None = None   # None = clinic holiday
    off: bool = True               # False = restore normal hours
