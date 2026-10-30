from pydantic import BaseModel, Field


class LeaveIn(BaseModel):
    start_date: str
    end_date: str
    type: str = Field(default="casual", pattern="^(casual|sick|earned|other)$")
    reason: str = ""
    member_id: int | None = None     # admins only
