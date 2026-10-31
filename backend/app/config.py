"""Which provider the app uses for each service. Change a name here to switch.

Each name is a file in that service's providers/ folder; to add one, drop a new file there and put its name here:
    database  shared/db/providers/        sqlite, postgres
    storage   shared/files/providers/     local, supabase
    llm       shared/ai/llm/providers/    gemini, none
    speech    shared/ai/speech/providers/ deepgram, browser

Secrets (DATABASE_URL, API keys, SUPABASE_*) never go here: they stay in .env locally, or in the Render dashboard.
A deployment that needs a different provider can override a name with an env var of the same name (e.g. DATABASE=postgres).
"""
import os
from importlib import import_module
from pathlib import Path

DATABASE = "sqlite"
STORAGE = "local"
LLM = "gemini"
LLM_MODEL = "gemini-2.5-flash"
SPEECH = "deepgram"
SPEECH_MODEL = "nova-3"
SPEECH_LANGUAGE = "en"

PACKAGES = {"DATABASE": "app.shared.db", "STORAGE": "app.shared.files", "LLM": "app.shared.ai.llm", "SPEECH": "app.shared.ai.speech"}
NO_PROVIDER = {"LLM": "none", "SPEECH": "browser"}   # built-in "off" choices with no file


def value(name: str) -> str:
    return (os.environ.get(name) or globals()[name]).strip()


def provider(kind: str):
    """The module for the chosen provider of DATABASE, STORAGE, LLM or SPEECH."""
    return import_module(f"{PACKAGES[kind]}.providers.{value(kind).lower()}")


def secret(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def data_dir() -> Path:
    return Path(secret("CLINIC_DATA_DIR") or Path(__file__).resolve().parents[2] / "data")


def check() -> None:
    """Fail at startup with a clear message instead of on the first request."""
    for kind, package in PACKAGES.items():
        name = value(kind).lower()
        if name == NO_PROVIDER.get(kind):
            continue
        try:
            provider(kind)
        except ModuleNotFoundError:
            folder = package.removeprefix("app.").replace(".", "/") + "/providers/"
            raise SystemExit(f"{kind}={name!r}: no provider file {folder}{name}.py")
    if value("DATABASE") == "postgres" and not secret("DATABASE_URL"):
        raise SystemExit("DATABASE=postgres needs DATABASE_URL in .env (or the Render dashboard).")
    if value("STORAGE") == "supabase" and not (secret("SUPABASE_URL") and secret("SUPABASE_SERVICE_KEY")):
        raise SystemExit("STORAGE=supabase needs SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    if value("DATABASE") == "sqlite" and secret("DATABASE_URL"):
        print("Note: DATABASE_URL is set but DATABASE is 'sqlite', so the local SQLite file is used.")
