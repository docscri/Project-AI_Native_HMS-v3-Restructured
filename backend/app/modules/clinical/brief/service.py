"""Pre-visit brief: summary, visit events and charts. Every line cites a signed-note section or a document."""
import json
import logging
import re
from datetime import date

from app.core.visit import get_visit
from app.shared.ai import llm, tasks
from app.shared.ai.tasks.brief_summary import task as brief_summary
from app.shared.ai.tasks.checks import grounded
from app.shared.ai.tasks.note_values import task as note_values_task
from app.shared.ai.tasks.visit_lines import task as visit_lines
from app.shared.db import connect, now
from . import repo

log = logging.getLogger(__name__)

SECTIONS = {"S": "Subjective", "O": "Objective", "A": "Assessment", "P": "Plan"}
ALIASES = {"hba1c": "HbA1c", "glycatedhb": "HbA1c", "glycatedhaemoglobin": "HbA1c", "glycatedhemoglobin": "HbA1c",
           "fbs": "Fasting sugar", "fastingsugar": "Fasting sugar", "fastingbloodsugar": "Fasting sugar", "fastingglucose": "Fasting sugar",
           "rbs": "Random sugar", "randomsugar": "Random sugar", "randombloodsugar": "Random sugar", "randomglucose": "Random sugar",
           "bp": "BP", "bloodpressure": "BP", "temp": "Temperature", "temperature": "Temperature", "spo2": "SpO2",
           "pulse": "Pulse", "hr": "Pulse", "heartrate": "Pulse", "weight": "Weight", "wt": "Weight",
           "creatinine": "Creatinine", "serumcreatinine": "Creatinine"}


# Usual adult ranges, used only to mark values; a value is marked only when its unit matches.
RANGES = {"HbA1c": (4.0, 5.6, "%"), "Fasting sugar": (70, 99, "mg/dl"), "Random sugar": (70, 139, "mg/dl"),
          "Creatinine": (0.6, 1.3, "mg/dl"), "BP systolic": (90, 139, "mmhg"), "BP diastolic": (60, 89, "mmhg"),
          "Pulse": (60, 100, "/min"), "SpO2": (95, 100, "%"), "Temperature": (97, 99.5, "°f")}


def note_values(soap: dict) -> list[dict]:
    """[{"test", "value", "unit", "section"}] read from a signed note; each value must appear in its section."""
    return tasks.run(note_values_task, soap=soap)


def name_of(test) -> str:
    return ALIASES.get(re.sub(r"[^a-z0-9]", "", str(test).lower()), str(test).strip())


def outside(name: str, unit: str, value) -> bool:
    r = RANGES.get(name)
    try:
        v = float(str(value).replace(",", ""))
    except ValueError:
        return False
    return bool(r) and (unit or "").replace(" ", "").lower() in (r[2], "") and not r[0] <= v <= r[1]


def lab_range(text) -> list | None:
    """The report's printed range as [low, high]; a side is None for "< 200" or "> 40". None if unreadable."""
    t = str(text or "").replace(",", "").strip()
    if m := re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*\S*", t):
        return [float(m[1]), float(m[2])]
    if m := re.fullmatch(r"(?:<|≤|<=|up to|upto)\s*(\d+(?:\.\d+)?)\s*\S*", t, re.I):
        return [None, float(m[1])]
    if m := re.fullmatch(r"(?:>|≥|>=)\s*(\d+(?:\.\d+)?)\s*\S*", t):
        return [float(m[1]), None]
    return None


def lab_says(f: dict) -> bool | None:
    """The lab's own verdict on a value: its printed flag first, then its printed range. None if it gives neither."""
    flag = str(f.get("flag") or "").strip().lower()
    if flag in ("h", "l", "high", "low", "*", "**", "↑", "↓", "abnormal"):
        return True
    r = lab_range(f.get("range"))
    try:
        v = float(str(f.get("value")).replace(",", ""))
    except ValueError:
        return None
    if r is None:
        return None
    return (r[0] is not None and v < r[0]) or (r[1] is not None and v > r[1])


def is_out(f: dict) -> bool:
    """Report's flag, then report's range, then the built-in usual range."""
    said = lab_says(f)
    return said if said is not None else outside(name_of(f.get("name") or f.get("test")), f.get("unit") or "", f.get("value"))


def abnormal_values(f: dict) -> list[str]:
    """The value text(s) of a finding that sit outside the range."""
    name, unit, value = name_of(f.get("name") or f.get("test")), f.get("unit") or "", str(f.get("value") or "").replace(" ", "")
    if name == "BP" and "/" in value:
        sys_, dia = value.split("/", 1)
        return [value] if outside("BP systolic", unit, sys_) or outside("BP diastolic", unit, dia) else []
    return [value] if is_out(f) else []


