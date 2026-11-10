-- Solo doctors: one doctor, their own patients, seen at several places (clinics, hospital OPDs).
-- A solo account is a clinic with solo = 1 and one member; it has no queue, billing, schedules or team.
alter table clinics add column solo integer not null default 0;
create table if not exists locations (
    id integer primary key,
    clinic_id integer not null references clinics(id),
    name text not null,
    archived integer not null default 0,
    created_at text not null default current_timestamp
);
create index if not exists locations_clinic on locations (clinic_id);
alter table visits add column location_id integer references locations(id);
