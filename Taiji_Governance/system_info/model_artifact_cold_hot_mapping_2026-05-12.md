# AI Model Artifact Cold/Hot Mapping Policy

Version: 2026-05-12

## Decision

AI model artifacts may be stored in organization cloud storage only as readonly cold artifacts when licensing, storage quota, and governance classification allow it.

Runtime execution must use Linux local hot cache. Cloud storage is not a live model execution backend.

## Storage Layers

| Layer | Purpose | Example Path | Rule |
|---|---|---|---|
| Cloud readonly cold store | Cross-device restore, version baseline, non-sensitive model distribution | Google Drive organization shared folder | Readonly, no secret, no member plaintext |
| Linux hot cache | Runtime execution and mmap loading | `/home/taiji_admin/.ollama/models` | Primary model runtime cache |
| Project model definitions | Modelfile and runtime configuration | `/home/taiji_admin/Taiji_Hub/models` | Cloud readonly allowed if no secret |
| D controlled folder | Restricted model or sensitive derivative artifact | `/mnt/d/taiji_lock` | Human-reviewed, audited, not automatic |

## Five-Metric Mapping

```yaml
five_metric_model_mapping:
  intent: model_restore_or_runtime_load
  resource: large_binary_model_artifact
  time: async_cold_to_hot_sync
  authority: human_review_for_restricted_models
  topology: cloud_cold_store_to_linux_hot_cache_to_runtime_mmap
```

## Runtime Rule

```text
Cloud -> Linux local cache -> runtime mmap/load
```

Forbidden:

- Directly executing models from cloud-mounted paths.
- Uploading secrets, member plaintext, credential-bearing adapters, or private training data.
- Treating cloud model presence as runtime authority.
- Reverse syncing cloud artifacts back into source without review.

## Operational Notes

- Ollama model blobs commonly carry content hash names such as `sha256-...`; these may be used as integrity identifiers without printing model contents.
- Large artifacts should be uploaded with resumable/manual Drive upload or a governed sync tool after human confirmation.
- Model licensing must be checked before distribution to organization shared cloud.
- Use local Linux disk or a controlled high-speed storage path for active inference.

## Risk

| Case | Risk | Action |
|---|---|---|
| Public/open model weights, no embedded private data | L1_near | allow_with_audit |
| Fine-tuned model with possible private/member traces | L2_drift | human review, D controlled or local only |
| Model or adapter containing secrets, member plaintext, credential traces | L3_metric_hazard | block |
| Cloud direct runtime execution path | L2_drift | warn and redirect to local cache |
