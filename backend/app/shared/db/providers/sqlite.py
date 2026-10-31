"""SQLite: local runs, tests and the free trial."""
import sqlite3

from ..config import DATA_DIR, DB_PATH


def _sqlite() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    conn.execute("pragma journal_mode = wal")
    return conn


class SqliteDB:
    dialect = "sqlite"

    def __init__(self):
        self.conn = _sqlite()

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def script(self, sql):
        self.conn.executescript(sql)

    def lock(self, key):
        # Take the write lock up front so following reads are race free.
        if not self.conn.in_transaction:
            self.conn.execute("begin immediate")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
