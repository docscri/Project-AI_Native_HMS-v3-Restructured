"""Uploads in Supabase Storage, when SUPABASE_URL and SUPABASE_SERVICE_KEY are set."""
import os

import httpx

BUCKET = os.environ.get("SUPABASE_BUCKET", "clinic-documents")
PREFIX = "supabase:"


def settings() -> tuple[str, str] | None:
    url, key = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SERVICE_KEY", "")
    return (url, key) if url and key else None


def save(name: str, data: bytes, mime: str) -> str:
    url, key = settings()
    r = httpx.post(f"{url}/storage/v1/object/{BUCKET}/{name}", content=data, timeout=60,
                   headers={"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": mime})
    r.raise_for_status()
    return PREFIX + name


def read(stored: str) -> bytes:
    sb = settings()
    if not sb:
        raise RuntimeError("Supabase storage is not configured.")
    url, key = sb
    r = httpx.get(f"{url}/storage/v1/object/{BUCKET}/{stored.removeprefix(PREFIX)}", timeout=60,
                  headers={"Authorization": f"Bearer {key}", "apikey": key})
    r.raise_for_status()
    return r.content


def delete(stored: str) -> None:
    sb = settings()
    if not sb:
        raise RuntimeError("Supabase storage is not configured.")
    url, key = sb
    r = httpx.delete(f"{url}/storage/v1/object/{BUCKET}/{stored.removeprefix(PREFIX)}", timeout=60,
                     headers={"Authorization": f"Bearer {key}", "apikey": key})
    if r.status_code != 404:   # already gone is fine
        r.raise_for_status()
