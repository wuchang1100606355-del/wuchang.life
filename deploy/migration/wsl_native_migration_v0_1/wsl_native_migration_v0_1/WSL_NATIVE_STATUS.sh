#!/usr/bin/env bash
set -euo pipefail

SOURCE="${SOURCE:-/mnt/c/Users/o0930/Taiji_Hub}"
TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"

echo "source=$SOURCE"
if [ -d "$SOURCE" ]; then
  echo "source_exists=true"
else
  echo "source_exists=false"
fi

echo "target=$TARGET"
if [ -d "$TARGET" ]; then
  echo "target_exists=true"
  du -sh "$TARGET" 2>/dev/null || true
else
  echo "target_exists=false"
fi

if mount | grep -q ' /mnt/c '; then
  echo "mnt_c_mounted=true"
else
  echo "mnt_c_mounted=unknown"
fi

echo "current_pwd=$(pwd)"
