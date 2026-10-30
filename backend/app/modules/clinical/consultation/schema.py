from pydantic import BaseModel, Field


class FreeText(BaseModel):
    text: str = Field(max_length=100_000)
    rev: int   # stale versions are refused


class Segment(BaseModel):
    speaker: str = "Doctor"
    text: str


class FollowUp(BaseModel):
    date: str
