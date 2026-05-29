# Existing File Reconciliation List

| Existing file | Runtime role | Action |
| --- | --- | --- |
| `docs/taiji_five_metric_tensor_runtime_zh.md` | master runtime specification | keep as governing overview |
| `schemas/tensor_packet.schema.json` | canonical TensorPacket JSON schema | keep canonical |
| `schemas/pos_service_intent.schema.json` | POS/service intent schema | bind into TensorPacket intent vector later |
| `Taiji_Governance/identity/digital_identity.yml` | node and service identity registry | map into trust graph |
| `Taiji_Governance/deployments/tailscale_deployment_manifest.json` | deployment manifest | input to replay/deployment drift checks |
| `Taiji_Governance/deployments/tailscale_preflight_record.json` | preflight record | input to audit lineage |
| `Taiji_Governance/deployments/tailscale_rollback_plan.md` | rollback plan | map to rollback horizon |
| `Taiji_Governance/logs/audit.log` | append-only audit journal | event bus candidate |
| `Taiji_Governance/logs/deployment_audit.jsonl` | deployment audit | deployment replay and drift source |
| `Taiji_AutoBuild/scripts/04_system_total_probe.py` | local authorization and rescue snapshot | human decision and physical anchor source |
| `Taiji_AutoBuild/scripts/06_metric_predictive_alert.py` | read-only hazard scanner | future risk classifier input |
