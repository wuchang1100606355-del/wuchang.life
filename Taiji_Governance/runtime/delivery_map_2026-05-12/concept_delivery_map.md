# Concept Delivery Map

| Concept Source | Engineering Delivery | Evidence | Next Action |
| --- | --- | --- | --- |
| MinimalSpacetimeSystem | temporal event runtime / event sourcing | `runtime/ledger/`, `runtime/snapshots/`, `Taiji_Governance/runtime/replay/` | Normalize event IDs and replay windows |
| SpaceTimeSystemBenchmark | deterministic temporal slot mapping / benchmark | `reports/metric_tensor_io_energy_eval_20260509_012731.json` | Keep as benchmark evidence, remove physics claims from production docs |
| SisterJ_ADI_Gateway | local-truth-cloud-metric / PII separation gateway | `legacy_core/taiji_unified_gateway_edge.py`, `docs/taiji_hub_google_workspace_policy_gateway_zh.md` | Refactor toward Gateway policy runtime before cloud use |
| SpacetimeTaskBridge | projection layer / external adapter | `services/gateway/main.py`, `runtime_adapters/` | Require TensorPacket before action routing |
| SpacetimeInstaller | deployment packaging / token gate | `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/` | Keep localhost-only until Gateway/Tunnel proof |
| MTL_Modelfile | identity constitution / governance runtime | `models/`, `Taiji_Governance/system_info/unique_ai_window_partition_policy_2026-05-12.md` | Preserve one XiaoJ identity, internal windows only |
| encrypted_blob/key | encrypted state persistence / key rotation required | `docs/taiji_hub_predictive_alert_system_zh.md`, `Taiji_Governance/runtime/plaintext_free/` | Keep keys outside repo, never expose content |

## Formal Documentation Rule

Formal engineering documents should use:

- temporal event runtime
- deterministic temporal slot mapping
- edge governance runtime
- local-truth-cloud-metric architecture
- coordinate MetricPacket protocol

Original symbolic wording may be preserved in archive or design notes, but production specs should express behavior in inspectable engineering terms.

