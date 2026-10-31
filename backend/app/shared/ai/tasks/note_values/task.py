"""Lists the measured numbers in a signed note (BP, pulse, HbA1c...), for the brief's charts."""
import re

from pydantic import field_validator

from app.shared.ai import tasks
from app.shared.ai.tasks.models import Shape, as_text

NAME = "note_values"

VITALS = [("BP", "mmHg", r"\b(?:BP|blood pressure)\D{0,6}(\d{2,3}\s*/\s*\d{2,3})"),
          ("Temperature", "°F", r"\btemp(?:erature)?\D{0,6}(\d{2,3}(?:\.\d)?)"),
          ("Pulse", "/min", r"\b(?:pulse|PR|HR|heart rate)\D{0,6}(\d{2,3})"),
          ("SpO2", "%", r"\bSpO2\D{0,6}(\d{2,3})"),
          ("Weight", "kg", r"\b(?:weight|wt)\D{0,6}(\d{2,3}(?:\.\d)?)"),
          ("HbA1c", "%", r"\bHbA1c\D{0,6}(\d{1,2}(?:\.\d)?)"),
          ("Fasting sugar", "mg/dL", r"\b(?:FBS|fasting (?:blood )?(?:sugar|glucose))\D{0,6}(\d{2,3})"),
          ("Random sugar", "mg/dL", r"\b(?:RBS|random (?:blood )?(?:sugar|glucose))\D{0,6}(\d{2,3})")]


class Value(Shape):
    test: str
    value: str
    unit: str = ""
    section: str

    _text = field_validator("test", "value", "unit", "section", mode="before")(lambda v: as_text(v))


class Reply(Shape):
    values: list[Value] = []


def parts(soap: dict) -> list[dict]:
    return [{"text": tasks.fill(__file__, note=soap)}]


def written_in(found: list[dict], soap: dict) -> list[dict]:
    """Only values that really appear in the section they're said to come from."""
    return [f for f in found if f["section"] in soap and f["value"].replace(" ", "") in (soap.get(f["section"]) or "").replace(" ", "")]


def check(reply: dict, soap: dict) -> list[dict]:
    return written_in(reply["values"], soap)


def fallback(soap: dict) -> list[dict]:
    """Without the AI: the usual vitals and sugar values, by pattern."""
    found = [{"test": t, "value": m.group(1).replace(" ", ""), "unit": u, "section": k}
             for k in ("O", "S", "A", "P") for t, u, rx in VITALS for m in re.finditer(rx, soap.get(k) or "", re.I)]
    return written_in(found, soap)
