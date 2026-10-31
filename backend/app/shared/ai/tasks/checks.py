"""Checks shared by the tasks that write sentences with citations."""
import re

NUM = re.compile(r"\d+(?:\.\d+)?")


def grounded(items: list[dict], sources: dict, allowed=None) -> list[dict]:
    """Keeps a sentence only if it cites known sources (and only allowed ones, when given) and every number in it
    appears in them. Repeated sentences become one, citing every source."""
    out, seen = [], {}
    for it in items or []:
        text = str(it.get("text") or "").strip()
        cites = [c for c in it.get("cites") or [] if c in sources]
        if not text or not cites or (allowed and not all(allowed(c) for c in cites)):
            continue
        have = set(NUM.findall(" ".join(sources[c]["text"] for c in cites)))
        if not all(x in have for x in NUM.findall(text)):
            continue
        key = re.sub(r"[^a-z0-9]", "", text.lower())
        if key in seen:
            seen[key]["cites"] += [c for c in cites if c not in seen[key]["cites"]]
            continue
        seen[key] = {"text": text, "cites": cites}
        out.append(seen[key])
    return out
