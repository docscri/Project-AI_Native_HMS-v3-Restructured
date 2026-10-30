"""Uploads: Supabase Storage if configured, else the server's disk."""
import uuid

from .providers import local, supabase

MAX_BYTES = 15 * 1024 * 1024
ALLOWED = {"application/pdf", "image/jpeg", "image/png", "image/webp", "image/heic", "text/plain"}
EXT = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic", "text/plain": "txt"}


def save(clinic_id: int, data: bytes, mime: str) -> str:
    name = f"{clinic_id}/{uuid.uuid4().hex}.{EXT.get(mime, 'bin')}"
    return (supabase if supabase.settings() else local).save(name, data, mime)


def read(stored: str) -> bytes:
    return (supabase if stored.startswith(supabase.PREFIX) else local).read(stored)
