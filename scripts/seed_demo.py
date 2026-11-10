"""Load the psychiatry demo clinic into an EMPTY database (the same one the app uses: data/ locally, or DATABASE_URL).

    python scripts/seed_demo.py

Does nothing if the database already has a clinic. Logins: anitha@demo.in (owner), arun@demo.in (solo doctor), joseph@demo.in, divya@demo.in,
sneha@demo.in; password demo1234. Invented people only: never load it into a database with real patients.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.demo.psychiatry import seed, seed_solo  # noqa: E402

if __name__ == "__main__":
    if os.environ.get("SEED_DEMO", "1") != "1":
        sys.exit(0)
    print("Psychiatry demo loaded." if seed() else "The database already has a clinic; nothing was added.")
    if seed_solo():   # its own account, so it is added even where the clinic demo already exists
        print("Solo psychiatrist demo loaded (arun@demo.in).")
