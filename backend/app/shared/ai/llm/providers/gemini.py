"""Gemini: JSON in, JSON out. Used only when GEMINI_API_KEY is set; LLM_MODEL / LLM_MODELS in app/config.py pick the model."""
import json
import os

import httpx

from app.shared import usage


def enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def generate(parts: list[dict], model: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    # The key goes in a header, never the URL: URLs end up in error messages and logs.
    r = httpx.post(url, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=90, json={
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    })
    r.raise_for_status()
    body = r.json()
    u = body.get("usageMetadata") or {}   # what Google billed: thinking tokens are charged as output
    usage.record_ai(model, u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0))
    return json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
