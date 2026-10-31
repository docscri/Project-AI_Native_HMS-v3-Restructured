"""Reports request bodies."""
from pydantic import BaseModel, Field


class Close(BaseModel):
    date: str
    counted_cash: int = Field(ge=0)
    note: str = ""
