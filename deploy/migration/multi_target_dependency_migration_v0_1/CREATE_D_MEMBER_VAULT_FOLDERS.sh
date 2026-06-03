#!/usr/bin/env bash
set -euo pipefail

D_MEMBER_VAULT="${D_MEMBER_VAULT:-/mnt/d/Taiji_Member_Vault}"
APPLY="${APPLY:-0}"

paths=(
  "$D_MEMBER_VAULT/00_ACCESS_REVIEW"
  "$D_MEMBER_VAULT/01_MEMBER_MASTER"
  "$D_MEMBER_VAULT/02_MEMBER_CONTACT"
  "$D_MEMBER_VAULT/03_SERVICE_RECORDS"
  "$D_MEMBER_VAULT/04_MEETING_AUTHORIZATION"
  "$D_MEMBER_VAULT/05_ODOO_IMPORT_REVIEW"
  "$D_MEMBER_VAULT/06_REDACTION_WORKSPACE"
  "$D_MEMBER_VAULT/90_ARCHIVE_SHA256"
)

if [ "$APPLY" != "1" ]; then
  echo "dry_run=true"
  printf 'would_create=%s\n' "${paths[@]}"
  echo "set APPLY=1 to create"
  exit 0
fi

mkdir -p "${paths[@]}"

cat > "$D_MEMBER_VAULT/README_MEMBER_VAULT_BOUNDARY.md" <<'EOF'
# Taiji Member Vault Boundary

This D drive / memory-card area is the protected local member information vault.

It is not cloud staging.
It is not all-device readonly public material.
It is not AI long-term memory.

Access requires:

- owner review
- public-interest metric
- audit record
- SHA256 baseline
- minimum necessary use

Do not place service account JSON, OAuth tokens, private keys, passwords, or
browser cookies here unless a separate credential governance flow explicitly
requires a secure store. Do not upload member plaintext to cloud.
EOF

echo "created=$D_MEMBER_VAULT"
