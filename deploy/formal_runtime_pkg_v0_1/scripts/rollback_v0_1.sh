#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

"$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/stop_v0_1.sh" || true

rm -f "$ROOT_DIR/runtime_adapters/formal_tensor_runtime_adapter_v0_1.py"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/env.example"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/Dockerfile"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/docker-compose.yml"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/systemd/taiji-formal-runtime-pkg-v0-1.service"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/preflight_v0_1.sh"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/start_v0_1.sh"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/health_v0_1.sh"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/stop_v0_1.sh"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/hash_manifest_v0_1.sh"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/MANIFEST.md"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/SHA256SUMS"
rm -f "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts/rollback_v0_1.sh"

rmdir "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/scripts" 2>/dev/null || true
rmdir "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/systemd" 2>/dev/null || true
rmdir "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1" 2>/dev/null || true
rmdir "$ROOT_DIR/runtime_adapters" 2>/dev/null || true

echo "rollback complete for formal runtime package v0.1"