def title_of(d: dict) -> str:
    return (d["extracted"] or {}).get("title") or d["filename"].rsplit(".", 1)[0]


def nice(d: str) -> str:
    x = date.fromisoformat(d[:10])
    return f"{x.day} {x.strftime('%b %Y')}"


def inputs(db, v: dict) -> tuple[list[dict], list[dict]]:
    """The patient's other signed notes (newest first) and documents that finished reading, read or not."""
    return repo.signed_notes(db, v["patient_id"], v["id"]), repo.finished_documents(db, v["patient_id"])


def basis(notes: list[dict], docs: list[dict]) -> str:
    """Changes when a note is signed, a report is read or a brief prompt changes version; the saved brief is reused until then."""
    return ("n" + ",".join(str(n["id"]) + "+" * len(n.get("addenda") or []) for n in notes) + ";d" + ",".join(str(d["id"]) + ("x" if d["ai_status"] == "failed" else "") for d in docs)
            + (";ai:" + ",".join(tasks.version(t) for t in (brief_summary, visit_lines)) if llm.enabled() else ""))


def current_basis(db, v: dict) -> str:
    return basis(*inputs(db, v))


def values_of(db, n: dict) -> list[dict]:
    """Numbers in a signed note, read once and saved; read again when the note_values prompt changes version."""
    saved, current = json.loads(n["vals"]) if n.get("vals") else None, tasks.version(note_values_task)
    if not isinstance(saved, dict) or saved.get("version") != current:
        saved = {"version": current, "values": note_values(n["content"]["soap"])}
        n["vals"] = json.dumps(saved)
        repo.save_values(db, n["id"], n["vals"])
    return saved["values"]


def with_flags(lines: list[dict], sources: dict) -> list[dict]:
    """Marks values outside the usual range inside each sentence ("flags")."""
    for s in lines:
        s["flags"] = list(dict.fromkeys(x for c in s["cites"] for f in sources[c].get("values", []) for x in abnormal_values(f)
                                        if x in s["text"].replace(" ", "")))
    return lines


def checked(items, sources: dict) -> list[dict]:
    """Sentences their sources support (see tasks.checks.grounded), with out-of-range values flagged."""
    return with_flags(grounded([i for i in items or [] if isinstance(i, dict)], sources), sources)


def charts(notes: list[dict], docs: list[dict], db) -> list[dict]:
    points = {}   # (test, unit) -> {date: point}; a report beats a note on the same day
    def add(test, unit, value, day, cite, from_doc, f=None):
        name = name_of(test)
        unit = str(unit or "").strip()
        value = str(value).replace(" ", "").replace(",", "")
        if name == "BP" and "/" in value:
            sys_, dia = value.split("/", 1)
            add("BP systolic", unit or "mmHg", sys_, day, cite, from_doc)
            add("BP diastolic", unit or "mmHg", dia, day, cite, from_doc)
            return
        if not re.fullmatch(r"\d+(?:\.\d+)?", value) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day or ""):
            return
        series = points.setdefault((name, unit), {})
        if from_doc or day not in series or not series[day]["doc"]:
            said = lab_says(f) if f else None
            series[day] = {"date": day, "value": float(value), "text": value, "cite": cite, "doc": from_doc,
                           "out": said if said is not None else outside(name, unit, value), "lab": lab_range(f.get("range")) if f else None}
    for d in docs:
        for f in d["extracted"].get("findings") or []:
            add(f.get("name"), f.get("unit"), f.get("value"), (f.get("date") or d["created_at"])[:10], f"D{d['id']}", True, f)
    for n in notes:
        for f in values_of(db, n):
            add(f["test"], f.get("unit"), f["value"], n["date"], f"N{n['id']}.{f['section']}", False)
    out, bp = [], {}
    for (name, unit), series in points.items():
        ordered = sorted(series.values(), key=lambda p: p["date"])
        pts = [{k: p[k] for k in ("date", "value", "text", "cite", "out")} for p in ordered]
        lab = next((p["lab"] for p in reversed(ordered) if p["lab"]), None)   # the latest report's printed range wins
        usual = list(RANGES[name][:2]) if name in RANGES and unit.replace(" ", "").lower() in (RANGES[name][2], "") else None
        ser = {"name": name, "points": pts, "range": lab or usual, "range_from": "report" if lab else "usual" if usual else None}
        if name.startswith("BP "):
            bp[name] = ser | {"name": name.split()[1].title()}
        else:
            out.append({"test": name, "unit": unit, "series": [ser]})
    if bp:
        out.append({"test": "BP", "unit": "mmHg", "series": [bp[k] for k in ("BP systolic", "BP diastolic") if k in bp]})
    latest = lambda c: max(p["date"] for s_ in c["series"] for p in s_["points"])
    return sorted(out, key=lambda c: (latest(c), sum(len(s_["points"]) for s_ in c["series"])), reverse=True)


