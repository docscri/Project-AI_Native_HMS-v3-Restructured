"""The state machines in app/shared/states.py: in step with the database, the docs, and the code, and enforced."""
import re
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.shared.states import MACHINES, markdown
from tests.helpers import clinic, join, member

ROOT = Path(__file__).resolve().parents[1]
SQL = "\n".join(p.read_text() for p in sorted((ROOT / "migrations").glob("*.sql")))


def test_machines_match_the_database_checks():
    for m in MACHINES.values():
        table = re.search(rf"create table if not exists {m.table} \((.*?)\n\);", SQL, re.S)
        assert table, m.table
        check = re.search(rf"{m.column} text not null[^\n]*check \({m.column} in \(([^)]*)\)\)", table.group(1))
        assert check, (m.table, m.column)
        assert set(re.findall(r"'([a-z_]+)'", check.group(1))) == m.states, m.table
        assert set(m.start) <= m.states


def test_docs_are_generated_from_the_machines():
    assert (ROOT / "docs" / "STATES.md").read_text() == markdown(), "run: cd backend && python -m app.shared.states > ../docs/STATES.md"


def test_no_status_written_by_hand():
    """Status changes go through a Machine; plain `set status = '...'` SQL would skip its rules."""
    found = []
    for p in (ROOT / "backend" / "app").rglob("*.py"):
        if "demo" in p.parts:
            continue
        for m in MACHINES.values():
            for sets in re.findall(rf"update {m.table} set (.*?) where", p.read_text(), re.S):
                if re.search(rf"\b{m.column} = (?!\?)", sets):
                    found.append(f"{p.relative_to(ROOT)}: {m.table}")
    # Each of these is written only from a state the machine allows:
    assert sorted(found) == [
        "backend/app/modules/operations/administration/repo.py: members",    # accepting an invite, from invited, with the password
        "backend/app/modules/operations/appointments/repo.py: waitlist",     # booking marks matching entries, from waiting
        "backend/app/modules/operations/scheduling/repo.py: leave_requests",  # a doctor back at work cancels approved leave
    ], found


def test_moves_are_refused_with_a_clear_reason():
    with TestClient(app) as c:
        h, doc = clinic(c, "states@x.in")
        day = (date.today() + timedelta(days=5)).isoformat()
        # leave: a turned-down leave can't be cancelled; a cancelled one can't be cancelled again
        r = c.post("/api/leave", headers=h, json={"start_date": day, "end_date": day, "type": "casual", "reason": "x"}).json()
        nurse = member(c, h, "Nurse", "n-states@x.in", "staff", ["operations"])
        nh = join(c, nurse["invite_code"])
        mine = c.post("/api/leave", headers=nh, json={"start_date": day, "end_date": day, "type": "sick", "reason": "y"}).json()
        assert c.post(f"/api/leave/{mine['id']}/reject", headers=h).json()["status"] == "rejected"
        x = c.post(f"/api/leave/{mine['id']}/cancel", headers=nh)
        assert x.status_code == 409 and x.json()["detail"] == "This leave was turned down."
        assert c.post(f"/api/leave/{mine['id']}/approve", headers=h).status_code == 409
        assert c.post(f"/api/leave/{r['id']}/cancel", headers=h).status_code == 200
        assert c.post(f"/api/leave/{r['id']}/cancel", headers=h).json()["detail"] == "This leave was already cancelled."

        # waitlist: removing twice is fine; a booked entry stays booked
        p = c.post("/api/patients", headers=h, json={"name": "W", "consent": True}).json()
        w = c.post("/api/waitlist", headers=h, json={"patient_id": p["id"], "doctor_id": doc, "date": day}).json()
        c.post(f"/api/waitlist/{w['id']}/book", headers=h)
        x = c.delete(f"/api/waitlist/{w['id']}", headers=h)
        assert x.status_code == 409 and x.json()["detail"] == "They already have a booking."
        assert c.delete("/api/waitlist/99999", headers=h).status_code == 404

        # members: someone deactivated before joining goes back to invited, not to an account with no password
        late = member(c, h, "Late", "late@x.in", "staff", ["operations"])
        assert c.patch(f"/api/members/{late['id']}", headers=h, json={"status": "inactive"}).json()["status"] == "inactive"
        assert c.patch(f"/api/members/{late['id']}", headers=h, json={"status": "active"}).json()["status"] == "invited"
        assert c.post(f"/api/members/{late['id']}/invite", headers=h).status_code == 200
