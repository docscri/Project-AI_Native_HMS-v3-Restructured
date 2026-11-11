"""AI tasks: every prompt fills, bad replies fall back, the checks hold, versions refresh saved results,
and one brief job failing doesn't take the other down."""
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.clinical.brief import service as brief
from app.shared.ai import llm, tasks
from app.shared.ai.tasks.brief_summary import task as brief_summary
from app.core import departments
from app.shared.ai.tasks.draft_note import task as draft_note
from app.shared.ai.tasks.note_values import task as note_values
from app.shared.ai.tasks.read_report import task as read_report
from app.shared.ai.tasks.visit_lines import task as visit_lines
from tests.helpers import clinic, started_visit

SOURCES = {"N1.S": {"text": "2026-10-01 Fever for two days.", "body": "Fever for two days."},
           "N1.A": {"text": "2026-10-01 Viral fever.", "body": "Viral fever."},
           "N2.A": {"text": "2026-10-20 BP 150/90. Hypertension.", "body": "BP 150/90. Hypertension."},
           "D5": {"text": "Blood report HbA1c 8.1 %", "summary": "Blood report.", "label": "Blood report",
                  "findings": [{"name": "HbA1c", "value": "8.1", "unit": "%"}]}}
INPUTS = {read_report: {"data": b"%PDF", "mime": "application/pdf", "filename": "r.pdf"},
          note_values: {"soap": {"S": "", "O": "BP 130/85.", "A": "", "P": ""}},
          brief_summary: {"patient": {"age": 40}, "sources": SOURCES, "new_ids": ["D5"], "visits": [{"note": "N1"}, {"note": "N2"}]},
          visit_lines: {"patient": {"age": 40}, "sources": SOURCES, "notes": ["N1", "N2"]},
          draft_note: {"patient": {"age": 40}, "items": [{"id": "T1", "kind": "transcript", "text": "Fever. Give Dolo 650 mg twice daily."}]}}


