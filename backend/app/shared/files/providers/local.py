"""Uploads on the server's disk (data/uploads)."""
from pathlib import Path

from ...db import UPLOAD_DIR


def save(name: str, data: bytes, mime: str) -> str:
    path = UPLOAD_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def read(stored: str) -> bytes:
    with open(stored, "rb") as f:
        return f.read()


def delete(stored: str) -> None:
    Path(stored).unlink(missing_ok=True)
