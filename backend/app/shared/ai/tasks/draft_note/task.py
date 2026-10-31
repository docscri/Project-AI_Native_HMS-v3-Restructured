"""Drafts the note in the doctor's department format (sections, vitals, prescription) from this consultation's words,
with reports and earlier notes as evidence."""
import re

from pydantic import field_validator

from app.core import departments
from app.shared.ai import tasks
from app.shared.ai.tasks.models import Shape, as_text
from app.shared.ai.tasks.note_values import task as note_values   # the same vitals patterns the charts use

NAME = "draft_note"
SECTIONS = ("S", "O", "A", "P")

MED = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+syrup)?)\s+(\d+(?:\.\d+)?\s*(?:mg|ml|mcg|g))\b", re.I)
FREQ = re.compile(r"\b(once|twice|three times|thrice|four times)\s+(?:a\s+day|daily)|\b\d-\d-\d\b|\bevery\s+\d+\s+hours\b", re.I)
DURATION = re.compile(r"\bfor\s+(\d+\s+(?:days?|weeks?|months?))", re.I)

FORMS = {"tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule", "capsules", "syrup", "syp", "inj", "injection",
         "drops", "cream", "ointment", "gel", "mg", "ml", "mcg", "sr", "er", "xr", "ds", "forte", "plus"}
NEGATION = re.compile(r"\b(?:no|not|don'?t|do not|never|stop|stopped|discontinue|avoid|without|allergic|allergy|hold|instead of)\b")
# A new phrase starts at punctuation or a joining word, so "Stop metformin, start X" and "stop metformin and start X"
# rule out only metformin. Verbs like "give" don't start one: in "do not give X" the "not" belongs to X.
CLAUSE = re.compile(r"[,;:]|\b(?:and|but|then|instead|also)\b")
SLOT = {"0", "½", "1/2", "0.5", "1", "1½", "1.5", "2"}   # tablets per slot in a 1-0-1 schedule
TIMES = {"once": 1, "daily": 1, "od": 1, "twice": 2, "bd": 2, "bid": 2, "two times": 2, "thrice": 3, "three times": 3,
         "tds": 3, "tid": 3, "four times": 4, "qid": 4, "at night": 1, "at bedtime": 1, "hs": 1, "in the morning": 1}
NUMBER = re.compile(r"\d+(?:\.\d+)?")


class Rx(Shape):
    medicine: str
    dose: str = ""
    duration: str = ""
    instructions: str = ""

    _text = field_validator("medicine", "dose", "duration", "instructions", mode="before")(lambda v: as_text(v))


class Reply(Shape):
    sections: dict[str, str] = {}
    vitals: dict[str, str] = {}
    rx: list[Rx] = []
    citations: dict[str, list[str]] = {}

    @field_validator("sections", "vitals", mode="before")
    @classmethod
    def _texts(cls, v):
        return {str(k): as_text(x) for k, x in (v or {}).items()} if isinstance(v, dict) else v


def parts(patient: dict, items: list[dict], sheet: dict | None = None) -> list[dict]:
    sheet = sheet or departments.template(None)
    template = [{"key": str(i + 1), "title": s["title"], "prompts": s["prompts"]} for i, s in enumerate(sheet["sections"])]
    return [{"text": tasks.fill(__file__, patient=patient, evidence=items, template=template,
                                rules="\n".join("- " + r for r in sheet["rules"]), note=sheet.get("note") or "none")}]


def spoken(items: list[dict]) -> list[str]:
    """What was said in this consultation, sentence by sentence, lower case."""
    return [x.lower() for i in items if i["kind"] == "transcript" for x in re.split(r"(?<=[.!?])\s+", i["text"]) if x.strip()]


def names_of(medicine: str) -> list[str]:
    """A medicine's own name words, without "tab", "syrup" or units."""
    return [w for w in re.findall(r"[a-z]{3,}", medicine.lower()) if w not in FORMS]


