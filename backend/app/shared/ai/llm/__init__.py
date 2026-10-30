"""Language model access. Prompts live in shared/ai/prompts; providers in providers/."""
from pathlib import Path

from .providers.gemini import enabled, generate

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def prompt(name: str) -> str:
    return (PROMPTS / name).read_text()
