# Architecture

```
backend/app/
  main.py            app, routers, static frontend
  shared/            plumbing with swappable providers, no clinic rules
    db/              connect/get_db/row/rows/now; providers/sqlite.py, providers/postgres.py; migrate.py
    auth/            sessions, passwords, roles and screens (current_member, require_screen, require_admin)
    audit/           log_event
    ai/              llm/ (Gemini provider, prompt()), speech/ (Deepgram), prompts/
    files/           uploads: providers/local.py, providers/supabase.py
    mail/  printing/ validate.py  errors.py
  core/              entities several features change: clinic (+ schedule rules), member, patient, visit (+ ledger)
  modules/
    operations/      account, onboarding, administration, patients, scheduling, appointments, waitlist, team/{attendance,leave}
    clinical/        consultation, dictation, documents, notes, brief
    financial/       payments, collections, day_close
  demo/seed.py       demo clinic (SEED_DEMO=1)
migrations/          NNN_name.sql or .py with run(db); applied once each at startup
frontend/            the browser app
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
