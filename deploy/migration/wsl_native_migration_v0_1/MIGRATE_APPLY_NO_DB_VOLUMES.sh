#!/usr/bin/env bash
set -euo pipefail

SOURCE="${SOURCE:-/mnt/c/Users/o0930/Taiji_Hub}"
TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"
APPLY="${APPLY:-0}"

if [ "$APPLY" != "1" ]; then
  echo "refusing to copy without APPLY=1" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync missing. Install with: sudo apt install rsync" >&2
  exit 1
fi

mkdir -p "$TARGET"

rsync -aH --no-times --info=stats2,name1 \
  --exclude='.git/' \
  --exclude='.taiji_runtime*/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='.venv/' \
  --exclude='node_modules/' \
  --exclude='Taiji_Odoo/postgres_data/' \
  --exclude='Taiji_Odoo/odoo_data/' \
  --exclude='.env' \
  --exclude='*.env' \
  --exclude='*.key' \
  --exclude='*.pem' \
  --exclude='*token*' \
  --exclude='*secret*' \
  --exclude='*credential*' \
  --exclude='*credentials*' \
  --exclude='*service_account*.json' \
  --exclude='*oauth*.json' \
  "$SOURCE/" "$TARGET/"

cat > "$TARGET/.taiji_migration_source.json" <<EOF
{
  "migration_package": "wsl_native_migration_v0_1",
  "mode": "no_db_volumes",
  "source": "$SOURCE",
  "target": "$TARGET",
  "excluded_db_volumes": true,
  "delete_source": false,
  "secret_material_printed": false,
  "services_started": false
}
EOF

echo "copy_complete_no_db_volumes"
