#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/multi_target_dependency_migration_v0_1/migration_targets.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

check_file() {
  local base="$1"
  local rel="$2"
  if [ ! -f "$base/$rel" ]; then
    echo "missing: $base/$rel" >&2
    exit 1
  fi
}

check_file "$LINUX_TARGET" "deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL_V011.sh"
check_file "$LINUX_TARGET" "runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py"
check_file "$LINUX_TARGET" "services/gateway/policies/formal_tensor_validator.py"
check_file "$LINUX_TARGET" "schemas/formal_tensor_packet.schema.json"
check_file "$D_ARCHIVE_TARGET" "Taiji_Governance/progress/taiji_hub_architecture_completion_dashboard_v2026-05-11.md"
check_file "$CLOUD_STAGE_TARGET" "Taiji_Governance/progress/taiji_hub_architecture_completion_dashboard_v2026-05-11.md"

mkdir -p "$LINUX_TARGET/Taiji_Governance/progress"

find "$LINUX_TARGET/deploy" "$LINUX_TARGET/runtime_adapters" "$LINUX_TARGET/schemas" "$LINUX_TARGET/services" "$LINUX_TARGET/tests" \
  -type f -print0 | sort -z | xargs -0 sha256sum > "$LINUX_TARGET/Taiji_Governance/progress/multi_target_linux_runtime_sha256_2026-05-11.txt"

find "$CLOUD_STAGE_TARGET" -type f -print0 | sort -z | xargs -0 sha256sum > "$LINUX_TARGET/Taiji_Governance/progress/multi_target_cloud_stage_sha256_2026-05-11.txt"

echo "verify_ok"
echo "linux_hash=$LINUX_TARGET/Taiji_Governance/progress/multi_target_linux_runtime_sha256_2026-05-11.txt"
echo "cloud_stage_hash=$LINUX_TARGET/Taiji_Governance/progress/multi_target_cloud_stage_sha256_2026-05-11.txt"
