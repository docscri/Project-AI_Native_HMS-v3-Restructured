-- What each clinic used: one row per AI call (tokens) and per dictation stream (seconds of audio), with its cost
-- at the prices in app/config.py when it happened. cost_micro_usd is millionths of a dollar (whole numbers: no float drift).
create table if not exists usage_events (
    id integer primary key,
    clinic_id integer references clinics(id),
    kind text not null check (kind in ('ai', 'speech')),
    job text not null,
    model text not null,
    tokens_in integer not null default 0,
    tokens_out integer not null default 0,
    seconds integer not null default 0,
    cost_micro_usd integer not null default 0,
    at text not null
);
create index if not exists usage_clinic_at on usage_events (clinic_id, at);
