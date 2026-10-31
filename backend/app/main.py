import hashlib
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.shared import db, errors
from app.modules.clinical.brief import routes as brief
from app.modules.clinical.consultation import routes as consultation
from app.modules.clinical.documents import routes as documents
from app.modules.clinical.notes import routes as notes
from app.modules.financial.reports import routes as reports
from app.modules.financial.payments import routes as payments
from app.modules.operations.account import routes as account
from app.modules.operations.administration import routes as administration
from app.modules.operations.appointments import routes as appointments
from app.modules.operations.patients import routes as patients
from app.modules.operations.scheduling import routes as scheduling
from app.modules.operations.team import routes as team

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.check()
    db.init()
    yield


app = FastAPI(title="Dictate", lifespan=lifespan)


errors.install(app)
ROUTERS = (account, administration, scheduling, patients, appointments, payments,
           consultation, brief, documents, notes, team, reports)
for r in ROUTERS:
    app.include_router(r.router)


@app.get("/health")
def health():
    return {"ok": True}


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


def page() -> str:
    """Cache-bust assets by content hash."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    tag = lambda m: f'/static/{m[1]}?v={hashlib.sha1((FRONTEND / m[1]).read_bytes()).hexdigest()[:10]}"'
    return re.sub(r'/static/([\w./-]+\.(?:js|css))"', tag, html)


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found.")
    return HTMLResponse(page(), headers={"Cache-Control": "no-cache"})
