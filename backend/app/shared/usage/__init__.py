"""The usage meter: every Gemini call (tokens the provider billed) and every dictation stream (seconds of audio sent),
tagged with the clinic and the job, priced at the rates in app/config.py. Never stops the work it measures."""
import logging
from contextlib import contextmanager
from contextvars import ContextVar

from app import config
from app.shared.db import connect, now, rows

log = logging.getLogger(__name__)
_clinic: ContextVar[int | None] = ContextVar("usage_clinic", default=None)
_job: ContextVar[str] = ContextVar("usage_job", default="other")


@contextmanager
def clinic(clinic_id: int | None):
    """AI calls made inside are counted for this clinic."""
    t = _clinic.set(clinic_id)
    try:
        yield
    finally:
        _clinic.reset(t)


@contextmanager
def job(name: str):
    t = _job.set(name)
    try:
        yield
    finally:
        _job.reset(t)


def ai_cost(model: str, tokens_in: int, tokens_out: int, cached: int = 0) -> int:
    """Millionths of a dollar. Cached input (part of tokens_in) is billed at a tenth of the input price."""
    p_in, p_out = config.AI_PRICES.get(model, config.AI_PRICES.get(config.value("LLM_MODEL"), (0, 0)))
    cached = min(cached, tokens_in)
    return round((tokens_in - cached) * p_in + cached * p_in * config.CACHED_INPUT_SHARE + tokens_out * p_out)


def speech_cost(model: str, seconds: float) -> int:
    return round(seconds / 60 * config.SPEECH_PRICES.get(model, 0) * 1_000_000)


def _add(row: dict) -> None:
    try:
        db = connect()
        try:
            db.execute("""insert into usage_events (clinic_id, kind, job, model, tokens_in, tokens_out, tokens_cached, seconds, cost_micro_usd, at)
                          values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (row["clinic_id"], row["kind"], row["job"], row["model"], row.get("tokens_in", 0), row.get("tokens_out", 0),
                        row.get("tokens_cached", 0), row.get("seconds", 0), row["cost"], now()))
            db.commit()
        finally:
            db.close()
    except Exception:
        log.exception("Usage not recorded")   # the meter must never break a note or a dictation


def record_ai(model: str, tokens_in: int, tokens_out: int, cached: int = 0) -> None:
    _add({"clinic_id": _clinic.get(), "kind": "ai", "job": _job.get(), "model": model, "tokens_in": tokens_in,
          "tokens_out": tokens_out, "tokens_cached": cached, "cost": ai_cost(model, tokens_in, tokens_out, cached)})


def record_speech(clinic_id: int | None, model: str, seconds: float) -> None:
    if seconds > 0:
        _add({"clinic_id": clinic_id, "kind": "speech", "job": "dictation", "model": model,
              "seconds": round(seconds), "cost": speech_cost(model, seconds)})


def report(db, month: str) -> list[dict]:
    """Per clinic for a month (YYYY-MM): visits, AI calls and tokens, dictation minutes, and cost in $ and ₹."""
    start, end = f"{month}-01", f"{month}-31T99"
    rate = config.USD_INR
    clinics = {r["id"]: {"clinic_id": r["id"], "clinic": r["name"], "solo": bool(r["solo"])} for r in rows(db.execute("select id, name, solo from clinics"))}
    out = {}
    for r in rows(db.execute(
            """select clinic_id, kind, job, count(*) as calls, sum(tokens_in) as t_in, sum(tokens_out) as t_out,
                      sum(tokens_cached) as t_cached, sum(seconds) as secs,
                      sum(cost_micro_usd) as cost
               from usage_events where at >= ? and at <= ? group by clinic_id, kind, job""", (start, end))):
        cid, calls, t_in, t_out, secs, cost = r["clinic_id"], r["calls"], r["t_in"] or 0, r["t_out"] or 0, r["secs"] or 0, r["cost"] or 0
        t_cached = r["t_cached"] or 0
        c = out.setdefault(cid, clinics.get(cid, {"clinic_id": cid, "clinic": "(not linked to a clinic)", "solo": False})
                           | {"jobs": {}, "ai_calls": 0, "tokens_in": 0, "tokens_out": 0, "tokens_cached": 0, "dictation_minutes": 0.0, "cost_micro_usd": 0})
        c["jobs"][r["job"]] = {"calls": calls, "tokens_in": t_in, "tokens_out": t_out, "tokens_cached": t_cached,
                               "minutes": round(secs / 60, 1), "usd": round(cost / 1e6, 4)}
        if r["kind"] == "ai":
            c["ai_calls"] += calls; c["tokens_in"] += t_in; c["tokens_out"] += t_out; c["tokens_cached"] += t_cached
        else:
            c["dictation_minutes"] += round(secs / 60, 1)
        c["cost_micro_usd"] += cost
    visits = {r["clinic_id"]: r["n"] for r in rows(db.execute(
        "select clinic_id, count(*) as n from visits where status = 'done' and date >= ? and date <= ? group by clinic_id", (start, end)))}
    result = []
    for cid, c in out.items():
        usd = c.pop("cost_micro_usd") / 1e6
        n = visits.get(cid, 0)
        result.append(c | {"visits": n, "usd": round(usd, 2), "inr": round(usd * rate), "inr_per_visit": round(usd * rate / n, 2) if n else None})
    return sorted(result, key=lambda r: -r["usd"])
