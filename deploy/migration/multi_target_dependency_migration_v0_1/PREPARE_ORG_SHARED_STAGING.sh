#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/multi_target_dependency_migration_v0_1/org_shared_cloud.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

SOURCE="${SOURCE:-$ROOT_DIR}"
STAGE="${ORG_SHARED_STAGE_TARGET:?}"

mkdir -p \
  "$STAGE/$ORG_SHARED_PROJECT_ROOT/00_README_GOVERNANCE" \
  "$STAGE/$ORG_SHARED_PROJECT_ROOT/01_Whitepaper" \
  "$STAGE/$ORG_SHARED_PROJECT_ROOT/02_Runtime_Schemas" \
  "$STAGE/$ORG_SHARED_PROJECT_ROOT/03_Deployment_Artifacts" \
  "$STAGE/$ORG_SHARED_PROJECT_ROOT/04_Audit_Summaries" \
  "$STAGE/$ORG_SHARED_PROJECT_ROOT/05_Architecture_Dashboards" \
  "$STAGE/$ORG_SHARED_PROJECT_ROOT/90_Archive"

rsync -aH --ignore-existing \
  --exclude='keys/' \
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
  "$SOURCE/docs/" "$STAGE/$ORG_SHARED_PROJECT_ROOT/01_Whitepaper/" 2>/dev/null || true

rsync -aH --ignore-existing \
  "$SOURCE/schemas/" "$STAGE/$ORG_SHARED_PROJECT_ROOT/02_Runtime_Schemas/" 2>/dev/null || true

rsync -aH --ignore-existing \
  --exclude='*.env' \
  --exclude='env.example' \
  "$SOURCE/deploy/packages/" "$STAGE/$ORG_SHARED_PROJECT_ROOT/03_Deployment_Artifacts/packages/" 2>/dev/null || true

rsync -aH --ignore-existing \
  "$SOURCE/runtime_adapters/" "$STAGE/$ORG_SHARED_PROJECT_ROOT/03_Deployment_Artifacts/runtime_adapters/" 2>/dev/null || true

rsync -aH --ignore-existing \
  "$SOURCE/Taiji_Governance/progress/" "$STAGE/$ORG_SHARED_PROJECT_ROOT/05_Architecture_Dashboards/" 2>/dev/null || true

cat > "$STAGE/$ORG_SHARED_PROJECT_ROOT/00_README_GOVERNANCE/ORG_SHARED_SPACE_MANIFEST.json" <<EOF
{
  "org_domain": "$ORG_DOMAIN",
  "shared_space_name": "$ORG_SHARED_SPACE_NAME",
  "project_root": "$ORG_SHARED_PROJECT_ROOT",
  "stage_target": "$STAGE",
  "upload_mode": "$ORG_SHARED_UPLOAD_MODE",
  "cloud_semantics": "non_sensitive_readonly_all_device_accessible",
  "personal_owner_allowed": $ORG_SHARED_ALLOW_PERSONAL_OWNER,
  "anyone_with_link_allowed": $ORG_SHARED_ALLOW_ANYONE_WITH_LINK,
  "secret_upload_allowed": $ORG_SHARED_ALLOW_SECRET_UPLOAD,
  "member_progress_allowed": $ORG_SHARED_ALLOW_MEMBER_PROGRESS,
  "external_api_called": false,
  "cloud_upload_performed": false
}
EOF

find "$STAGE/$ORG_SHARED_PROJECT_ROOT" -type f -print0 | sort -z | xargs -0 sha256sum > "$STAGE/$ORG_SHARED_PROJECT_ROOT/04_Audit_Summaries/org_shared_stage_sha256.txt"

echo "org_shared_stage_ready=$STAGE/$ORG_SHARED_PROJECT_ROOT"
echo "cloud_upload_performed=false"