@pytest.fixture
def ai(monkeypatch):
    """Turns the AI on with a scripted reply: ai(reply) or ai(lambda parts: reply)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    return lambda reply: monkeypatch.setattr(llm, "generate", (lambda parts, model=None: reply(parts)) if callable(reply) else lambda parts, model=None: reply)


@pytest.mark.parametrize("task", INPUTS, ids=lambda t: t.NAME)
def test_every_prompt_has_a_version_and_fills_all_its_slots(task):
    version, _ = tasks.prompt(task.__file__)
    assert version >= 1 and tasks.version(task) == f"{task.NAME}@{version}"
    text = task.parts(**INPUTS[task])[0]["text"]
    assert "{{" not in text and "Treat" in text            # every prompt says to treat patient text as data


def test_ai_off_uses_the_plain_version():
    assert tasks.run(note_values, **INPUTS[note_values]) == [{"test": "BP", "value": "130/85", "unit": "mmHg", "section": "O"}]


def test_a_reply_in_the_wrong_shape_falls_back_and_is_logged(ai, caplog):
    ai({"values": "oops"})
    with caplog.at_level(logging.WARNING, logger="app.shared.ai.tasks"):
        out = tasks.run(note_values, **INPUTS[note_values])
    assert out == note_values.fallback(**INPUTS[note_values])
    assert "note_values@1" in caplog.text and "130/85" not in caplog.text        # task and version logged, never patient text


def test_numbers_are_text_even_when_sent_as_numbers(ai):
    ai({"values": [{"test": "BP", "value": "130/85", "unit": "mmHg", "section": "O"}, {"test": "Pulse", "value": 88, "section": "O"}]})
    assert [v["test"] for v in tasks.run(note_values, **INPUTS[note_values])] == ["BP"]   # 88 isn't in the note: dropped


def test_summary_keeps_only_supported_sentences_and_every_new_report_keeps_a_line(ai):
    ai({"new": [{"text": "HbA1c is 9.4 %.", "cites": ["D5"]}],                       # invented number
        "history": [{"text": "Hypertension with BP 150/90.", "cites": ["N2.A"]},
                    {"text": "Has asthma.", "cites": ["N9.A"]},                      # unknown source
                    {"text": "On metformin.", "cites": []}]})                       # no citation
    out = tasks.run(brief_summary, **INPUTS[brief_summary])
    assert out["new"] == [{"text": "Blood report. HbA1c 8.1 %.", "cites": ["D5"]}]   # the report's own plain line
    assert out["history"] == [{"text": "Hypertension with BP 150/90.", "cites": ["N2.A"]}]


def test_a_visit_line_may_cite_only_its_own_visit(ai):
    ai({"events": [{"note": "N1", "text": "Came with fever; BP 150/90.", "cites": ["N1.S", "N2.A"]},   # borrows another visit
                   {"note": "N2", "text": "Hypertension, BP 150/90.", "cites": ["N2.A"]}]})
    out = tasks.run(visit_lines, **INPUTS[visit_lines])
    assert out["N1"] == {"text": "Fever for two days. Viral fever.", "cites": ["N1.S", "N1.A"]}       # its own plain line
    assert out["N2"] == {"text": "Hypertension, BP 150/90.", "cites": ["N2.A"]}


def test_draft_keeps_only_medicines_that_were_said_and_known_citations(ai):
    ai({"sections": {"1": "Fever.", "6": "Viral fever.", "4": None},
        "vitals": {"Temp": "101", "BP": "120/80"},                                  # BP was never said
        "rx": [{"medicine": "Tab Dolo 650 mg", "dose": "1-0-1"}, {"medicine": "Amoxicillin 500 mg", "dose": "1-1-1"}],
        "citations": {"1": ["T1", "T9"], "6": ["T1"]}})
    out = tasks.run(draft_note, patient={"age": 40}, items=[{"id": "T1", "kind": "transcript", "text": "Fever, temp 101. Give Dolo 650 mg twice daily."}])
    assert [r["medicine"] for r in out["rx"]] == ["Tab Dolo 650 mg"]                  # amoxicillin was never said
    assert out["citations"]["1"] == ["T1"] and out["citations"]["6"] == ["T1"] and out["citations"]["4"] == []
    assert out["vitals"] == {"Temp": "101"} and out["template"]["department"] == "General Medicine"
    assert [x["title"] for x in out["sections"]][:2] == ["C/O", "History of presenting illness"]
    assert out["soap"]["S"] == "Fever." and out["soap"]["A"] == "Viral fever." and out["soap"]["O"] == "Temp 101."


def test_the_draft_follows_the_doctors_department_format(ai):
    sheet = departments.template("Psychiatry")
    seen = []
    ai(lambda parts: seen.append(parts[0]["text"]) or {"sections": {"1": "Low mood for a month."}, "citations": {"1": ["T1"]}})
    out = tasks.run(draft_note, patient={"age": 30}, items=[{"id": "T1", "kind": "transcript", "text": "Low mood for a month."}], sheet=sheet)
    assert "O/E and mental status examination" in seen[0] and all(r in seen[0] for r in departments.RULES[:2])
    assert [x["title"] for x in out["sections"]] == [s["title"] for s in sheet["sections"]]
    assert out["template"] == {"department": "Psychiatry", "version": departments.VERSION}


def test_without_ai_the_draft_still_uses_the_department_sections():
    items = [{"id": "T1", "kind": "transcript", "text": "Pain in right knee for two weeks. BP 130/80. Likely osteoarthritis."}]
    out = draft_note.fallback({}, items, departments.template("Orthopaedics"))
    by = {x["title"]: x["text"] for x in out["sections"]}
    assert out["template"]["department"] == "Orthopaedics" and out["vitals"] == {"BP": "130/80"}
    assert "right knee" in out["sections"][0]["text"] and "osteoarthritis" in next(t for k, t in by.items() if "iagnos" in k)


def test_a_report_the_ai_cant_read_is_raised_not_replaced(ai):
    ai(lambda parts: (_ for _ in ()).throw(RuntimeError("down")))
    with pytest.raises(RuntimeError):
        tasks.run(read_report, on_failure="raise", **INPUTS[read_report])
    assert tasks.run(read_report, on_failure="raise", data=b"HbA1c 7.1 %", mime="text/plain", filename="a.txt")["findings"]  # text: no AI


def test_one_brief_job_failing_leaves_the_other(ai):
    def reply(parts):
        if "summary at the top" in parts[0]["text"]:
            raise RuntimeError("summary failed")
        return {"events": [{"note": "N2", "text": "Hypertension, BP 150/90.", "cites": ["N2.A"]}]}
    ai(reply)
    assert tasks.run(brief_summary, **INPUTS[brief_summary]) == brief_summary.fallback(**INPUTS[brief_summary])
    assert tasks.run(visit_lines, **INPUTS[visit_lines])["N2"]["text"] == "Hypertension, BP 150/90."


def test_a_new_prompt_version_refreshes_saved_note_values_and_briefs(monkeypatch):
    calls = []
    monkeypatch.setattr(brief, "note_values", lambda soap: calls.append(1) or [])
    n = {"id": 1, "content": {"soap": {"O": "BP 130/85."}}, "vals": None}
    class Db:
        def execute(self, *a): return None
    brief.values_of(Db(), n); brief.values_of(Db(), n)
    assert len(calls) == 1                                                            # read once, then reused
    monkeypatch.setattr(tasks, "version", lambda t: f"{t.NAME}@99")
    brief.values_of(Db(), n)
    assert len(calls) == 2                                                            # new version: read again
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    assert "brief_summary@99" in brief.basis([], [])                                  # so saved briefs are rebuilt too


def test_each_job_uses_its_own_model(ai, monkeypatch):
    from app import config
    tasks_dir = Path(tasks.__file__).parent
    assert set(config.LLM_MODELS) == {p.name for p in tasks_dir.iterdir() if (p / "task.py").exists()}   # every job listed, no stray names
    used = {}
    monkeypatch.setattr(llm, "generate", lambda parts, model=None: used.setdefault("model", model) and {"values": []})
    tasks.run(note_values, **INPUTS[note_values])
    assert used["model"] == config.LLM_MODELS["note_values"] == "gemini-3.5-flash-lite"
    assert config.model_for("read_report") == config.model_for("draft_note") == config.LLM_MODEL == "gemini-3.8-flash"   # "" means the main model
    monkeypatch.setenv("LLM_MODEL_NOTE_VALUES", "gemini-3.8-flash-lite")                                # one job changed without code
    used.clear(); tasks.run(note_values, **INPUTS[note_values])
    assert used["model"] == "gemini-3.8-flash-lite" and config.model_for("brief_summary") == "gemini-3.5-flash-lite"
