#!/usr/bin/env bash
set -euo pipefail

SOURCE="${SOURCE:-/mnt/c/Users/o0930/Taiji_Hub}"
TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"
APPLY="${APPLY:-0}"

if [ "$APPLY" != "1" ]; then
  echo "refusing to copy without APPLY=1" >&2
  echo "run: APPLY=1 bash deploy/migration/wsl_native_migration_v0_1/MIGRATE_APPLY.sh" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync missing. Install with: sudo apt install rsync" >&2
  exit 1
fi

if [ ! -d "$SOURCE" ]; then
  echo "source missing: $SOURCE" >&2
  exit 1
fi

mkdir -p "$TARGET"

echo "copy_start"
echo "source=$SOURCE"
echo "target=$TARGET"

rsync -aHAX --info=stats2,name1 \
  --ignore-existing \
  --exclude='.git/' \
  --exclude='.taiji_runtime*/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='.venv/' \
  --exclude='node_modules/' \
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
  "source": "$SOURCE",
  "target": "$TARGET",
  "delete_source": false,
  "overwrite_existing_files": false,
  "secret_material_printed": false,
  "services_started": false
}
EOF

echo "copy_complete"
