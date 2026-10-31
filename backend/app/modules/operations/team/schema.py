"""Team request bodies."""
from pydantic import BaseModel, Field


class Mark(BaseModel):
    status: str = Field(pattern="^(present|late|absent|half|clear)$")
    check_in: str | None = None    # HH:MM
    note: str = ""


class LeaveIn(BaseModel):
    start_date: str
    end_date: str
    type: str = Field(default="casual", pattern="^(casual|sick|earned|other)$")
    reason: str = ""
    member_id: int | None = None     # admins only
