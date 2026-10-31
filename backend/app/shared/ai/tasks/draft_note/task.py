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


FORMS = {"tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule", "capsules", "syrup", "syp", "inj", "injection",
         "drops", "cream", "ointment", "gel", "mg", "ml", "mcg", "sr", "er", "xr", "ds", "forte", "plus"}
NEGATION = re.compile(r"\b(?:no|not|don'?t|do not|never|stop|stopped|discontinue|avoid|without|allergic|allergy|hold|instead of)\b")
# A new phrase starts at punctuation or a joining word, so "Stop metformin, start X" and "stop metformin and start X"
# rule out only metformin. Verbs like "give" don't start one: in "do not give X" the "not" belongs to X.
CLAUSE = re.compile(r"[,;:]|\b(?:and|but|then|instead|also)\b")
SLOT = {"0", "½", "1/2", "0.5", "1", "1½", "1.5", "2"}   # tablets per slot in a 1-0-1 schedule
TIMES = {"once": 1, "daily": 1, "od": 1, "twice": 2, "bd": 2, "bid": 2, "two times": 2, "thrice": 3, "three times": 3,
         "tds": 3, "tid": 3, "four times": 4, "qid": 4}
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def spoken(items: list[dict]) -> list[str]:
    """What was said in this consultation, sentence by sentence, lower case."""
    return [x.lower() for i in items if i["kind"] == "transcript" for x in re.split(r"(?<=[.!?])\s+", i["text"]) if x.strip()]


def prescribed_in(medicine: str, said: list[str]) -> int | None:
    """The sentence where the medicine's own name (not "tab" or a unit) is said without "no", "stop", "allergic"...
    before it in the same phrase; None if it was never said, or only said that way."""
    names = [w for w in re.findall(r"[a-z]{3,}", medicine.lower()) if w not in FORMS]
    for k, s in enumerate(said):
        for w in names:
            for m in re.finditer(rf"\b{re.escape(w)}", s):
                phrase = CLAUSE.split(s[:m.start()])[-1]
                if not NEGATION.search(phrase):
                    return k
    return None


WORDS = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                         "fifteen sixteen seventeen eighteen nineteen twenty".split())} | {"thirty": "30", "a": "1"}
FILLER = {"the", "and", "for", "with", "then", "per", "each", "take", "times", "time", "tablet", "tablets", "tab", "dose", "doses"}


def digits(text: str) -> str:
    """ "for five days" -> "for 5 days", so said numbers in words match numbers written by the AI."""
    return re.sub(r"\b(" + "|".join(WORDS) + r")\b", lambda m: WORDS[m.group(1)], text)


def supported(value: str, where: str, near: str) -> bool:
    """A dose, duration or instruction is kept only if it was said: its numbers and words near the medicine,
    and "1-0-1" only if that many times a day was said in the sentence that prescribes it."""
    if not value.strip():
        return True
    near = digits(near)
    pattern = re.fullmatch(r"\s*([0-9½./]+)-([0-9½./]+)-([0-9½./]+)\s*", value)
    if pattern:
        if pattern.group(0).strip() in near:
            return True   # said exactly as written
        if not set(pattern.groups()) <= SLOT:
            return False  # "10-0-10" is not a tablet schedule anyone said
        per_day = sum(1 for x in pattern.groups() if x != "0")
        said = {TIMES[w] for w in TIMES if re.search(rf"\b{w}\b", where)}
        said = said - {1} if len(said) > 1 else said   # "twice daily" is twice, not also once
        return per_day in said
    words = [w for w in re.findall(r"[a-z]{3,}", value.lower()) if w not in FILLER]
    return (all(n in NUMBER.findall(near) for n in NUMBER.findall(value))
            and all(re.search(rf"\b{re.escape(w.rstrip('s'))}", near) for w in words))


def keep_said(rx: list[dict], items: list[dict]) -> list[dict]:
    """Only medicines the doctor prescribed, at a strength they said; unsupported dose, duration or instructions are
    left blank for the doctor to fill rather than guessed."""
    said, out = spoken(items), []
    for r in rx:
        k = prescribed_in(r["medicine"], said)
        if k is None:
            continue
        near = " ".join(said[k:k + 2])   # the sentence that prescribes it and the one after ("...for five days.")
        if not all(n in NUMBER.findall(near) for n in NUMBER.findall(r["medicine"])):
            continue   # a strength that wasn't said
        out.append({"medicine": r["medicine"]} | {f: r.get(f, "") if supported(r.get(f, ""), said[k], near) else ""
                                                  for f in ("dose", "duration", "instructions")})
    return out


def check(reply: dict, patient: dict, items: list[dict]) -> dict:
    """Citations only to evidence that exists; medicines only as the doctor prescribed them in this consultation."""
    known = {i["id"] for i in items}
    cites = {k: [c for c in reply["citations"].get(k) or [] if c in known] for k in SECTIONS}
    return {"soap": reply["soap"], "rx": keep_said(reply["rx"], items), "citations": cites}


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
    return {"soap": {k: " ".join(v) for k, v in soap.items()}, "rx": keep_said(rx, items), "citations": cites}
