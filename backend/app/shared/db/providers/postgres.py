"""Postgres (Supabase in production); queries keep SQLite's `?` placeholders."""
import re

from ..config import DATABASE_URL


class Row(dict):
    """dict that also answers row[0], like sqlite3.Row."""

    def __getitem__(self, k):
        if isinstance(k, int):
            return list(self.values())[k]
        return super().__getitem__(k)


def _row_factory(cursor):
    if cursor.description is None:
        return lambda values: None
    names = [c.name for c in cursor.description]
    return lambda values: Row(zip(names, values))


class PgCursor:
    def __init__(self, cur, lastrowid=None):
        self.cur, self.lastrowid = cur, lastrowid
        self.rowcount = cur.rowcount

    def fetchone(self):
        return self.cur.fetchone() if self.cur.description else None

    def fetchall(self):
        return self.cur.fetchall() if self.cur.description else []

    def __iter__(self):
        return iter(self.fetchall())


_INSERT = re.compile(r"^\s*insert\s+into\s+(\w+)", re.I)
_NO_ID = {"events", "schema_version", "sessions", "password_resets"}


def to_pg(sql: str) -> str:
    sql = re.sub(r"\bis not \?", "is distinct from ?", sql, flags=re.I)
    sql = sql.replace("%", "%%").replace("?", "%s")
    return sql


class PgDB:
    dialect = "postgres"

    def __init__(self):
        import psycopg
        self.conn = psycopg.connect(DATABASE_URL, row_factory=_row_factory, prepare_threshold=None)

    def execute(self, sql, params=()):
        m = _INSERT.match(sql)
        add_id = bool(m) and " returning " not in sql.lower() and m.group(1) not in _NO_ID
        cur = self.conn.cursor()
        cur.execute(to_pg(sql) + (" returning id" if add_id else ""), tuple(params))
        got = cur.fetchone() if add_id else None   # insert ... select may insert nothing
        lastrowid = got["id"] if got else None
        return PgCursor(cur, lastrowid)

    def script(self, sql):
        with self.conn.cursor() as cur:
            cur.execute(sql)

    def lock(self, key):
        self.conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (str(key),))

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


DB = PgDB
