# Governance Gap Report

## Gap Classification

| Gap | Level | Reason | Required closeout |
| --- | --- | --- | --- |
| Runtime subdomain files absent | L1 | Concepts exist but were not individually indexed | Add standalone runtime files |
| Replay index absent | L2 | Replay cannot be machine-audited without packet lineage index | Add `replay_index_schema.yaml` |
| Deadbox restore absent | L2 | Unsafe packets need controlled recovery path | Add restore policy |
| AI usage routing absent | L2 | GPU/token/multimodal costs can drift | Add routing policy |
| Runtime identity trust graph absent | L2 | Nodes exist but trust boundary is not machine-readable | Add trust graph |
| Enforcement interceptor not implemented | L2 | Gateway skeleton is not yet runtime interceptor | Add interceptor spec; code later |
| Live execution protection | L3 if bypassed | Live deployment remains disabled | Keep A5 disabled until approved runtime exists |

## Reconciliation Result

This pass converts missing runtime domains into local governance files. It does not implement live runtime mutation, credential issuance, cloud calls, Docker changes, Odoo DB writes, or deployment execution.
