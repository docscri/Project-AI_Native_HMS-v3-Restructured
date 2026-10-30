"""Postgres when DATABASE_URL is set, else SQLite; queries use `?` placeholders.

    db.execute(sql, params) -> cursor with fetchone/fetchall/rowcount/lastrowid
    db.lock(key)            -> serialise writes that allocate numbers (tokens, UHIDs, receipts)
"""
from datetime import datetime

from .config import DATA_DIR, DATABASE_URL, DB_PATH, UPLOAD_DIR, is_postgres
from .providers.postgres import PgDB
from .providers.sqlite import SqliteDB


def connect():
    return PgDB() if is_postgres() else SqliteDB()


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
