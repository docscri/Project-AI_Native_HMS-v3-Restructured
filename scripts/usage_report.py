"""What each clinic used this month (or --month YYYY-MM): visits, AI calls and tokens, dictation minutes, cost in $ and ₹.
Runs against the same database as the app (data/ locally, or DATABASE_URL).

    python scripts/usage_report.py [--month 2026-11] [--json]
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.shared import db as database  # noqa: E402
from app.shared.usage import report  # noqa: E402

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--month", default=date.today().strftime("%Y-%m"))
    a.add_argument("--json", action="store_true")
    args = a.parse_args()
    database.init()
    db = database.connect()
    try:
        rows = report(db, args.month)
    finally:
        db.close()
    if args.json:
        print(json.dumps(rows, indent=2))
        sys.exit(0)
    print(f"Usage for {args.month}\n")
    print(f"{'Clinic':34} {'Visits':>6} {'AI calls':>8} {'Tokens in/out':>17} {'Dict. min':>9} {'$':>8} {'₹':>8} {'₹/visit':>8}")
    for r in rows:
        name = (r["clinic"] + (" (Just me)" if r["solo"] else ""))[:34]
        per = f"{r['inr_per_visit']:.2f}" if r["inr_per_visit"] is not None else "—"
        print(f"{name:34} {r['visits']:>6} {r['ai_calls']:>8} {r['tokens_in']:>8}/{r['tokens_out']:<8} {r['dictation_minutes']:>9.1f} "
              f"{r['usd']:>8.2f} {r['inr']:>8} {per:>8}")
    print(f"\nTotal: ${sum(r['usd'] for r in rows):.2f}  (₹{sum(r['inr'] for r in rows)})")
