"""Language model access. LLM in app/config.py picks providers/<name>.py; prompts live in shared/ai/prompts."""
from pathlib import Path

from app import config

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def enabled() -> bool:
    return config.value("LLM") != "none" and config.provider("LLM").enabled()


def generate(parts: list[dict]) -> dict:
    return config.provider("LLM").generate(parts)


def prompt(name: str) -> str:
    return (PROMPTS / name).read_text()
