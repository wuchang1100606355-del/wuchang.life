# Replay Governance Runtime

Replay governance validates whether a packet may be executed again.

## Required Checks

- packet hash
- parent hash
- nonce uniqueness
- execution window
- authority continuity
- topology legitimacy
- deadbox state
- rollback horizon

## Replay Outcomes

| Outcome | Meaning |
| --- | --- |
| allow | replay is valid and low risk |
| warn | replay is suspicious but non-mutating |
| quarantine | replay needs audit review |
| deadbox | replay is unsafe |
| human_review | authority or topology changed |
