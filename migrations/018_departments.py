"""Doctors' free-text specialities become one of the 12 departments (it fixes their note template)."""
from app.core import departments


def run(db) -> None:
    for r in db.execute("select id, speciality from members where kind = 'doctor'").fetchall():
        db.execute("update members set speciality = ? where id = ?", (departments.match(r[1]), r[0]))
