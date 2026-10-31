import html
import json

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.core.patient import age
from app.shared import printing as printpage
from app.shared.auth import require_any, require_screen
from app.shared.db import get_db
from . import service
from .schema import AddendumIn, NoteEdit

router = APIRouter(prefix="/api")
doctor_screen = require_screen("consultation")


@router.post("/visits/{visit_id}/note/draft")
def draft(visit_id: int, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.draft(db, me, visit_id)


@router.post("/visits/{visit_id}/note")
def blank_note(visit_id: int, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.blank(db, me, visit_id)


@router.put("/notes/{note_id}")
def edit_note(note_id: int, body: NoteEdit, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.edit(db, me, note_id, body.soap, body.rx)


@router.post("/notes/{note_id}/sign")
def sign(note_id: int, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.sign(db, me, note_id)


@router.post("/notes/{note_id}/addenda")
def add_addendum(note_id: int, body: AddendumIn, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.add_addendum(db, me, note_id, body.text)


@router.get("/notes/{note_id}/print", response_class=HTMLResponse)
def print_note(note_id: int, auto: int = 0, me=Depends(require_any("consultation", "patients")), db=Depends(get_db)):
    """Fetched by the app with the login header and written into a new tab, so the token never sits in a URL."""
    n = service.get(db, note_id)
    if not n or n["clinic_id"] != me["clinic_id"]:
        return HTMLResponse(printpage.message("Note not found", "It may have been removed."), 404)
    c, v, p, d = service.print_parts(db, me, n)

    content, e = json.loads(n["content"]), html.escape
    labels = {"S": "Subjective", "O": "Objective", "A": "Assessment", "P": "Plan"}
    soap = "".join(f'<div class="sec"><b class="tile">{k}</b><div><small>{labels[k]}</small><p>{e(t)}</p></div></div>'
                   for k, t in content["soap"].items() if t and k in labels)
    rx = [r for r in content["rx"] if r.get("medicine")]
    rx_html = ("<h2>Prescription</h2><table><tr><th>Medicine</th><th>Dose</th><th>Duration</th><th>Instructions</th></tr>" + "".join(
        f"<tr><td><b>{e(r.get('medicine', ''))}</b></td><td>{e(r.get('dose', ''))}</td><td>{e(r.get('duration', ''))}</td><td>{e(r.get('instructions', ''))}</td></tr>"
        for r in rx) + "</table>") if rx else ""
    adds = service.addenda(db, n["id"])
    addenda_html = ("<h2>Addenda</h2>" + "".join(
        f'<div class="add"><small>{printpage.stamp(x["signed_at"])} · {e(x["signed_by_name"])}</small><p>{e(x["text"])}</p></div>' for x in adds)) if adds else ""
    sex = {"M": "Male", "F": "Female", "O": "Other"}.get(p["sex"] or "", "")
    who = " · ".join(x for x in [f"{age(p['dob'])} yrs" if p["dob"] else "", sex, p["uhid"]] if x)
    signed = f"Signed by {e(n['signed_by_name'] or d['name'])} · {printpage.stamp(n['signed_at'])}" if n["signed_at"] else "Draft · not signed"
    body = f"""<header><div><h1>{e(c['name'])}</h1><small>{e(' · '.join(x for x in [c['address'], c['phone']] if x))}</small></div>
<div class="r"><b>{e(p['name'])}</b><small>{e(who)}</small><small><span class="lime">{printpage.day(v['date'])}</span> · {e(d['name'])}{' · ' + e(d['speciality']) if d['speciality'] else ''}</small></div></header>
<div class="secs">{soap or '<p>—</p>'}</div>{rx_html}{addenda_html}
<footer><div class="s">{signed}</div><div class="sign">Doctor's signature</div></footer>"""
    note_css = ("<style>.secs{display:flex;flex-direction:column;gap:20px;margin:30px 0 8px}.sec{display:grid;grid-template-columns:28px 1fr;gap:12px;align-items:start}"
                ".tile{width:28px;height:28px;border-radius:8px;background:#0B1411;color:#E8F1EC;display:grid;place-items:center;font-size:12px;font-weight:800}"
                ".sec small{display:block;font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#6B7C75;margin-top:2px}"
                ".sec p{margin:4px 0 0;font-size:15.5px;line-height:1.65;font-weight:500}"
                ".add{border-left:3px solid #B6F36B;padding:4px 0 4px 14px;margin:10px 0}.add small{font-size:11px;font-weight:700;color:#6B7C75}"
                ".add p{margin:4px 0 0;font-size:15px;line-height:1.6;white-space:pre-wrap}</style>")
    return printpage.page(f"{p['name']} · {printpage.day(v['date'])}", note_css + body, auto=bool(auto))
