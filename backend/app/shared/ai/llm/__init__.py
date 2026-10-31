"""Language model access. LLM in app/config.py picks providers/<name>.py; the jobs it does live in shared/ai/tasks."""
from app import config


def enabled() -> bool:
    return config.value("LLM") != "none" and config.provider("LLM").enabled()


def generate(parts: list[dict]) -> dict:
    return config.provider("LLM").generate(parts)
