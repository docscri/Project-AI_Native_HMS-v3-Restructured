"""One line per past visit for the brief's event cards: why the patient came and what was found."""
from app.shared.ai import tasks
from app.shared.ai.tasks.checks import grounded
from app.shared.ai.tasks.models import Shape
from app.shared.text import sentences

NAME = "visit_lines"


class Event(Shape):
    note: str
    text: str
    cites: list[str] = []


class Reply(Shape):
    events: list[Event] = []


def wants_ai(patient: dict, sources: dict, notes: list[str]) -> bool:
    return bool(notes)   # a first visit has no past visits to describe


def parts(patient: dict, sources: dict, notes: list[str]) -> list[dict]:
    listing = [{"id": k, "text": s["text"]} for k, s in sources.items() if k.split(".")[0] in notes]
    return [{"text": tasks.fill(__file__, patient=patient, visits=notes, sources=listing)}]


def plain(sources: dict, nid: str) -> dict:
    """The note's own words: the first sentence of why they came (S) and of what was found (A), and any signed
    correction (X) after them, so a withdrawn assessment never stands alone."""
    got = [(f"{nid}.{k}", (sentences(sources[f"{nid}.{k}"]["body"]) or [""])[0]) for k in ("S", "A") if f"{nid}.{k}" in sources]
    if f"{nid}.X" in sources:
        got.append((f"{nid}.X", "Corrected later: " + sources[f"{nid}.X"]["body"]))
    return {"text": " ".join(t for _, t in got if t), "cites": [c for c, t in got if t]}


def check(reply: dict, patient: dict, sources: dict, notes: list[str]) -> dict:
    """{note id: line}; a line must cite only its own visit's sections, else that visit gets its plain line."""
    lines = {}
    for e in reply["events"]:
        if e["note"] in notes and e["note"] not in lines:
            got = grounded([e], sources, allowed=lambda c, n=e["note"]: c.startswith(n + "."))
            if got:
                lines[e["note"]] = got[0]
    return {n: lines.get(n) or plain(sources, n) for n in notes}


def fallback(patient: dict, sources: dict, notes: list[str]) -> dict:
    return {n: plain(sources, n) for n in notes}
