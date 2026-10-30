import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("CLINIC_DATA_DIR", Path(__file__).resolve().parents[4] / "data"))
DB_PATH = DATA_DIR / "clinic.db"
UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def is_postgres() -> bool:
    return DATABASE_URL.startswith(("postgres://", "postgresql://"))
