#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SNAPSHOT_TAR="$ROOT/Taiji_Governance/snapshots/snapshot_20260512T180017+0800/taiji_hub_safe_snapshot_20260512T180017+0800.tar.gz"
if [[ "${CONFIRM_ROLLBACK:-}" != "YES" ]]; then
  echo "Refusing rollback without CONFIRM_ROLLBACK=YES"
  echo "This overlays safe snapshot files only; DB volumes and secrets are not included."
  exit 2
fi
if [[ ! -f "$SNAPSHOT_TAR" ]]; then
  echo "Missing snapshot tar: $SNAPSHOT_TAR" >&2
  exit 1
fi
BACKUP_DIR="$ROOT/Taiji_Governance/rollback_points/pre_rollback_backup_$(date +%Y%m%dT%H%M%S%z)"
mkdir -p "$BACKUP_DIR"
cp -a "$ROOT/Taiji_Governance" "$BACKUP_DIR/Taiji_Governance.before" 2>/dev/null || true
cp -a "$ROOT/Taiji_Odoo/addons" "$BACKUP_DIR/Taiji_Odoo_addons.before" 2>/dev/null || true
tar -xzf "$SNAPSHOT_TAR" -C "$ROOT"
echo "rollback_overlay_complete"
echo "pre_rollback_backup=$BACKUP_DIR"
