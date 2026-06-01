#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/dependency_relocation_v0_1/relocation.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PLAN_DIR="$SOURCE_ROOT/Taiji_Governance/system_info"
PLAN_JSONL="$PLAN_DIR/dependency_relocation_plan_2026-05-12.jsonl"
PLAN_MD="$PLAN_DIR/dependency_relocation_plan_2026-05-12.md"

mkdir -p "$PLAN_DIR"
: > "$PLAN_JSONL"

classify() {
  local rel="$1"
  case "$rel" in
    docs/*|Taiji_Governance/policies/*|Taiji_Governance/schemas/*|Taiji_Governance/progress/*|schemas/*|tests/*|examples/*|runtime_adapters/*|site/taiji_system_dashboard/*|deploy/packages/taiji_formal_tensor_runtime_v0_1_0/*|deploy/migration/*|services/gateway/policies/*)
      echo "cloud_readonly_dependency"
      ;;
    Taiji_Governance/identity/*|Taiji_Governance/runtime/*|Taiji_AutoBuild/*|Taiji_Vector_Runtime_Lite/*|services/gateway/*|services/clow_adapter/*|Taiji_Odoo/addons/*|Taiji_Odoo/scripts/*)
      echo "local_runtime_dependency"
      ;;
    *)
      echo "review_or_archive"
      ;;
  esac
}

is_excluded() {
  local rel="$1"
  case "$rel" in
    .git/*|.secrets/*|keys/*|data/secrets/*|data/service_account_memory/*|*.env|.env|*.key|*.pem|*token*|*secret*|*credential*|*credentials*|*service_account*.json|*oauth*.json|Taiji_Odoo/postgres_data/*|Taiji_Odoo/odoo_data/*|Taiji_Governance/system_info/dependency_relocation_*|Taiji_Governance/system_info/dependency_links_*|Taiji_Governance/system_info/Taiji_Dependency_Cloud_Readonly_*|__pycache__/*|*/__pycache__/*|.pytest_cache/*|node_modules/*|.venv*/*|taiji_env/*|open_webui_data/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

cd "$SOURCE_ROOT"

find docs Taiji_Governance schemas tests examples runtime_adapters site deploy services Taiji_AutoBuild Taiji_Vector_Runtime_Lite Taiji_Odoo/addons Taiji_Odoo/scripts -type f 2>/dev/null | sort | while IFS= read -r rel; do
  if is_excluded "$rel"; then
    continue
  fi
  category="$(classify "$rel")"
  sha="$(sha256sum "$rel" | awk '{print $1}')"
  cloud_allowed=false
  d_allowed=true
  local_allowed=true
  if [ "$category" = "cloud_readonly_dependency" ]; then
    cloud_allowed=true
  fi
  printf '{"path":"%s","category":"%s","sha256":"sha256:%s","five_code":{"intent":"dependency_relocation","resource":"file","time":"2026-05-12","authority":"source_to_targets_only","topology":"linux_to_cloud_local_dlock"},"targets":{"cloud_allowed":%s,"local_allowed":%s,"d_lock_allowed":%s},"reverse_sync_allowed":false,"secret_material_included":false}\n' \
    "$rel" "$category" "$sha" "$cloud_allowed" "$local_allowed" "$d_allowed" >> "$PLAN_JSONL"
done

cat > "$PLAN_MD" <<EOF
# Dependency Relocation Plan

Version: 2026-05-12

## Source

\`\`\`text
$SOURCE_ROOT
\`\`\`

## Targets

\`\`\`text
Cloud staging: $CLOUD_STAGE
Local dependency workspace: $LOCAL_DEP_TARGET
D controlled folder: $D_LOCK_TARGET
Google Drive target: $GOOGLE_DRIVE_TARGET_URL
\`\`\`

## Rule

\`\`\`text
雙地五維碼映射，一處單向非同步寫入。
source -> targets only.
reverse sync is blocked.
\`\`\`

## Plan JSONL

\`\`\`text
$PLAN_JSONL
\`\`\`

## Secret Handling

Secret-like paths, keys, env files, Odoo/Postgres live volumes, caches, and virtual environments are excluded.

EOF

echo "plan_jsonl=$PLAN_JSONL"
echo "plan_md=$PLAN_MD"
