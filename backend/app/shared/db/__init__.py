"""Database chosen by DATABASE in app/config.py (providers/<name>.py); queries use `?` placeholders.

    db.execute(sql, params) -> cursor with fetchone/fetchall/rowcount/lastrowid
    db.lock(key)            -> serialise writes that allocate numbers (tokens, UHIDs, receipts)
"""
from datetime import datetime

from app import config as app_config
from .config import DATA_DIR, DATABASE_URL, DB_PATH, UPLOAD_DIR


def connect():
    return app_config.provider("DATABASE").DB()


def get_db():
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def row(r) -> dict | None:
    return dict(r) if r else None


def rows(rs) -> list[dict]:
    return [dict(r) for r in rs]


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init() -> None:
    from .migrate import migrate
    migrate()
