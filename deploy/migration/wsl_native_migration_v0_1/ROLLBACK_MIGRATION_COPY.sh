#!/usr/bin/env bash
set -euo pipefail

TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"

if [ "$TARGET" = "/" ] || [ "$TARGET" = "/home" ] || [ "$TARGET" = "/mnt/c/Users/o0930/Taiji_Hub" ]; then
  echo "refusing unsafe rollback target: $TARGET" >&2
  exit 1
fi

if [ ! -f "$TARGET/.taiji_migration_source.json" ]; then
  echo "refusing rollback because migration marker is missing: $TARGET/.taiji_migration_source.json" >&2
  exit 1
fi

echo "rollback_target=$TARGET"
echo "This removes only the migrated Linux-native copy, not the Windows source."
rm -rf "$TARGET"
echo "rollback_complete"
