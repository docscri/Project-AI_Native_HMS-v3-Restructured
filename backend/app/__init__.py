"""Settings from environment variables or .env (not read when CLINIC_DOTENV=0, as in the tests)."""
import os
from pathlib import Path

if os.environ.get("CLINIC_DOTENV") != "0":
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    except ImportError:  # dotenv is optional
        pass

# Servers run on UTC; "today" and times must be clinic-local.
import os as _os
import time as _time

_os.environ["TZ"] = _os.environ.get("CLINIC_TZ") or "Asia/Kolkata"
if hasattr(_time, "tzset"):  # not on Windows
    _time.tzset()
