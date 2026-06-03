#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CREATED="$ROOT_DIR/Taiji_Governance/system_info/host_restructure/taiji01_host_restructure_created_2026-05-12.txt"

if [ ! -f "$CREATED" ]; then
  echo "nothing_to_rollback: missing $CREATED"
  exit 0
fi

tac "$CREATED" | while IFS= read -r path; do
  if [ -f "$path" ]; then
    rm -f "$path"
    echo "removed=$path"
  fi
done

echo "rollback_complete_source_untouched"
