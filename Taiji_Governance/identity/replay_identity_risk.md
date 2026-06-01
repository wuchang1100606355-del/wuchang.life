# Replay Identity Risk

Replay risk occurs when an old action is replayed under a changed identity.

| Replay case | Risk | Action |
| --- | --- | --- |
| old architect packet replayed as runtime owner | L2/L3 | quarantine |
| private commercial action replayed as community governance | L3 | deadbox |
| old payment or fund-pool packet replay | L3 | deadbox |
| stale deployment approval replay | L3 | deadbox |
| stale hardware lending record replay | L2 | human review |

Replay reset requires authority regeneration and audit review.
