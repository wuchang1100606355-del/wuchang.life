#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/dependency_relocation_v0_1/relocation.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

OUT_DIR="$SOURCE_ROOT/Taiji_Governance/system_info"
MANIFEST="$OUT_DIR/model_artifact_manifest_2026-05-12.jsonl"
SUMMARY="$OUT_DIR/model_artifact_manifest_2026-05-12.md"
AUDIT="$SOURCE_ROOT/Taiji_Governance/logs/model_artifact_manifest_2026-05-12.jsonl"

mkdir -p "$OUT_DIR" "$(dirname "$AUDIT")"
: > "$MANIFEST"

emit_file() {
  local path="$1"
  local category="$2"
  local cloud_allowed="$3"
  local d_lock_required="$4"
  local size
  local sha
  size="$(stat -c '%s' "$path")"
  if [[ "$(basename "$path")" =~ ^sha256-([0-9a-f]{64})$ ]]; then
    sha="sha256:${BASH_REMATCH[1]}"
    hash_source="ollama_blob_name"
  elif [ "$size" -le 10485760 ]; then
    sha="sha256:$(sha256sum "$path" | awk '{print $1}')"
    hash_source="sha256sum"
  else
    sha="pending_explicit_large_file_hash"
    hash_source="pending_local_execution"
  fi

  python3 - <<PY >> "$MANIFEST"
import json
record = {
    "path": "$path",
    "size_bytes": int("$size"),
    "category": "$category",
    "sha256": "$sha",
    "hash_source": "$hash_source",
    "five_code": {
        "intent": "model_artifact_baseline",
        "resource": "large_binary_or_modelfile",
        "time": "cold_to_hot_async_on_demand",
        "authority": "human_review_for_restricted_or_private_derivative",
        "topology": "cloud_cold_store_to_linux_hot_cache_to_runtime_mmap"
    },
    "targets": {
        "cloud_readonly_allowed": "$cloud_allowed" == "true",
        "linux_hot_cache_required_for_runtime": True,
        "d_lock_required": "$d_lock_required" == "true"
    },
    "runtime_rule": "copy_or_sync_to_local_linux_cache_before_load",
    "secret_material_included": False,
    "member_plaintext_included": False,
    "reverse_sync_allowed": False
}
print(json.dumps(record, ensure_ascii=False))
PY
}

if [ -d "$SOURCE_ROOT/models" ]; then
  while IFS= read -r file; do
    emit_file "$file" "project_model_definition" "true" "false"
  done < <(find "$SOURCE_ROOT/models" -type f | sort)
fi

if [ -d "$HOME/.ollama/models" ]; then
  while IFS= read -r file; do
    emit_file "$file" "ollama_model_artifact" "true" "false"
  done < <(find "$HOME/.ollama/models" -type f | sort)
fi

MANIFEST_PATH="$MANIFEST" SUMMARY_PATH="$SUMMARY" python3 - <<'PY'
import json
import os
from pathlib import Path
manifest = os.environ["MANIFEST_PATH"]
summary = os.environ["SUMMARY_PATH"]
rows = [json.loads(x) for x in Path(manifest).read_text(encoding="utf-8").splitlines() if x.strip()]
total = sum(r["size_bytes"] for r in rows)
large = [r for r in rows if r["size_bytes"] > 10 * 1024 * 1024]
Path(summary).write_text(f"""# Model Artifact Manifest

Version: 2026-05-12

## Summary

```text
files={len(rows)}
total_bytes={total}
large_files_over_10MiB={len(large)}
manifest={manifest}
```

## Runtime Rule

```text
Cloud readonly cold store -> Linux hot cache -> runtime mmap/load.
Reverse sync is blocked.
```

## Notes

Large files with Ollama `sha256-...` blob names use the blob filename as the integrity identifier without printing or inspecting model contents.
Large files without hash-bearing names are marked `pending_explicit_large_file_hash` until a human-approved hash pass is run.
""", encoding="utf-8")
print(f"manifest={manifest}")
print(f"summary={summary}")
print(f"files={len(rows)}")
print(f"total_bytes={total}")
print(f"large_files_over_10MiB={len(large)}")
PY

MANIFEST_PATH="$MANIFEST" python3 - <<'PY' >> "$AUDIT"
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
manifest = os.environ["MANIFEST_PATH"]
rows = [json.loads(x) for x in Path(manifest).read_text(encoding="utf-8").splitlines() if x.strip()]
print(json.dumps({
    "event": "model_artifact_manifest_built",
    "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    "manifest": manifest,
    "file_count": len(rows),
    "total_bytes": sum(r["size_bytes"] for r in rows),
    "google_api_called": False,
    "model_contents_printed": False,
    "secret_material_printed": False,
    "reverse_sync_allowed": False,
    "risk_level": "L1_near"
}, ensure_ascii=False))
PY
