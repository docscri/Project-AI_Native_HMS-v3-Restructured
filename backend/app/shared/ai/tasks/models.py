"""Reply pieces shared by several tasks. Unknown fields are ignored; numbers sent as numbers become text."""
from pydantic import BaseModel, ConfigDict


class Shape(BaseModel):
    model_config = ConfigDict(extra="ignore")


def as_text(v):
    """The AI sometimes sends 7.2 rather than "7.2", or null for an empty field."""
    return "" if v is None else str(v) if isinstance(v, (int, float)) else v


class Line(Shape):
    text: str
    cites: list[str] = []
