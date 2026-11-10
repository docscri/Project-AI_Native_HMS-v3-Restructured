-- A doctor's signature image. Every version is kept: a signed note points at the one that was current when it was
-- signed, so changing the signature later never changes an old note.
create table if not exists signatures (
    id integer primary key,
    clinic_id integer not null references clinics(id),
    member_id integer not null references members(id),
    path text not null,
    created_at text not null default current_timestamp
);
create index if not exists signatures_member on signatures (member_id);
alter table members add column signature_id integer references signatures(id);
alter table notes add column signature_id integer references signatures(id);
