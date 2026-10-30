from pydantic import BaseModel, Field


class Mark(BaseModel):
    status: str = Field(pattern="^(present|late|absent|half|clear)$")
    check_in: str | None = None    # HH:MM
    note: str = ""
