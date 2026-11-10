# States

Generated from `backend/app/shared/states.py`. Do not edit by hand.

## Visit (`visits.status`)

```mermaid
stateDiagram-v2
    [*] --> booked
    [*] --> waiting
    [*] --> with_doctor
    booked --> cancelled
    booked --> no_show
    booked --> waiting
    waiting --> booked
    waiting --> with_doctor
    with_doctor --> done
    cancelled --> [*]
    done --> [*]
    no_show --> [*]
```

## Note (`notes.status`)

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> signed
    signed --> [*]
```

## Member (`members.status`)

```mermaid
stateDiagram-v2
    [*] --> invited
    [*] --> active
    invited --> active
    invited --> inactive
    active --> inactive
    inactive --> active
    inactive --> invited
```

## Leave (`leave_requests.status`)

```mermaid
stateDiagram-v2
    [*] --> pending
    [*] --> approved
    pending --> approved
    pending --> cancelled
    pending --> rejected
    approved --> cancelled
    cancelled --> [*]
    rejected --> [*]
```

## Waitlist (`waitlist.status`)

```mermaid
stateDiagram-v2
    [*] --> waiting
    waiting --> booked
    waiting --> removed
    booked --> [*]
    removed --> [*]
```

## Document (`documents.ai_status`)

```mermaid
stateDiagram-v2
    [*] --> processing
    processing --> failed
    processing --> ready
    failed --> processing
    ready --> [*]
```
