"""Plain text helpers shared by features."""
import re

SENTENCE = re.compile(r"[^.!?\s].*?(?:[.!?]+(?=\s|$)|$)")


def sentences(text: str) -> list[str]:
    """Split like the page's sentences(): at . ! ? followed by a space or line end, so 100.8 stays whole."""
    return [m.group().strip() for line in (text or "").split("\n") for m in SENTENCE.finditer(line) if m.group().strip()]
