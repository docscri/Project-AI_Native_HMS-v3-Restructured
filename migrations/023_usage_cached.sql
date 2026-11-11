-- Input tokens Google served from its cache (billed at a tenth of the input price); part of tokens_in.
alter table usage_events add column tokens_cached integer not null default 0;
