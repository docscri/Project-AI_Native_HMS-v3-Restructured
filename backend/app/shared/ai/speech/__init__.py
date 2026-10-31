"""Speech to text. SPEECH in app/config.py picks providers/<name>.py; "browser" (or no key) = the browser's own recognition."""
from app import config


def name() -> str:
    """The provider in use: a server-side one when its key is set, else "browser"."""
    p = config.value("SPEECH").lower()
    return p if p != "browser" and config.provider("SPEECH").enabled() else "browser"


def enabled() -> bool:
    return name() != "browser"


def open_stream():
    return config.provider("SPEECH").open_stream()
