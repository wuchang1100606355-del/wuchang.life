# Governance Risk Register

| Risk | Level | Evidence | Required Action |
| --- | --- | --- | --- |
| Raw full context exchanged between model windows | L3 | Design hazard | Use `MetricPacket` coordinate tensor state only |
| 小J presented as two physical AIs | L2 | Naming hazard | Keep one XiaoJ identity and one visible AI surface |
| Open WebUI exposed on `0.0.0.0:3000` | L2/L3 | Docker metadata | Prove VPN/firewall/Gateway boundary or bind down |
| Odoo credential-like config visible through runtime config/process style | L3 if secret value is exposed | Earlier local observation, value not recorded here | Move to secret boundary and rotate before production |
| Odoo production mutation from natural language | L3 | Policy hazard | Draft-first, human confirmation, audit, rollback |
| Payment / refund / manager override by AI | L3 | Policy hazard | Block unless separate approved human-governed runtime exists |
| Destroying Docker volumes during optimization | L3 | Container hazard | No destructive cleanup without explicit confirmation |
| Cloud payload includes local truth / member plaintext | L3 | Data boundary hazard | Cloud payload limited to metric/hash/event/audit refs |

## Current Safe Status

- No container deletion performed.
- No volume deletion performed.
- No production deployment performed.
- No env secret value read or written.
- No cloud API call performed.

