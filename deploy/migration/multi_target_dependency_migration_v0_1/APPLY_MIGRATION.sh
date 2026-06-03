#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/multi_target_dependency_migration_v0_1/migration_targets.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

SOURCE="${SOURCE:-$ROOT_DIR}"
APPLY="${APPLY:-0}"

if [ "$APPLY" != "1" ]; then
  echo "refusing to apply without APPLY=1" >&2
  exit 1
fi

if [ "${ALLOW_CLOUD_UPLOAD:-false}" = "true" ]; then
  echo "cloud upload is not implemented in this package; staging only" >&2
  exit 1
fi

rsync_common=(
  -aH
  --info=stats2,name1
  --ignore-existing
  --exclude='.git/'
  --exclude='__pycache__/'
  --exclude='.pytest_cache/'
  --exclude='.venv/'
  --exclude='node_modules/'
  --exclude='.taiji_runtime*/'
  --exclude='Taiji_Odoo/postgres_data/'
  --exclude='Taiji_Odoo/odoo_data/'
  --exclude='keys/'
  --exclude='*.key'
  --exclude='*.pem'
  --exclude='*token*'
  --exclude='*secret*'
  --exclude='*credential*'
  --exclude='*credentials*'
  --exclude='*service_account*.json'
  --exclude='*oauth*.json'
)

mkdir -p "$LINUX_TARGET" "$D_ARCHIVE_TARGET" "$CLOUD_STAGE_TARGET"

echo "== apply Linux native =="
rsync "${rsync_common[@]}" "$SOURCE/" "$LINUX_TARGET/"

echo "== apply D archive =="
rsync "${rsync_common[@]}" "$SOURCE/" "$D_ARCHIVE_TARGET/"

echo "== apply cloud staging =="
rsync "${rsync_common[@]}" \
  --exclude='data/' \
  --exclude='models/' \
  --exclude='archive/' \
  --include='docs/***' \
  --include='Taiji_Governance/***' \
  --include='schemas/***' \
  --include='tests/***' \
  --include='examples/***' \
  --include='deploy/***' \
  --include='runtime_adapters/***' \
  --include='services/***' \
  --exclude='*' \
  "$SOURCE/" "$CLOUD_STAGE_TARGET/"

cat > "$LINUX_TARGET/.taiji_multi_target_migration.json" <<EOF
{
  "migration_package": "multi_target_dependency_migration_v0_1",
  "source": "$SOURCE",
  "linux_target": "$LINUX_TARGET",
  "d_archive_target": "$D_ARCHIVE_TARGET",
  "cloud_stage_target": "$CLOUD_STAGE_TARGET",
  "secret_material_printed": false,
  "cloud_upload_performed": false,
  "production_started": false
}
EOF

echo "apply_complete"
