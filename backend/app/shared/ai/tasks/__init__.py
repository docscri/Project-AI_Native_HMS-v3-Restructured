"""AI tasks. Each folder is one job the AI does, laid out the same way:

    prompt.md  the instructions; the first line is "Version: N" and {{slots}} are filled from the inputs
    task.py    NAME, Reply (the reply shape), parts() (what is sent), check() (keeps only what the sources
               support) and fallback() (the plain version, used when the AI is off, fails or gives a bad reply)

run() treats every task the same way. Bump the version in prompt.md when the instructions change:
saved results made with an older version are then made again.
"""
import json
import logging
import re
from pathlib import Path

import httpx

from app import config
from app.shared.ai import llm

log = logging.getLogger(__name__)


class Rejected(Exception):
    """A reply that parsed but failed the task's checks."""


def prompt(task_file: str) -> tuple[int, str]:
    """(version, instructions) from the prompt.md beside a task's task.py (pass its __file__)."""
    path = Path(task_file).parent / "prompt.md"
    head, _, body = path.read_text(encoding="utf-8").partition("\n")
    m = re.fullmatch(r"Version:\s*(\d+)\s*", head)
    if not m:
        raise ValueError(f"{path} must start with 'Version: N'")
    return int(m.group(1)), body.strip()


def version(task) -> str:
    """e.g. "brief_summary@1"; saved results carry it, so a new prompt version makes them again."""
    return f"{task.NAME}@{prompt(task.__file__)[0]}"


def fill(task_file: str, **slots) -> str:
    """The instructions with {{slots}} filled; values that aren't text are sent as JSON."""
    text = prompt(task_file)[1]
    for k, v in slots.items():
        text = text.replace("{{" + k + "}}", v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
    if left := re.findall(r"\{\{(\w+)\}\}", text):
        raise ValueError(f"{task_file}: prompt.md slots not filled: {left}")
    return text


def reason(e: Exception) -> str:
    """Why a call failed, for the server log; never the request URL or any patient text."""
    status = getattr(getattr(e, "response", None), "status_code", None)
    if status == 404:
        return f"model {config.value('LLM_MODEL')!r} not found; check LLM_MODEL in backend/app/config.py"
    if status in (400, 401, 403):
        return f"request refused ({status}); check the API key"
    if status == 429:
        return "busy or over its limit (429)"
    if status:
        return f"AI service answered {status}"
    if isinstance(e, httpx.TimeoutException):
        return "AI service took too long"
    if isinstance(e, httpx.HTTPError):
        return "couldn't reach the AI service"
    if isinstance(e, Rejected):
        return f"reply failed the checks: {e}"
    return f"bad reply ({type(e).__name__})"


def run(task, *, on_failure: str = "fallback", **inputs):
    """The task's checked AI reply, or its fallback. on_failure="raise" re-raises instead (a report that
    couldn't be read is marked failed rather than given a plain stand-in)."""
    wants_ai = getattr(task, "wants_ai", lambda **_: True)
    if llm.enabled() and wants_ai(**inputs):
        try:
            reply = task.Reply.model_validate(llm.generate(task.parts(**inputs)))
            return task.check(reply.model_dump(), **inputs)
        except Exception as e:
            log.warning("AI task %s failed: %s", version(task), reason(e))
            if on_failure == "raise":
                raise
    return task.fallback(**inputs)
