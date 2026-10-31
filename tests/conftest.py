"""Tests drop the schema, so never point them at the real DATABASE_URL."""
import os
import tempfile

os.environ["CLINIC_DOTENV"] = "0"   # never load the developer's .env: real keys would make real AI and email calls

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "")
os.environ["DATABASE"] = "postgres" if os.environ["DATABASE_URL"] else "sqlite"
os.environ["STORAGE"] = "local"
for name in ("LLM", "LLM_MODEL", "SPEECH", "SPEECH_MODEL", "SPEECH_LANGUAGE"):
    os.environ.pop(name, None)
for name in [n for n in os.environ if n.startswith("LLM_MODEL_")]:   # per-job model overrides
    os.environ.pop(name)

os.environ["CLINIC_DATA_DIR"] = tempfile.mkdtemp()
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("SMTP_HOST", None)

if os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://")):
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute("drop schema public cascade")
        conn.execute("create schema public")
