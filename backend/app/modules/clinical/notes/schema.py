from pydantic import BaseModel


class NoteEdit(BaseModel):
    soap: dict[str, str]
    rx: list[dict]


class AddendumIn(BaseModel):
    text: str
