"""The psychiatry demo loads into an empty database through the app's own API, and never into one that has a clinic."""
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(bool(os.environ.get("DATABASE_URL")), reason="runs on its own temporary SQLite database")
def test_psychiatry_demo_loads_once_into_an_empty_database():
    data = tempfile.mkdtemp()
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "DATABASE", "GEMINI_API_KEY")} | {"CLINIC_DATA_DIR": data, "CLINIC_DOTENV": "0", "SEED_DEMO": "1"}
    run = lambda: subprocess.run([sys.executable, str(ROOT / "scripts/seed_demo.py")], env=env, capture_output=True, text=True, timeout=240)
    first = run()
    assert first.returncode == 0 and "Psychiatry demo loaded." in first.stdout, first.stderr[-1500:]
    db = sqlite3.connect(Path(data) / "clinic.db")
    one = lambda q: db.execute(q).fetchone()[0]
    assert one("select count(*) from members where clinic_id = 1") == 4 and one("select count(*) from patients where clinic_id = 1") == 10
    assert "Solo psychiatrist demo loaded" in first.stdout
    solo = one("select clinic_id from members where email = 'arun@demo.in'")
    assert one(f"select solo from clinics where id = {solo}") == 1 and one(f"select count(*) from locations where clinic_id = {solo}") == 3
    assert one(f"select count(*) from notes n join visits v on v.id = n.visit_id where v.clinic_id = {solo} and n.status = 'signed'") == 5
    assert one(f"select count(*) from visits where clinic_id = {solo} and status = 'with_doctor'") == 1
    assert one("select count(*) from members where kind = 'doctor' and speciality != 'Psychiatry'") == 0      # psychiatry only
    assert one("select count(*) from notes where status = 'signed' and clinic_id = 1") >= 20 and one("select count(*) from note_addenda") == 1
    assert one("select count(*) from notes where content not like '%\"department\": \"Psychiatry\"%'") == 0      # every note in the psychiatry format
    assert one("select count(*) from documents where ai_status = 'ready'") == 4
    assert {r[0] for r in db.execute("select status from visits where date = (select max(date) from visits where status = 'done')")} >= \
        {"done", "with_doctor", "waiting", "no_show", "cancelled"}
    db.close()
    again = run()
    assert again.returncode == 0 and "nothing was added" in again.stdout and "Solo" not in again.stdout
