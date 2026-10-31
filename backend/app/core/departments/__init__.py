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
