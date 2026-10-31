"""The brief's Summary: a paragraph on new reports, then one on the patient's history. Every sentence cites its sources."""
from app.shared.ai import tasks
from app.shared.ai.tasks.checks import grounded
from app.shared.ai.tasks.models import Line, Shape
from app.shared.text import sentences

NAME = "brief_summary"


class Reply(Shape):
    new: list[Line] = []
    history: list[Line] = []


def wants_ai(patient: dict, sources: dict, new_ids: list[str], visits: list[dict]) -> bool:
    return bool(sources)   # nothing to summarise: no call


def parts(patient: dict, sources: dict, new_ids: list[str], visits: list[dict]) -> list[dict]:
    listing = [{"id": k, "text": s["text"]} for k, s in sources.items()]
    return [{"text": tasks.fill(__file__, patient=patient, new_documents=new_ids, sources=listing)}]


def first(text: str) -> str:
    return (sentences(text) or [""])[0]


def report_line(sources: dict, d: str) -> dict:
    """A new report in plain words: its title, the first sentence of its summary and its first values."""
    s = sources[d]
    lead = first(s["summary"]) if first(s["summary"]).lower().startswith(s["label"].lower()) else f"{s['label']}: {first(s['summary'])}"
    vals = ", ".join(f'{f.get("name")} {f.get("value")} {f.get("unit") or ""}'.strip() for f in s["findings"][:6])
    return {"text": lead + (f" {vals}." if vals else ""), "cites": [d]}


def check(reply: dict, patient: dict, sources: dict, new_ids: list[str], visits: list[dict]) -> dict:
    new = grounded(reply["new"], sources, allowed=lambda c: c in new_ids)
    missing = [d for d in new_ids if not any(d in s["cites"] for s in new)]
    new += grounded([report_line(sources, d) for d in missing], sources)   # every new report keeps a line
    return {"new": new, "history": grounded(reply["history"], sources)}


def fallback(patient: dict, sources: dict, new_ids: list[str], visits: list[dict]) -> dict:
    """Without the AI: each new report in plain words, then each past assessment once, citing every visit it came from."""
    seen = {}
    for v in visits:
        a = v["note"] + ".A"
        if a in sources:
            seen.setdefault(first(sources[a]["body"]), []).append(a)
    history = [{"text": t, "cites": cites} for t, cites in list(seen.items())[:4]]
    return {"new": grounded([report_line(sources, d) for d in new_ids], sources), "history": grounded(history, sources)}
