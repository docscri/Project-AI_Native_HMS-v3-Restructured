"""Day close: system cash against counted cash."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.modules.financial.collections import service as collections
from app.shared.audit import log_event
from app.shared.auth import require_admin
from app.shared.db import get_db, now, row, rows
from app.shared.validate import valid_day

router = APIRouter(prefix="/api")
CLOSES = "select c.*, m.name as closed_by_name from day_close c left join members m on m.id = c.closed_by where c.clinic_id = ?"


class Close(BaseModel):
    date: str
    counted_cash: int = Field(ge=0)
    note: str = ""


def summary(db, me, date: str) -> dict:
    t = collections.collections(db, me, date, date, None)
    cash = t["by_method"]["cash"] - t["refunded"]   # refunds are handed back in cash
    closed = row(db.execute(CLOSES + " and c.date = ?", (me["clinic_id"], date)).fetchone())
    past = rows(db.execute(CLOSES + " order by c.date desc limit 14", (me["clinic_id"],)))
    return {"date": date, "system_cash": cash, "closed": closed, "past": past}


def close(db, me, body: Close) -> dict:
    body.date = valid_day(body.date)
    sys_cash = summary(db, me, body.date)["system_cash"]
    db.execute(
        """insert into day_close (clinic_id, date, system_cash, counted_cash, note, closed_by, closed_at) values (?, ?, ?, ?, ?, ?, ?)
           on conflict (clinic_id, date) do update set system_cash = excluded.system_cash, counted_cash = excluded.counted_cash,
             note = excluded.note, closed_by = excluded.closed_by, closed_at = excluded.closed_at""",
        (me["clinic_id"], body.date, sys_cash, body.counted_cash, body.note.strip(), me["id"], now()))
    log_event(db, me["clinic_id"], me["id"], "clinic", me["clinic_id"], "day_closed", {"date": body.date, "difference": body.counted_cash - sys_cash})
    return summary(db, me, body.date)


@router.get("/day-close")
def day_close(date: str, me=Depends(require_admin), db=Depends(get_db)):
    return summary(db, me, date)


@router.post("/day-close")
def close_day(body: Close, me=Depends(require_admin), db=Depends(get_db)):
    return close(db, me, body)
