"""Drafts the SOAP note and prescription from this consultation's words, with reports and earlier notes as evidence."""
import re

from pydantic import field_validator

from app.shared.ai import tasks
from app.shared.ai.tasks.models import Shape, as_text

NAME = "draft_note"
SECTIONS = ("S", "O", "A", "P")

MED = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+syrup)?)\s+(\d+(?:\.\d+)?\s*(?:mg|ml|mcg|g))\b", re.I)
FREQ = re.compile(r"\b(once|twice|three times|thrice|four times)\s+(?:a\s+day|daily)|\b\d-\d-\d\b|\bevery\s+\d+\s+hours\b", re.I)
DURATION = re.compile(r"\bfor\s+(\d+\s+(?:days?|weeks?|months?))", re.I)


class Soap(Shape):
    S: str = ""
    O: str = ""
    A: str = ""
    P: str = ""

    _text = field_validator(*SECTIONS, mode="before")(lambda v: as_text(v))


class Rx(Shape):
    medicine: str
    dose: str = ""
    duration: str = ""
    instructions: str = ""

    _text = field_validator("medicine", "dose", "duration", "instructions", mode="before")(lambda v: as_text(v))


class Reply(Shape):
    soap: Soap = Soap()
    rx: list[Rx] = []
    citations: dict[str, list[str]] = {}


def parts(patient: dict, items: list[dict]) -> list[dict]:
    return [{"text": tasks.fill(__file__, patient=patient, evidence=items)}]


def said(items: list[dict]) -> str:
    return " ".join(i["text"] for i in items if i["kind"] == "transcript").lower()


FORMS = {"tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule", "capsules", "syrup", "syp", "inj", "injection",
         "drops", "cream", "ointment", "gel", "mg", "ml", "mcg", "sr", "er", "xr", "ds", "forte", "plus"}


def was_said(medicine: str, words: str) -> bool:
    """The medicine's own name (not "tab", "syrup" or a unit) appears in what was said."""
    names = [w for w in re.findall(r"[a-z]{3,}", medicine.lower()) if w not in FORMS]
    return bool(names) and any(re.search(rf"\b{re.escape(w)}", words) for w in names)


def check(reply: dict, patient: dict, items: list[dict]) -> dict:
    """Citations only to evidence that exists; medicines only if the doctor said them in this consultation."""
    known, words = {i["id"] for i in items}, said(items)
    rx = [r for r in reply["rx"] if was_said(r["medicine"], words)]
    cites = {k: [c for c in reply["citations"].get(k) or [] if c in known] for k in SECTIONS}
    return {"soap": reply["soap"], "rx": rx, "citations": cites}


def fallback(patient: dict, items: list[dict]) -> dict:
    """Without the AI: each sentence said in the consultation sorted into S, O, A or P by its words; medicines by pattern."""
    soap, cites, rx = {k: [] for k in SECTIONS}, {k: [] for k in SECTIONS}, []
    for i in items:
        if i["kind"] != "transcript":
            continue
        for text in [x for x in re.split(r"(?<=[.!?])\s+", i["text"]) if x.strip()]:
            low = text.lower()
            if any(w in low for w in ("likely", "looks like", "diagnos", "this is", "suggest")):
                k = "A"
            elif re.search(r"\d", low) and any(w in low for w in ("bp", "temp", "weight", "pulse", "report", "hba1c", "sugar", "spo2", "°")):
                k = "O"
            elif any(w in low for w in ("mg", "ml", "tablet", "syrup", "review", "come back", "follow", "advice", "walk", "drink", "test")):
                k = "P"
            else:
                k = "O" if re.search(r"\d", low) else "S"
            soap[k].append(text.rstrip(".") + ".")
            if i["id"] not in cites[k]:
                cites[k].append(i["id"])
            for m in MED.finditer(text):
                freq, dur = FREQ.search(text), DURATION.search(text)
                rx.append({"medicine": f"{m.group(1).title()} {m.group(2)}", "dose": freq.group(0) if freq else "as advised",
                           "duration": dur.group(1) if dur else "", "instructions": ""})
    return {"soap": {k: " ".join(v) for k, v in soap.items()}, "rx": rx, "citations": cites}
