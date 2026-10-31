"""Reads an uploaded PDF or photo: its title, a short summary and the values printed in it."""
import base64
import re

from pydantic import field_validator

from app.shared.ai import tasks
from app.shared.ai.tasks.models import Shape, as_text

NAME = "read_report"


class Finding(Shape):
    name: str
    value: str
    unit: str = ""
    range: str = ""
    flag: str = ""
    date: str = ""

    _text = field_validator("name", "value", "unit", "range", "flag", "date", mode="before")(lambda v: as_text(v))


class Reply(Shape):
    title: str = ""
    summary: str = ""
    findings: list[Finding] = []


def wants_ai(data: bytes, mime: str, filename: str) -> bool:
    """Text files are read directly; PDFs and photos need the AI."""
    return (mime or "").split("/")[0] in ("image", "application")


def parts(data: bytes, mime: str, filename: str) -> list[dict]:
    return [{"text": tasks.fill(__file__)},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}]


def check(reply: dict, data: bytes, mime: str, filename: str) -> dict:
    reply["findings"] = [f for f in reply["findings"] if f["name"].strip() and f["value"].strip()]
    return reply


def fallback(data: bytes, mime: str, filename: str) -> dict:
    """Without the AI: a text file's first line and "name value unit" pairs; anything else is just named."""
    text = data.decode(errors="ignore")[:4000] if (mime or "").startswith("text") else ""
    head = next((x.strip() for x in text.splitlines() if x.strip()), "")
    findings = [{"name": n.strip(), "value": v, "unit": u.strip()}
                for n, v, u in re.findall(r"([A-Za-z][A-Za-z0-9 ]{1,20})[:\s]+(\d+(?:\.\d+)?)\s*([a-zA-Z/%]*)", text)][:10]
    return {"summary": text[:300] or f"Uploaded document: {filename}", "findings": findings,
            "title": head if 0 < len(head) <= 60 and not re.search(r"\d", head) else ""}
