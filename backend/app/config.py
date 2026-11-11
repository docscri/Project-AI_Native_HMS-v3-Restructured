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
LLM_MODEL = "gemini-3.8-flash"     # newest stable Flash on our key (Oct 2026); "gemini-flash-latest" follows Google's current Flash
# The model for each AI job (a folder in shared/ai/tasks/); "" uses LLM_MODEL. The stronger model reads reports and
# writes the note, where a mistake costs most; summaries of already-checked text use 3.5 Flash-Lite.
# Override one job without editing this file: LLM_MODEL_<JOB>=<model>, e.g. LLM_MODEL_BRIEF_SUMMARY=gemini-3.8-flash
LLM_MODELS = {
    "read_report": "",                       # lab reports and scans (images, PDFs)
    "draft_note": "",                        # the note and prescription
    "brief_summary": "gemini-3.5-flash-lite",
    "visit_lines": "gemini-3.5-flash-lite",
    "note_values": "gemini-3.5-flash-lite",
}
SPEECH = "deepgram"
SPEECH_MODEL = "nova-3-medical"   # medical vocabulary (drugs, doses, MSE...); patients' audio opted out of Deepgram training
SPEECH_LANGUAGE = "en"

# Prices for the usage meter (scripts/usage_report.py, /api/ops/usage). Check them against Google's and Deepgram's
# pages now and then: the meter prices each call at the rate here when it happened.
AI_PRICES = {                      # model: ($ per 1M input tokens, $ per 1M output tokens), standard tier
    "gemini-3.8-flash": (0.75, 3.75),         # introductory to 31 Dec 2026; from 1 Jan 2027: (1.50, 7.50), so update it then
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.8-flash-lite": (0.30, 2.50),
}
SPEECH_PRICES = {                  # model: $ per minute of audio, pay-as-you-go (no diarization / redaction add-ons used)
    "nova-3-medical": 0.0077,
    "nova-3": 0.0077,
}
USD_INR = 85

PACKAGES = {"DATABASE": "app.shared.db", "STORAGE": "app.shared.files", "LLM": "app.shared.ai.llm", "SPEECH": "app.shared.ai.speech"}
NO_PROVIDER = {"LLM": "none", "SPEECH": "browser"}   # built-in "off" choices with no file


def value(name: str) -> str:
    return (os.environ.get(name) or globals()[name]).strip()


def model_for(job: str) -> str:
    """The model an AI job uses: LLM_MODEL_<JOB> env var, then LLM_MODELS above, then LLM_MODEL."""
    return (os.environ.get(f"LLM_MODEL_{job.upper()}") or LLM_MODELS.get(job) or value("LLM_MODEL")).strip()


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
