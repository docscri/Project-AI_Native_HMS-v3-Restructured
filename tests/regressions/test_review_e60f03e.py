"""Findings from the review of e60f03e: a tablet count said before the medicine's name counts, and a strength must
be said as a strength (the 7 of "for 7 days" is not 7 mg)."""
from app.shared.ai.tasks.draft_note import task as draft_note


def keep(text, rx):
    items = [{"id": "T1", "kind": "transcript", "text": text}]
    full = [r | {k: r.get(k, "") for k in ("dose", "duration", "instructions")} for r in rx]
    return [(r["medicine"], r["dose"], r["duration"]) for r in draft_note.keep_said(full, items)]


def test_a_count_said_before_the_name_counts():
    assert keep("Give one tablet of Dolo 650 mg twice daily.", [{"medicine": "Dolo 650 mg", "dose": "2-0-2"}]) == [("Dolo 650 mg", "", "")]
    assert keep("Give two tablets of Dolo 500 mg twice daily.", [{"medicine": "Dolo 500 mg", "dose": "2-0-2"}]) == [("Dolo 500 mg", "2-0-2", "")]
    assert keep("Give Dolo 650 mg twice daily and one tablet of Pantoprazole 40 mg once daily.",
                [{"medicine": "Pantoprazole 40 mg", "dose": "2-0-0"}, {"medicine": "Dolo 650 mg", "dose": "1-0-1"}]) == [
        ("Pantoprazole 40 mg", "", ""), ("Dolo 650 mg", "1-0-1", "")]


def test_a_strength_must_be_said_as_a_strength():
    assert keep("Amoxicillin 500 mg for 7 days.", [{"medicine": "Amoxicillin 7 mg"}]) == []
    assert keep("Amoxicillin 500 mg for 7 days.", [{"medicine": "Amoxicillin 500 mg", "duration": "7 days"}]) == [("Amoxicillin 500 mg", "", "7 days")]
    assert keep("Pan-D 40 before breakfast for 10 days.", [{"medicine": "Pan-D 10"}]) == []
    assert keep("Syrup Ascoril 5 ml thrice daily.", [{"medicine": "Ascoril syrup 10 ml"}]) == []