def instruction(medicine: str, said: list[str], others: set[str]) -> str | None:
    """The words that prescribe this medicine: its phrase up to the name ("give one tablet of ..."), said without "no",
    "stop", "allergic"..., then on to where the next medicine starts in that sentence, plus the next sentence when it
    names no other medicine ("...Continue for five days."). None if it was never prescribed."""
    def next_drug(s: str, after: int) -> int:
        starts = [m.start() for w in others for m in re.finditer(rf"\b{re.escape(w)}", s) if m.start() >= after]
        starts += [m.start() for m in MED.finditer(s) if m.start() >= after]
        return min(starts, default=len(s))
    for k, s in enumerate(said):
        for w in names_of(medicine):
            for m in re.finditer(rf"\b{re.escape(w)}", s):
                lead = CLAUSE.split(s[:m.start()])[-1]
                if NEGATION.search(lead):
                    continue
                end = next_drug(s, m.end())
                text = lead + s[m.start():end]
                if end == len(s) and k + 1 < len(said) and next_drug(said[k + 1], 0) == len(said[k + 1]):
                    text += " " + said[k + 1]
                return text
    return None


WORDS = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                         "fifteen sixteen seventeen eighteen nineteen twenty".split())} | {"thirty": "30", "a": "1"}
FILLER = {"the", "and", "for", "with", "then", "per", "each", "take", "times", "time", "tablet", "tablets", "tab", "dose", "doses"}


def digits(text: str) -> str:
    """ "for five days" -> "for 5 days", so said numbers in words match numbers written by the AI."""
    return re.sub(r"\b(" + "|".join(WORDS) + r")\b", lambda m: WORDS[m.group(1)], text)


COUNT = re.compile(r"\b(half|½|1/2|0\.5|one and a half|1½|1\.5|one|two|1|2)\s+(?:tab|tablet|tablets|cap|capsule|capsules|tsp|teaspoon|teaspoons|puff|puffs)\b")
AMOUNT = {"half": 0.5, "½": 0.5, "1/2": 0.5, "0.5": 0.5, "one and a half": 1.5, "1½": 1.5, "1.5": 1.5, "one": 1, "1": 1, "two": 2, "2": 2}


def supported(value: str, said: str) -> bool:
    """A dose, duration or instruction is kept only if this medicine's own instruction says it: its numbers and words,
    and for "1-0-1" both how many times a day and, when said, how many tablets each time."""
    if not value.strip():
        return True
    words_said, said = said, digits(said)   # times a day and tablet counts read from the words, numbers from digits
    pattern = re.fullmatch(r"\s*([0-9½./]+)-([0-9½./]+)-([0-9½./]+)\s*", value)
    if pattern:
        if pattern.group(0).strip() in said:
            return True   # said exactly as written
        if not set(pattern.groups()) <= SLOT:
            return False  # "10-0-10" is not a tablet schedule anyone said
        slots = [AMOUNT.get(x, 0) for x in pattern.groups() if x != "0"]
        times = {TIMES[w] for w in TIMES if re.search(rf"\b{w}\b", words_said)}
        times = times - {1} if len(times) > 1 else times   # "twice daily" is twice, not also once
        count = COUNT.search(words_said)
        return len(slots) in times and (not count or all(x == AMOUNT[count.group(1)] for x in slots))
    words = [w for w in re.findall(r"[a-z]{3,}", value.lower()) if w not in FILLER]
    return (all(n in NUMBER.findall(said) for n in NUMBER.findall(value))
            and all(re.search(rf"\b{re.escape(w.rstrip('s'))}", said) for w in words))


STRENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|units?|%)(?![a-z])")
NOT_STRENGTH = r"\s*(?:days?|weeks?|months?|years?|times?|hours?|hrs?|x|tabs?|tablets?|doses?)\b"


def strength_said(medicine: str, said: str) -> bool:
    """Each strength in the medicine was said as a strength of it: "500 mg" as "500 mg" (not the 7 of "for 7 days");
    a number without a unit only where it isn't a count of days, times or tablets."""
    said, med = digits(said), medicine.lower()
    for n, unit in STRENGTH.findall(med):
        if not re.search(rf"(?<![\d.]){re.escape(n)}\s*{re.escape(unit)}(?![a-z])", said):
            return False
    for n in NUMBER.findall(STRENGTH.sub(" ", med)):
        if not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])(?!{NOT_STRENGTH})", said):
            return False
    return True


