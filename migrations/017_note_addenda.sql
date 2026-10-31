-- Addenda: dated, signed corrections or additions under a signed note. The note itself never changes.
create table if not exists note_addenda (
    id integer primary key,
    clinic_id integer not null references clinics(id),
    note_id integer not null references notes(id),
    text text not null,
    signed_by integer not null references members(id),
    signed_by_name text not null,
    signed_at text not null
);
create index if not exists note_addenda_note on note_addenda (note_id);
