#!/usr/bin/env bash
set -euo pipefail

SOURCE="${SOURCE:-/mnt/c/Users/o0930/Taiji_Hub}"
TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"

if [ ! -d "$SOURCE" ]; then
  echo "source missing: $SOURCE" >&2
  exit 1
fi

mkdir -p "$TARGET"

copy_path() {
  local rel="$1"
  if [ -e "$SOURCE/$rel" ]; then
    mkdir -p "$(dirname "$TARGET/$rel")"
    cp -a "$SOURCE/$rel" "$TARGET/$rel"
    echo "synced: $rel"
  else
    echo "missing in source, skipped: $rel" >&2
  fi
}

copy_path "schemas/formal_tensor_packet.schema.json"
copy_path "schemas/pos_service_intent.schema.json"
copy_path "schemas/tensor_packet.schema.json"
copy_path "services/gateway/policies/formal_tensor_validator.py"
copy_path "tests/test_formal_tensor_validator.py"
copy_path "tests/test_runtime_entry.py"
copy_path "runtime_adapters/formal_tensor_runtime_adapter_v0_1.py"
copy_path "runtime_adapters/taiji_formal_tensor_runtime_v0_1_0_adapter.py"
copy_path "runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py"
copy_path "deploy/packages/taiji_formal_tensor_runtime_v0_1_0"
copy_path "deploy/migration/wsl_native_migration_v0_1"

echo "runtime_artifact_sync_complete"
