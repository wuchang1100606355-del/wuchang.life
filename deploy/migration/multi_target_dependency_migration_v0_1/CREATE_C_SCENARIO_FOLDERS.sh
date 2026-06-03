#!/usr/bin/env bash
set -euo pipefail

C_SCENARIO_ROOT="${C_SCENARIO_ROOT:-/mnt/c/Users/o0930/Taiji_Data}"
APPLY="${APPLY:-0}"

paths=(
  "$C_SCENARIO_ROOT/group_members"
  "$C_SCENARIO_ROOT/merchant_operations"
  "$C_SCENARIO_ROOT/condo_committee_meetings"
  "$C_SCENARIO_ROOT/community_service_cases"
  "$C_SCENARIO_ROOT/odoo_import_staging"
  "$C_SCENARIO_ROOT/pos_business_records"
  "$C_SCENARIO_ROOT/meeting_minutes_private"
  "$C_SCENARIO_ROOT/export_review"
  "$C_SCENARIO_ROOT/redacted_cloud_candidates"
)

if [ "$APPLY" != "1" ]; then
  echo "dry_run=true"
  printf 'would_create=%s\n' "${paths[@]}"
  echo "set APPLY=1 to create"
  exit 0
fi

mkdir -p "${paths[@]}"

cat > "$C_SCENARIO_ROOT/README_TAIJI_DATA_BOUNDARY.md" <<'EOF'
# Taiji Data Boundary

This C drive folder is for frequently read/write scenario data.

It may contain group-member operational data, merchant operation data, condo
committee meeting information, Odoo import staging, and POS business records.

It is not an organization readonly cloud folder.
It is not a D drive high-authority special-purpose archive.

Cloud flow:

C scenario data -> redact/summarize -> export_review -> redacted_cloud_candidates -> owner review -> org readonly cloud staging

Do not place general secrets, private keys, OAuth tokens, service account JSON,
or passwords here.

Do not directly sync plaintext personal data, business confidential data, or
meeting-sensitive data to cloud.
EOF

echo "created=$C_SCENARIO_ROOT"

