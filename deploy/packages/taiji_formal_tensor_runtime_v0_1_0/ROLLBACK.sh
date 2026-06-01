#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PKG="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0"

"$PKG/STOP_LOCAL.sh" || true

rm -f "$ROOT_DIR/runtime_adapters/taiji_formal_tensor_runtime_v0_1_0_adapter.py"
rm -f "$PKG/runtime_entry.py"
rm -f "$PKG/env.example"
rm -f "$PKG/Dockerfile"
rm -f "$PKG/docker-compose.yml"
rm -f "$PKG/systemd.service"
rm -f "$PKG/PREFLIGHT.sh"
rm -f "$PKG/START_LOCAL.sh"
rm -f "$PKG/STOP_LOCAL.sh"
rm -f "$PKG/HEALTH.sh"
rm -f "$PKG/HASH_SCRIPT.sh"
rm -f "$PKG/ROLLBACK.sh"
rm -f "$PKG/MANIFEST.json"
rm -f "$PKG/README_DEPLOY.md"
rm -f "$PKG/SHA256SUMS"

rmdir "$PKG" 2>/dev/null || true
rmdir "$ROOT_DIR/runtime_adapters" 2>/dev/null || true

echo "rollback complete: taiji_formal_tensor_runtime_v0_1_0"