def keep_said(rx: list[dict], items: list[dict]) -> list[dict]:
    """Only medicines the doctor prescribed, at the strength said for that medicine; a dose, duration or instruction
    not said for it is left blank for the doctor to fill rather than guessed."""
    said, out = spoken(items), []
    for r in rx:
        others = {w for o in rx for w in names_of(o["medicine"])} - set(names_of(r["medicine"]))
        text = instruction(r["medicine"], said, others)
        if text is None:
            continue
        if not strength_said(r["medicine"], text):
            continue   # a strength that wasn't said for this medicine
        out.append({"medicine": r["medicine"]} | {f: r.get(f, "") if supported(r.get(f, ""), text) else ""
                                                  for f in ("dose", "duration", "instructions")})
    return out


def shaped(sheet: dict, texts: dict, cites: dict, vitals: dict, rx: list, items: list[dict]) -> dict:
    """The saved note: the department's sections in order, vitals, prescription, citations and the S/O/A/P summary."""
    known = {i["id"] for i in items}
    sections = [{"key": str(i + 1), "title": s["title"], "text": (texts.get(str(i + 1)) or "").strip()} for i, s in enumerate(sheet["sections"])]
    cites = {x["key"]: [c for c in cites.get(x["key"]) or [] if c in known] for x in sections}
    return {"template": {"department": sheet["department"], "version": sheet["version"]}, "sections": sections,
            "vitals": vitals, "rx": rx, "citations": cites, "soap": departments.soap_of(sections, vitals)}


def stated_vitals(vitals: dict, items: list[dict]) -> dict:
    """Only vitals whose numbers were said in this consultation."""
    words = " ".join(spoken(items))
    out = {}
    for k in departments.VITALS:
        v = (vitals.get(k) or "").strip()
        if v and NUMBER.findall(v) and all(n in NUMBER.findall(words) for n in NUMBER.findall(v)):
            out[k] = v
    return out


def check(reply: dict, patient: dict, items: list[dict], sheet: dict | None = None) -> dict:
    """Citations only to evidence that exists; vitals only as said; medicines only as the doctor prescribed them."""
    sheet = sheet or departments.template(None)
    return shaped(sheet, reply["sections"], reply["citations"], stated_vitals(reply["vitals"], items),
                  keep_said(reply["rx"], items), items)


PLAIN_VITALS = {"BP": "BP", "Pulse": "Pulse", "Temperature": "Temp", "SpO2": "SpO2", "Weight": "Weight"}


def into_sections(sheet: dict, soap: dict, cites: dict | None = None) -> tuple[dict, dict]:
    """S/O/A/P text (and its citations) placed in the first section of the department's format that feeds each letter."""
    first = {}
    for i, s in enumerate(sheet["sections"]):
        first.setdefault(departments.letter(s["title"]), str(i + 1))
    texts, keyed = {}, {}
    for k in SECTIONS:
        key = first.get(k) or "1"
        if (soap.get(k) or "").strip():
            texts[key] = (texts.get(key, "") + " " + str(soap[k]).strip()).strip()
        for c in (cites or {}).get(k) or []:
            keyed.setdefault(key, [])
            if c not in keyed[key]:
                keyed[key].append(c)
    return texts, keyed


def fallback(patient: dict, items: list[dict], sheet: dict | None = None) -> dict:
    """Without the AI: each sentence said sorted into S, O, A or P by its words and put in the first section of the
    department's format that feeds that letter; vitals and medicines by pattern."""
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
    sheet = sheet or departments.template(None)
    texts, keyed = into_sections(sheet, {k: " ".join(v) for k, v in soap.items()}, cites)
    said = " ".join(spoken(items))
    vitals = {PLAIN_VITALS[f["test"]]: f["value"] for f in note_values.fallback({"O": said}) if f["test"] in PLAIN_VITALS}
    return shaped(sheet, texts, keyed, vitals, keep_said(rx, items), items)
