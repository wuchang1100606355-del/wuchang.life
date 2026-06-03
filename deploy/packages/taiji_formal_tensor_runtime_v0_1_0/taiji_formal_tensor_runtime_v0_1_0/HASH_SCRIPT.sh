#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PKG="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0"

sha256sum \
  "$ROOT_DIR/runtime_adapters/taiji_formal_tensor_runtime_v0_1_0_adapter.py" \
  "$PKG/runtime_entry.py" \
  "$PKG/env.example" \
  "$PKG/Dockerfile" \
  "$PKG/docker-compose.yml" \
  "$PKG/systemd.service" \
  "$PKG/PREFLIGHT.sh" \
  "$PKG/START_LOCAL.sh" \
  "$PKG/STOP_LOCAL.sh" \
  "$PKG/HEALTH.sh" \
  "$PKG/HASH_SCRIPT.sh" \
  "$PKG/ROLLBACK.sh" \
  "$PKG/MANIFEST.json" \
  "$PKG/README_DEPLOY.md" \
  > "$PKG/SHA256SUMS"

cat "$PKG/SHA256SUMS"
