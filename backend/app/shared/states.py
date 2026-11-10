"""Every status in the app, and the only moves between them.

Each thing with a status (a visit, a note, a leave request...) gets one Machine here. A move is
checked against the table and written only from the status that was read, so two people acting at
once can't leave a record in a state neither of them chose: the slower one gets a clear 409.

tests/test_states.py keeps these in step with the database CHECK constraints, and
docs/STATES.md is generated from them (python -m app.shared.states > docs/STATES.md).
"""
from dataclasses import dataclass, field

from app.shared.errors import Conflict


@dataclass(frozen=True)
class Machine:
    table: str
    moves: dict[str, frozenset[str]]
    start: tuple[str, ...]                      # states a new row may be created in
    column: str = "status"
    noun: str = "record"
    # What to tell someone who tried a move that isn't allowed from where the record is now.
    stuck: dict[str, str] = field(default_factory=dict)

    @property
    def states(self) -> set[str]:
        return set(self.moves) | {s for t in self.moves.values() for s in t}

    @property
    def final(self) -> set[str]:
        return {s for s in self.states if not self.moves.get(s)}

    def can(self, frm: str, to: str) -> bool:
        return to in self.moves.get(frm, ())

    def check(self, frm: str, to: str) -> None:
        if not self.can(frm, to):
            raise Conflict(self.stuck.get(frm) or f"This {self.noun} can't be changed now.")

    def move(self, db, row_id: int, frm: str, to: str, **fields) -> None:
        """Checks the move, then writes it only if the row is still `frm`."""
        self.check(frm, to)
        sets = {self.column: to, **fields}
        cur = db.execute(f"update {self.table} set {', '.join(f'{k} = ?' for k in sets)} where id = ? and {self.column} = ?",
                         (*sets.values(), row_id, frm))
        if cur.rowcount != 1:
            raise Conflict(f"This {self.noun} just changed. Refresh and try again.")


def _m(**moves: set[str]) -> dict[str, frozenset[str]]:
    return {k: frozenset(v) for k, v in moves.items()}


VISIT = Machine("visits", _m(
    booked={"waiting", "cancelled", "no_show"},
    waiting={"with_doctor", "booked"},              # booked <- waiting: undo an arrival
    with_doctor={"done"},
), start=("booked", "waiting", "with_doctor"),     # booked; walk-in arrives paid; a solo doctor's visit starts with him
   noun="visit", stuck={"done": "This visit is finished.", "cancelled": "This visit was cancelled.",
                        "no_show": "This visit was marked as not come."})

NOTE = Machine("notes", _m(draft={"signed"}), start=("draft",), noun="note",
               stuck={"signed": "This note is signed, so it can't be changed."})

MEMBER = Machine("members", _m(
    invited={"active", "inactive"},                # active only by accepting the invite
    active={"inactive"},
    inactive={"active", "invited"},                # back to invited if they never joined
), start=("invited", "active"), noun="member")

LEAVE = Machine("leave_requests", _m(
    pending={"approved", "rejected", "cancelled"},
    approved={"cancelled"},
), start=("pending", "approved"), noun="leave request",
   stuck={"rejected": "This leave was turned down.", "cancelled": "This leave was already cancelled."})

WAITLIST = Machine("waitlist", _m(waiting={"booked", "removed"}), start=("waiting",), noun="waitlist entry",
                   stuck={"booked": "They already have a booking.", "removed": "They're no longer on the waitlist."})

DOCUMENT = Machine("documents", _m(
    processing={"ready", "failed"},
    failed={"processing"},                         # read again
), start=("processing",), column="ai_status", noun="document",
   stuck={"processing": "This document is still being read.", "ready": "This document has already been read."})

MACHINES = {"visit": VISIT, "note": NOTE, "member": MEMBER, "leave": LEAVE, "waitlist": WAITLIST, "document": DOCUMENT}


def markdown() -> str:
    out = ["# States", "", "Generated from `backend/app/shared/states.py`. Do not edit by hand.", ""]
    for name, m in MACHINES.items():
        out += [f"## {name.capitalize()} (`{m.table}.{m.column}`)", "", "```mermaid", "stateDiagram-v2"]
        out += [f"    [*] --> {s}" for s in m.start]
        out += [f"    {a} --> {b}" for a in m.moves for b in sorted(m.moves[a])]
        out += [f"    {s} --> [*]" for s in sorted(m.final)]
        out += ["```", ""]
    return "\n".join(out)


if __name__ == "__main__":
    print(markdown(), end="")
