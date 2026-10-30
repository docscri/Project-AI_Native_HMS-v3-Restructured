import hashlib
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.shared import db, errors
from app.routes import clinic, consultation, dictation, patients
from app.modules.financial.collections import routes as collections
from app.modules.financial.day_close import day_close
from app.modules.financial.payments import routes as payments
from app.modules.operations.appointments import routes as appointments
from app.modules.operations.scheduling import routes as scheduling
from app.modules.operations.team.attendance import routes as attendance
from app.modules.operations.team.leave import routes as leave
from app.modules.operations.waitlist import routes as waitlist

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="Clinic V1")


errors.install(app)
for r in (clinic, scheduling, patients, appointments, payments, waitlist, consultation, dictation, attendance, leave, collections, day_close):
    app.include_router(r.router)


@app.on_event("startup")
def startup() -> None:
    db.init()
    if os.environ.get("SEED_DEMO", "0") == "1":
        from app.demo.seed import seed
        seed()


@app.get("/health")
def health():
    return {"ok": True}


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


def page() -> str:
    """Cache-bust assets by content hash."""
    html = (FRONTEND / "index.html").read_text()
    tag = lambda m: f'/static/{m[1]}?v={hashlib.sha1((FRONTEND / m[1]).read_bytes()).hexdigest()[:10]}"'
    return re.sub(r'/static/([\w./-]+\.(?:js|css))"', tag, html)


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found.")
    return HTMLResponse(page(), headers={"Cache-Control": "no-cache"})
