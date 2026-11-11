-- Per doctor: write the note automatically when they stop dictating (on unless they turn it off in Account).
alter table members add column auto_note integer not null default 1;
