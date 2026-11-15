"""Gemini: JSON in, JSON out. Used only when GEMINI_API_KEY is set; LLM_MODEL / LLM_MODELS in app/config.py pick the model."""
import json
import os
import time

import httpx

from app.shared import usage


def enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


RETRY = (429, 500, 503)   # busy, over the per-minute limit, or a passing server error: worth a short second try
WAITS = (2, 5)            # seconds before the 2nd and 3rd tries (Google's own retry hint is used when shorter)


def generate(parts: list[dict], model: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    for wait in (*WAITS, None):
        # The key goes in a header, never the URL: URLs end up in error messages and logs.
        r = httpx.post(url, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=90, json=body)
        if r.status_code not in RETRY or wait is None:
            break
        hint = r.headers.get("retry-after", "")
        time.sleep(min(wait, float(hint)) if hint.replace(".", "", 1).isdigit() else wait)
    r.raise_for_status()
    body = r.json()
    u = body.get("usageMetadata") or {}   # what Google billed: thinking tokens are charged as output
    usage.record_ai(model, u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0),
                    u.get("cachedContentTokenCount", 0))   # Google's automatic cache: the repeated start of a request, a tenth of the price
    return json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
