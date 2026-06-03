#!/usr/bin/env bash
set -euo pipefail

SOURCE="${SOURCE:-/mnt/c/Users/o0930/Taiji_Hub}"
TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync missing. Install with: sudo apt install rsync" >&2
  exit 1
fi

if [ ! -d "$SOURCE" ]; then
  echo "source missing: $SOURCE" >&2
  exit 1
fi

echo "dry_run=true"
echo "source=$SOURCE"
echo "target=$TARGET"

rsync -aHAXn --info=stats2,name1 \
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

echo "dry_run_complete"
