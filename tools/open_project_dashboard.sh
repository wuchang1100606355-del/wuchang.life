#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/taiji_admin/Taiji_Hub"
cd "$ROOT" || exit 1

echo "=== regenerate project board ==="
python3 tools/project_board_generator.py

echo
echo "=== regenerate worklinks ==="
python3 tools/worklink_builder.py

echo
echo "=== regenerate dashboard ==="
python3 tools/project_dashboard_generator.py

HTML="docs/project/PROJECT_DASHBOARD.html"

echo
echo "=== open dashboard ==="
echo "file://wsl.localhost/Ubuntu/home/taiji_admin/Taiji_Hub/$HTML"

if command -v wslpath >/dev/null 2>&1 && command -v explorer.exe >/dev/null 2>&1; then
  explorer.exe "$(wslpath -w "$HTML")" >/dev/null 2>&1 || true
fi

echo
echo "=== status ==="
git status --short -- \
  docs/project/PROJECT_CONTROL_BOARD.md \
  docs/project/WORKLINKS.md \
  docs/project/PROJECT_DASHBOARD.html

echo
echo "DONE: dashboard regenerated and opened."
