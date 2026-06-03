#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/multi_target_dependency_migration_v0_1/migration_targets.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

if [ "$CLOUD_STAGE_TARGET" = "/" ] || [ "$D_ARCHIVE_TARGET" = "/" ]; then
  echo "refusing unsafe target" >&2
  exit 1
fi

rm -rf "$CLOUD_STAGE_TARGET"
echo "removed_cloud_stage=$CLOUD_STAGE_TARGET"
echo "D archive and Linux workspace are not removed by this script"
