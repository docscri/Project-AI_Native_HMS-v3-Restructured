# Architecture

```
backend/requirements.txt      Python packages the app needs
backend/requirements-dev.txt  + test tools (pip install -r backend/requirements-dev.txt, then pytest)
backend/app/
  config.py          provider names (DATABASE, STORAGE, LLM, SPEECH) and models; secrets stay in .env
  main.py            app, routers, static frontend
  shared/            plumbing with swappable providers, no clinic rules
    db/              connect/get_db/row/rows/now; providers/sqlite.py, providers/postgres.py; migrate.py
    auth/            sessions, passwords, roles and screens (current_member, require_screen, require_admin)
    audit/           log_event
    ai/              llm/ (Gemini provider), speech/ (Deepgram), tasks/ (the AI jobs, see below)
    files/           uploads: providers/local.py, providers/supabase.py
    mail/  printing/ validate.py  errors.py
  core/              entities several features change: clinic (+ schedule rules), member, patient, visit (+ ledger)
  modules/
    operations/      account (+ owner onboarding), administration, patients, scheduling, appointments (+ waitlist), team (attendance + leave)
    clinical/        consultation (+ live dictation), notes, brief, documents
    financial/       payments, reports (collections + day close)
migrations/          NNN_name.sql or .py with run(db); applied once each at startup
frontend/            the browser app
docs/                README.md, ARCHITECTURE.md
infra/                deployment: render/ (Render blueprints); docker/ etc. go here later
scripts/             run.py (local start helper)
tests/               helpers.py (clinic, started_visit) shared by all tests
  operations/ clinical/ financial/   API and direct service tests per area
  regressions/       tests for bugs found in earlier reviews
  test_flow.py       one end-to-end clinic day
  test_api_snapshot.py  guards every route's status and response shape (never update it to make a refactor pass)
```

## A feature

```
feature/
  routes.py   URLs, auth dependency, body in -> service -> response out. No SQL, no rules.
  schema.py   Pydantic request bodies (and response shapes where useful). No logic.
  service.py  The rules. Raises app.shared.errors (NotFound, Conflict, Invalid, Forbidden), never HTTPException. No FastAPI imports.
  repo.py     SQL only. Takes db, returns dicts/rows. No decisions.
```

A small feature may be a single `feature.py` until it grows.

## Rules

1. Features call each other through `service`, never another feature's `repo`.
2. One action = one transaction: the request's `db` (from `get_db`) commits at the end; services never commit, except where a background task must see the row first (then commit right before adding the task).
3. Repos return plain dicts. SQL uses `?` placeholders; Postgres gets them translated.
4. Clinical text (dictation, notes) never leaves through Operations endpoints (`core.visit.VISIT_FIELDS`).
5. Messages stay short and plain (e.g. "Visit not found.", "Note is signed.").

## AI tasks

Each job the AI does is a folder in `backend/app/shared/ai/tasks/`, laid out the same way:

| Task | Does | Used by |
|---|---|---|
| `read_report` | title, summary and values of an uploaded PDF or photo | documents |
| `note_values` | measured numbers in a signed note (for charts) | brief |
| `brief_summary` | the brief's Summary: new reports, then history | brief |
| `visit_lines` | one line per past visit for the event cards | brief |
| `draft_note` | SOAP note and prescription from the consultation | notes |

- `prompt.md`: the instructions. First line `Version: N`; `{{slots}}` are filled from the inputs.
- `task.py`: `Reply` (the reply shape, checked with Pydantic), `parts()` (what is sent), `check()` (keeps only what
  the sources support: real citations, numbers that match, medicines that were said) and `fallback()` (the plain version).
- `tasks.run(task, **inputs)` is the only way to call one: AI off, a failed call, a reply in the wrong shape or one
  that fails the checks all give the fallback, and the failure is logged with the task and version (no patient text).
- Bump `Version:` when you change a prompt: saved briefs and note values made with an older version are made again.

