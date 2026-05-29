# Missing Runtime Report

Status date: 2026-05-11  
Mode: Five-Metric Tensor Governance reconciliation  
Scope: local files only, no live deployment, no secret readout

## Summary

The Taiji Hub repository already contains a high-level Five-Metric Tensor Runtime specification and a JSON TensorPacket schema. The reconciliation found that several runtime domains were described in aggregate documents but were not yet separated into standalone runtime governance files.

## Existing Runtime Anchors

| Domain | Existing file | Status |
| --- | --- | --- |
| Five-Metric runtime overview | `docs/taiji_five_metric_tensor_runtime_zh.md` | implemented as specification |
| TensorPacket JSON schema | `schemas/tensor_packet.schema.json` | implemented |
| POS/service intent schema | `schemas/pos_service_intent.schema.json` | implemented |
| Digital identity | `Taiji_Governance/identity/digital_identity.yml` | partial |
| Deployment manifest | `Taiji_Governance/deployments/tailscale_deployment_manifest.json` | manifest-only |
| Rollback plan | `Taiji_Governance/deployments/tailscale_rollback_plan.md` | partial |
| Audit logs | `Taiji_Governance/logs/*.jsonl`, `audit.log` | partial |
| Runtime snapshot | `Taiji_Governance/baseline/runtime_snapshot_20260510T103532Z.txt` | snapshot exists |

## Missing Or Under-Indexed Runtime Domains

| Domain | Finding | Generated target |
| --- | --- | --- |
| Plaintext-Free Context Runtime | Policy exists in broad docs, not standalone | `runtime/plaintext_free/*.md` |
| Replay Governance Runtime | Mentioned in runtime spec, no index schema | `runtime/replay/*.md`, `replay_index_schema.yaml` |
| Tensor Deadbox Lifecycle | Defined conceptually, no restore policy | `runtime/deadbox/*.md` |
| AI Usage Governance | Legacy code has GPU/token hints, no governed policy | `runtime/ai_usage/*.md`, `usage_routing_policy.yaml` |
| Non-Linguistic Tensor Runtime | Concept defined, no state mapping file | `runtime/non_linguistic/*.md` |
| Governance Runtime Enforcement | Gateway skeleton exists, no interceptor spec | `runtime/enforcement/*.md` |
| Distributed Reconciliation | Topology notes exist, no reconciliation flow | `runtime/distributed/*.md` |
| Tensor Packet Lifecycle | JSON schema exists, no YAML mirror or lifecycle file | `runtime/packet/*.md`, `tensor_packet_schema.yaml` |
| Runtime Identity Layer | Identity YAML exists, no trust graph runtime | `runtime/identity/*.md` |
| Multimodal Governance Runtime | Mentioned in spec, no policy file | `runtime/multimodal/*.md` |

## Risk

Current risk: `L1_near` for documentation/schema gaps.  
Escalates to `L3_metric_hazard` if any runtime tries to execute without TensorPacket conversion, replay validation, audit lineage, or human decision for high-risk actions.
