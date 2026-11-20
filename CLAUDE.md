# Dictate: AI clinic app (read this first)

FastAPI backend + plain-JS frontend for Indian OPD clinics: front desk, queue, billing, team, and a doctor's
consultation (dictate → AI note in the department's format → sign → print/PDF). "Just me" (`clinics.solo = 1`) is
the same app for a doctor who visits several clinics: only Patients + Consultation, places instead of a clinic.

## Working here
- Push straight to `main`; no feature branches or PRs. Commits are authored by **Ephream**; no `Co-Authored-By`
  or `Claude-Session` lines. Render deploys `main`.
- Tests: `pip install -r backend/requirements-dev.txt`, then `CLINIC_DOTENV=0 pytest -q` (SQLite).
  Postgres too: `TEST_DATABASE_URL=postgresql://... CLINIC_DOTENV=0 pytest -q`. Run both before pushing.
- Run: `python scripts/run.py` (or `uvicorn app.main:app --app-dir backend --port 8050`). Demo data: `python scripts/seed_demo.py`.
- Never commit `.env` or keys. Never use the Gemini free tier with real patients.

## Map
```
backend/app/config.py   providers (DATABASE sqlite|postgres, STORAGE local|supabase, LLM, SPEECH), AI models per job,
                        prices for the usage meter (AI_PRICES, SPEECH_PRICES, USD_INR). Secrets only in .env / Render.
backend/app/shared/     db (sqlite/postgres providers, migrate), auth (sessions, screens), ai (llm/gemini, speech/deepgram,
                        tasks/), files, mail, printing (+ pdf.py, fonts), states.py, usage/ (meter), errors.py, audit
backend/app/core/       clinic (+ schedule), member, patient, visit (+ ledger), departments, labs.py (lab names/units)
backend/app/modules/    operations/ (account, administration, patients, scheduling, appointments, team)
                        clinical/ (consultation + live dictation, notes, brief, documents, signatures, solo)
                        financial/ (payments, reports + /api/ops/usage)
migrations/             NNN_name.sql or .py, applied once at startup (integer primary key → identity on Postgres)
frontend/               index.html, app.css, js/{shared,auth,admin,operations,clinical}/*.js (classic scripts, one global scope)
scripts/                run.py, seed_demo.py, usage_report.py
infra/render/           render.yaml (free trial, SQLite + demo), render.production.yaml (Supabase)
tests/                  helpers.py; operations/ clinical/ financial/ ai/ regressions/; test_api_snapshot.py; test_states.py
docs/STATES.md          generated: cd backend && python -m app.shared.states > ../docs/STATES.md
```

## Backend rules
- Feature = `routes.py` (HTTP only) → `service.py` (rules; raise `app.shared.errors`, never HTTPException) → `repo.py` (SQL only, `?` placeholders).
- Features talk through each other's `service`, never `repo`. Clinical text never leaves through Operations endpoints.
- One request = one transaction (`get_db` commits). **Never hold a write open across an AI call** (SQLite has one writer):
  commit first, as `brief.values_of` does.
- Postgres rows are dict-like: use `row()`/`rows()` and column names; never unpack a row as a tuple.
- Every status change goes through a `Machine` in `shared/states.py` (`VISIT.move(db, id, frm, to, ...)`).
- AI jobs: `shared/ai/tasks/<job>/{prompt.md, task.py}`, called only via `tasks.run()`; each has `check()` and a
  non-AI `fallback()`. Bump `Version:` in prompt.md when changing it. Fixed prompt text first, patient data last (caching).
- `tests/snapshots/api.json` guards every route's shape: regenerate with `UPDATE_SNAPSHOT=1` only for intended changes.
- Usage meter: Gemini tokens (incl. cached) and dictation seconds per clinic, written by a background thread.

## Frontend rules
- Clicks are delegated by `data-a="action"` (`shared/events.js`); file inputs must be in its pass-through list.
- State lives in `S` (session) and `M` (open modal). `api()`, `modal()`, `toast()`, `busy()` (the 3-dot "working" sign) are in `core.js`.
- Breakpoints: phone/tablet ≤ 1023 px (dark top bar with the patient, actions in the bottom bar), laptop ≥ 1024 px.
  Any feature must work in both apps (clinic and Just me) on phone, tablet and laptop.
- Consultation: Brief / Consult / Note tabs; bottom bar = + Report · mic · Generate note; Note tab has its own mic
  + live caption; after Stop the note is written automatically (unless the draft was hand-edited).

## Deploy notes
- Render start: `timeout 120 python scripts/seed_demo.py; uvicorn ...`. The demo loader runs with `LLM=none` (no AI calls).
- Gemini 429s mean a free or exhausted key; calls retry twice, then fall back to the plain draft.
- Production plan: Render Starter + Supabase Pro (Mumbai), `SEED_DEMO=0`, paid Gemini key, Deepgram `nova-3-medical`.
