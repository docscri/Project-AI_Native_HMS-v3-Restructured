"""Departments and their OPD case-sheet templates (from "Department Specific OPD Case Sheet Templates", v1.0, 9 Oct 2026).

A doctor's department is stored in members.speciality as one of the labels below; it fixes their note template."""
import re

from app.shared.errors import Invalid

from .templates import COMMON, RULES, TEMPLATES, VERSION

DEPARTMENTS = [t["label"] for t in TEMPLATES]
_BY_LABEL = {t["label"].lower(): t for t in TEMPLATES}

# Free text typed before departments were a list ("General medicine", "Paeds", "Eye") -> a department.
_MATCH = [(r"emergenc|casualty|\ber\b", "Emergency Medicine"), (r"obst|antenatal|\banc\b", "Obstetrics"),
          (r"gyn", "Gynaecology"), (r"paed|pediat|child", "Paediatrics"), (r"ortho|bone", "Orthopaedics"),
          (r"\bent\b|ear|nose|throat|otolaryng", "ENT"), (r"ophth|\beye", "Ophthalmology"), (r"derm|skin", "Dermatology"),
          (r"psych", "Psychiatry"), (r"\buro", "Urology"), (r"surg", "General Surgery")]


def canonical(text: str | None) -> str | None:
    """The department label for a choice from the list (any letter case); None if it isn't one."""
    t = _BY_LABEL.get((text or "").strip().lower())
    return t["label"] if t else None


def match(text: str | None) -> str:
    """Best department for old free-text specialities; General Medicine when nothing fits."""
    low = (text or "").lower()
    return canonical(text) or next((label for rx, label in _MATCH if re.search(rx, low)), "General Medicine")


def template(label: str | None) -> dict:
    """The case-sheet template for a department (General Medicine when unknown), with the shared header."""
    t = _BY_LABEL.get((label or "").strip().lower()) or _BY_LABEL["general medicine"]
    return {"version": VERSION, "department": t["label"], "title": t["title"], "header": COMMON,
            "sections": t["sections"], "note": t.get("note", ""), "rules": RULES}


def chosen(text: str | None, keep: str | None = None) -> str:
    """The department a form sent, checked against the list; empty keeps the current one (or General Medicine)."""
    if not (text or "").strip():
        return canonical(keep) or match(keep)
    label = canonical(text)
    if not label:
        raise Invalid("Choose a department from the list.")
    return label


VITALS = ["BP", "Pulse", "RR", "Temp", "SpO2", "Weight", "Height"]


def letter(title: str) -> str:
    """Which of S/O/A/P a template section feeds, so briefs, charts and past-visit lines keep working."""
    t = title.lower()
    if t.startswith("o/e") or "risk assessment" in t or "available" in t or "bedside" in t:
        return "O"
    if any(w in t for w in ("diagnos", "impression", "assessment", "formulation")):
        return "A"
    if "management" in t:
        return "P"
    return "S"


def sections_for(label: str | None) -> list[dict]:
    """The doctor's template as empty note sections: key, title and the prompts the AI follows."""
    return [{"key": str(i + 1), "title": s["title"], "prompts": s["prompts"], "text": ""} for i, s in enumerate(template(label)["sections"])]


def soap_of(sections: list[dict], vitals: dict | None = None) -> dict:
    """The S/O/A/P summary of a department-format note (vitals lead O, unless the text already gives them)."""
    soap = {k: [] for k in "SOAP"}
    written = " ".join(s.get("text") or "" for s in sections).replace(" ", "")
    v = "; ".join(f"{k} {x}" for k, x in (vitals or {}).items() if str(x).strip() and str(x).replace(" ", "") not in written)
    if v:
        soap["O"].append(v + ".")
    for s in sections:
        if (s.get("text") or "").strip():
            soap[letter(s["title"])].append(s["text"].strip())
    return {k: " ".join(v) for k, v in soap.items()}
