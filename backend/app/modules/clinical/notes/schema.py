from pydantic import BaseModel


class NoteEdit(BaseModel):
    soap: dict[str, str] | None = None        # notes written before the department formats
    sections: dict[str, str] | list[dict] | None = None   # department format: key -> text, or the saved [{key, title, text}]
    vitals: dict[str, str] | None = None
    rx: list[dict]


class AddendumIn(BaseModel):
    text: str
