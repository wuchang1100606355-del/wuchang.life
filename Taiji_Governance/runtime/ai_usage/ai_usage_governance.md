# AI Usage Governance

Taiji Runtime conserves model usage while preserving correctness.

## Goals

- lower unnecessary model invocation
- lower repeated rendering
- lower multimodal retry
- lower GPU wake-up
- lower context expansion
- lower deployment waste

## Routing

| Task | Route |
| --- | --- |
| deterministic metadata | shell/read-only local |
| L0 summary | small/local model if needed |
| L1 draft | governed local model or deterministic parser |
| L2 guarded action | policy path + human confirmation |
| L3 unsafe action | deadbox |

No model invocation may bypass TensorPacket conversion.
