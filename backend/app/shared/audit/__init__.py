"""Who did what, when: one row per action in events."""
import json

from app.shared.db import now


def log_event(db, clinic_id, actor_id, entity, entity_id, action, data=None) -> None:
    db.execute(
        "insert into events (clinic_id, actor_id, entity, entity_id, action, data, at) values (?, ?, ?, ?, ?, ?, ?)",
        (clinic_id, actor_id, entity, entity_id, action, json.dumps(data) if data else None, now()),
    )
