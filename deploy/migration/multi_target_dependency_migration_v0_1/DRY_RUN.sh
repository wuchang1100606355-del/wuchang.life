#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/multi_target_dependency_migration_v0_1/migration_targets.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

SOURCE="${SOURCE:-$ROOT_DIR}"

rsync_common=(
  -aHn
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

echo "== dry-run Linux native =="
rsync "${rsync_common[@]}" "$SOURCE/" "$LINUX_TARGET/"

echo "== dry-run D archive =="
rsync "${rsync_common[@]}" "$SOURCE/" "$D_ARCHIVE_TARGET/"

echo "== dry-run cloud staging =="
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

echo "dry_run_complete"
