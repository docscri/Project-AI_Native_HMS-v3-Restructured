"""Doctor workspace and live dictation."""
import asyncio
import time
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.visit import get_visit
from app.modules.clinical.consultation.service import editable
from app.shared.ai import llm
from app.shared.ai import speech as transcribe
from app.shared.auth import current_member, member_for_token, public_member, require_any, require_screen
from app.shared.db import connect, get_db
from app.shared.errors import DomainError

from . import service
from .schema import FollowUp, FreeText, Segment


router = APIRouter(prefix="/api")


doctor_screen = require_screen("consultation")


@router.get("/consultation/today")
def today(doctor_id: int | None = None, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.today(db, me, doctor_id)


@router.post("/consultation/next")
def call_next(doctor_id: int | None = None, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.call_next(db, me, doctor_id)


@router.post("/visits/{visit_id}/start")
def start(visit_id: int, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.start(db, me, visit_id)


@router.get("/visits/{visit_id}")
def workspace(visit_id: int, me=Depends(require_any("consultation", "patients")), db=Depends(get_db)):
    return service.workspace(db, me, visit_id)


@router.put("/visits/{visit_id}/text")
def save_text(visit_id: int, body: FreeText, me=Depends(doctor_screen), db=Depends(get_db)):
    return service.save_text(db, me, visit_id, body.text, body.rev)


@router.post("/visits/{visit_id}/transcript")
def add_segment(visit_id: int, body: Segment, me=Depends(doctor_screen), db=Depends(get_db)):
    """Legacy append endpoint."""
    return service.add_segment(db, me, visit_id, body.text)


@router.post("/visits/{visit_id}/follow-up")
def follow_up(visit_id: int, body: FollowUp, me=Depends(doctor_screen), db=Depends(get_db)):
    """Waitlists when the day is full."""
    return service.follow_up(db, me, visit_id, body.date)


RECHECK_SECONDS = 5
_active: set[int] = set()   # one live stream per visit (single server process)


@router.get("/dictation")
def provider(me=Depends(current_member)):
    return {"provider": transcribe.name(), "ai": llm.enabled()}


def _check(token: str, visit_id: int) -> str | None:
    """None when this login may dictate into this visit, else the reason."""
    db = connect()
    try:
        m = member_for_token(db, token)
        if not m:
            return "Session ended. Log in again."
        me = public_member(m)
        if "consultation" not in me["screens"]:
            return "No access to Consultation."
        try:
            editable(db, get_visit(db, me, visit_id))
        except (HTTPException, DomainError) as e:
            return getattr(e, "detail", None) or e.message
        db.commit()
        return None
    finally:
        db.close()


@router.websocket("/visits/{visit_id}/dictate")
async def dictate(ws: WebSocket, visit_id: int):
    # The login token comes as a WebSocket subprotocol so it never appears in URLs or logs.
    protocols = [p.strip() for p in ws.headers.get("sec-websocket-protocol", "").split(",")]
    token = protocols[1] if len(protocols) == 2 and protocols[0] == "dictate" else ""
    await ws.accept(subprotocol="dictate" if token else None)

    async def fail(message: str):
        with suppress(Exception):
            await ws.send_json({"type": "error", "message": message})
            await ws.close(code=1008)

    problem = await asyncio.to_thread(_check, token, visit_id)
    if problem:
        return await fail(problem)
    if not transcribe.enabled():
        return await fail("Dictation is not set up.")
    if visit_id in _active:
        return await fail("Already dictating in another window.")
    _active.add(visit_id)
    stream = None
    try:
        async def on_text(event: dict):
            if ws.application_state == WebSocketState.CONNECTED:
                with suppress(Exception):
                    await ws.send_json({"type": "transcript", **event})

        stream = transcribe.open_stream()
        await stream.connect(on_text)
        await ws.send_json({"type": "ready"})
        checked = time.monotonic()
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect" or msg.get("text") == "stop":
                break
            if msg.get("text") == "pause":   # the mic stays open; resume just sends audio again
                if finalize := getattr(stream, "finalize", None):
                    await finalize()
                continue
            if msg.get("bytes"):
                # The login is checked again every few seconds: after logout, a password change or the note being
                # signed, no more audio is sent on.
                if time.monotonic() - checked > RECHECK_SECONDS:
                    if problem := await asyncio.to_thread(_check, token, visit_id):
                        await fail(problem)
                        break
                    checked = time.monotonic()
                await stream.send(msg["bytes"])
    except WebSocketDisconnect:
        pass
    except Exception:
        await fail("Dictation stopped. Try again.")
    finally:
        if stream is not None:
            await asyncio.shield(stream.close())   # last words still reach the browser
        _active.discard(visit_id)
        if ws.application_state == WebSocketState.CONNECTED:
            with suppress(Exception):
                await ws.close()