def build(db, v: dict) -> dict:
    notes, finished = inputs(db, v)
    docs, unread = [d for d in finished if d["ai_status"] == "ready"], [d for d in finished if d["ai_status"] == "failed"]
    p = repo.patient(db, v["patient_id"])
    sources = {}
    for n in notes:
        for k, label in SECTIONS.items():
            body = (n["content"]["soap"].get(k) or "").strip()
            if body:
                sources[f"N{n['id']}.{k}"] = {"kind": "note", "visit_id": n["vid"], "date": n["date"], "doctor": n["doctor"], "section": label,
                                              "body": body, "text": f"{n['date']} {nice(n['date'])} {body}",
                                              "values": [f for f in values_of(db, n) if f["section"] == k]}
    last_signed = max((n["signed_at"] or "" for n in notes), default="")
    new_ids = []
    for d in docs:
        ex, made = d["extracted"], d["created_at"][:10]
        vals = ", ".join(f'{f.get("name")} {f.get("value")} {f.get("unit") or ""}'.strip() for f in ex.get("findings") or [])
        sources[f"D{d['id']}"] = {"kind": "document", "doc_id": d["id"], "filename": d["filename"], "date": made, "label": title_of(d),
                                  "summary": ex.get("summary") or "", "findings": ex.get("findings") or [], "values": ex.get("findings") or [],
                                  "text": f"{made} {nice(made)} {title_of(d)} {ex.get('summary') or ''} {vals}"}
        if d["created_at"].replace(" ", "T") >= last_signed:   # older rows were stamped "YYYY-MM-DD HH:MM:SS"
            new_ids.append(f"D{d['id']}")
    for d in unread:   # named in the Sources panel with a Try again button; never sent to the AI
        made = d["created_at"][:10]
        sources[f"D{d['id']}"] = {"kind": "document", "doc_id": d["id"], "filename": d["filename"], "date": made, "label": title_of(d),
                                  "summary": "Couldn't be read.", "findings": [], "values": [], "failed": True,
                                  "text": f"{made} {nice(made)} {title_of(d)} {d['filename']}"}
    visits = [{"note": f"N{n['id']}", "date_text": nice(n["date"])} for n in notes]
    patient = {"age": None if not p or not p["dob"] else date.today().year - int(p["dob"][:4]), "sex": p["sex"] if p else None}
    readable = {k: s for k, s in sources.items() if not s.get("failed")}
    summary = tasks.run(brief_summary, patient=patient, sources=readable, new_ids=new_ids, visits=visits)
    new = with_flags(summary["new"], readable) + [{"text": f"{d['filename']}: couldn't be read.", "cites": [f"D{d['id']}"], "flags": []}
                                                  for d in unread if d["created_at"].replace(" ", "T") >= last_signed]
    lines = tasks.run(visit_lines, patient=patient, sources=readable, notes=[v["note"] for v in visits])
    events = []
    for n in notes:
        line = lines[f"N{n['id']}"]
        own_docs = [{"id": d["id"], "filename": d["filename"], "title": title_of(d)} for d in docs if d["visit_id"] == n["vid"]]
        events.append({"visit_id": n["vid"], "date": n["date"], "doctor": n["doctor"], "text": line["text"],
                       "cites": line["cites"] + [f"D{d['id']}" for d in own_docs], "documents": own_docs,
                       "addenda": n.get("addenda") or []})   # signed corrections, shown as written
    return {"summary": [{"kind": "new", "sentences": new}] * bool(new) + [{"kind": "history", "sentences": with_flags(summary["history"], readable)}],
            "events": events, "charts": charts(notes, docs, db), "sources": sources, "basis": basis(notes, finished)}


def make(db, me, visit_id: int) -> dict:
    """Builds and saves the brief now."""
    v = get_visit(db, me, visit_id)
    b = build(db, v) | {"made_at": now()}
    repo.save_brief(db, visit_id, json.dumps(b))
    return b


def prebuild(visit_id: int) -> None:
    """Builds the brief in the background when a patient arrives or a report is read, so it's ready when the doctor opens it."""
    db = connect()
    try:
        v = repo.visit(db, visit_id)
        if not v or v["status"] not in ("waiting", "with_doctor"):
            return
        saved = json.loads(v["brief"]) if v["brief"] else None
        if saved and saved.get("basis") == current_basis(db, v):
            return
        repo.save_brief(db, visit_id, json.dumps(build(db, v) | {"made_at": now()}))
        db.commit()
    except Exception:
        log.exception("Brief prebuild failed for visit %s", visit_id)
    finally:
        db.close()

