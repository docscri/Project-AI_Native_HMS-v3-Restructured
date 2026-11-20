# Dictate: clinic app

## Run it
Python 3.10+:
```bash
pip install -r backend/requirements.txt
python scripts/run.py        # or: python -m uvicorn app.main:app --app-dir backend --port 8050
```
Open http://localhost:8050 in Chrome → **Create account** → **My clinic** (front desk, team, billing) or **Just me**
(a doctor visiting several clinics). Data is saved in `data/` unless `.env` says otherwise (see `.env.example`).

## Demo data (invented people)
On an empty database: `python scripts/seed_demo.py`. Password **`demo1234`**:
- `anitha@demo.in`: owner, psychiatrist, Manas Mind Clinic (10 patients, 3 months of notes, today's queue)
- `joseph@demo.in`: psychiatrist · `divya@demo.in`: front desk · `sneha@demo.in`: social worker
- `arun@demo.in`: Just me psychiatrist at three clinics

It does nothing if a clinic already exists, so it never mixes with real patients.

## Deploy on Render
- **Trial:** Render → New → Blueprint → `infra/render/render.yaml`. SQLite and the demo, wiped on every deploy. Not for real patients.
- **Production:** Blueprint `infra/render/render.production.yaml`, with Supabase (Mumbai):
  1. Make a **private** bucket `clinic-documents`.
  2. Set `DATABASE_URL` (Session pooler URI), `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` and `APP_URL`.

  The blueprint already sets `DATABASE` and `STORAGE`, and tables are created on first start.
- **Optional keys:**
  - `GEMINI_API_KEY`: AI notes. Use a paid tier.
  - `DEEPGRAM_API_KEY`: live dictation. Without it, Chrome's own speech recognition is used.
  - `SMTP_*`: emailed invites and password resets. Without it, links are copied from Administration → Members.
  - `CLINIC_TZ`: time zone (default India).
  - `OPS_TOKEN`: lets you read the usage meter.

## Usage and cost
`python scripts/usage_report.py --month 2026-11`, or `curl -H "X-Ops-Token: <secret>" https://<app>/api/ops/usage?month=2026-11`.
It shows AI tokens, dictation minutes and cost per clinic. Keep the prices in `backend/app/config.py` up to date.

Developer notes: [CLAUDE.md](CLAUDE.md). Status diagrams: [docs/STATES.md](docs/STATES.md).
