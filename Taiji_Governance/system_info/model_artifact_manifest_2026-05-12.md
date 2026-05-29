# Model Artifact Manifest

Version: 2026-05-12

## Summary

```text
files=82
total_bytes=43429575220
large_files_over_10MiB=8
manifest=/home/taiji_admin/Taiji_Hub/Taiji_Governance/system_info/model_artifact_manifest_2026-05-12.jsonl
```

## Runtime Rule

```text
Cloud readonly cold store -> Linux hot cache -> runtime mmap/load.
Reverse sync is blocked.
```

## Notes

Large files with Ollama `sha256-...` blob names use the blob filename as the integrity identifier without printing or inspecting model contents.
Large files without hash-bearing names are marked `pending_explicit_large_file_hash` until a human-approved hash pass is run.
