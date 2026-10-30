"""Gemini: JSON in, JSON out. Used only when GEMINI_API_KEY is set."""
import json
import os

import httpx

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def generate(parts: list[dict]) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    r = httpx.post(url, params={"key": os.environ["GEMINI_API_KEY"]}, timeout=90, json={
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    })
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
