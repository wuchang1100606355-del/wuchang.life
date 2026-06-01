#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT="$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/SHA256SUMS"

sha256sum \
  "$ROOT_DIR/runtime_adapters/formal_tensor_runtime_adapter_v0_1.py" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/env.example" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/Dockerfile" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/docker-compose.yml" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/systemd/taiji-formal-runtime-pkg-v0-1.service" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/preflight_v0_1.sh" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/start_v0_1.sh" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/health_v0_1.sh" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/stop_v0_1.sh" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/rollback_v0_1.sh" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/hash_manifest_v0_1.sh" \
  "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/MANIFEST.md" \
  > "$OUT"

cat "$OUT"
