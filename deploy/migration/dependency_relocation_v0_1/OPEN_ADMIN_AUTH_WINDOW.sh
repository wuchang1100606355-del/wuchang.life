#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/dependency_relocation_v0_1/relocation.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

ACCOUNT="admin@wuchang.life"
AUTH_URL="https://accounts.google.com/AccountChooser?Email=${ACCOUNT}&continue=https%3A%2F%2Fdrive.google.com%2Fdrive%2Ffolders%2F1PwybNATp-pPZ8DJiTEJbga3mJO1p4NCn"
AUDIT_LOG="$SOURCE_ROOT/Taiji_Governance/logs/admin_authorization_window_2026-05-12.jsonl"

mkdir -p "$(dirname "$AUDIT_LOG")"

python3 - <<PY
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

record = {
    "event": "admin_authorization_window_open_requested",
    "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    "account": "admin@wuchang.life",
    "scope": "organization_readonly_cloud_dependency_upload_window",
    "target": "google_drive_folder_1PwybNATp-pPZ8DJiTEJbga3mJO1p4NCn",
    "google_api_called": False,
    "credential_material_read": False,
    "credential_material_stored": False,
    "secret_material_printed": False,
    "human_login_required": True,
    "risk_level": "L1_near",
    "action": "allow_with_audit",
}
Path("$AUDIT_LOG").open("a", encoding="utf-8").write(json.dumps(record, ensure_ascii=False) + "\n")
PY

if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -Command "Start-Process '$AUTH_URL'" >/dev/null 2>&1
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$AUTH_URL" >/dev/null 2>&1
else
  printf '%s\n' "$AUTH_URL"
  exit 0
fi

echo "opened_authorization_window_for=$ACCOUNT"
echo "audit_log=$AUDIT_LOG"
