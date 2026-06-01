#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/multi_target_dependency_migration_v0_1/migration_targets.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

SOURCE="${SOURCE:-$ROOT_DIR}"
PLAN_DIR="$SOURCE/Taiji_Governance/progress"
PLAN_JSONL="$PLAN_DIR/multi_target_dependency_migration_plan_2026-05-11.jsonl"
SUMMARY="$PLAN_DIR/multi_target_dependency_migration_summary_2026-05-11.md"

mkdir -p "$PLAN_DIR"
: > "$PLAN_JSONL"

classify() {
  local rel="$1"
  case "$rel" in
    keys/*|*.key|*.pem|*token*|*secret*|*credential*|*credentials*|*service_account*.json|*oauth*.json)
      echo "secret_excluded"
      ;;
    Taiji_Odoo/postgres_data/*|Taiji_Odoo/odoo_data/*)
      echo "db_volume_excluded"
      ;;
    .taiji_runtime*/*|*/runtime.log|*/runtime_audit.jsonl)
      echo "runtime_state_excluded"
      ;;
    data/*.db|data/**/*.db)
      echo "local_data_db_optional"
      ;;
    docs/*|Taiji_Governance/*|schemas/*|tests/*|examples/*)
      echo "governance_cloud_safe"
      ;;
    deploy/*|runtime_adapters/*|services/*|scripts/*|security/*|Taiji_AutoBuild/*|Taiji_Vector_Runtime_Lite/*)
      echo "runtime_dependency"
      ;;
    legacy_core/*|core/*|edge/*|models/*|*.py|*.sh|*.yml|*.yaml|*.json|Dockerfile*|docker-compose*.yml|requirements*.txt)
      echo "linux_runtime_source"
      ;;
    *)
      echo "archive_only_review"
      ;;
  esac
}

cd "$SOURCE"

find . -type f \
  ! -path './.git/*' \
  ! -path './__pycache__/*' \
  ! -path './.pytest_cache/*' \
  ! -path './.venv/*' \
  ! -path './node_modules/*' \
  -print0 | sort -z | while IFS= read -r -d '' path; do
    rel="${path#./}"
    category="$(classify "$rel")"
    sha="$(sha256sum "$rel" | awk '{print $1}')"
    printf '{"path":"%s","category":"%s","sha256":"sha256:%s","secret_material_printed":false}\n' \
      "$rel" "$category" "$sha" >> "$PLAN_JSONL"
  done

cat > "$SUMMARY" <<EOF
# Multi-Target Dependency Migration Summary

Date: 2026-05-11

Source:

\`\`\`text
$SOURCE
\`\`\`

Targets:

\`\`\`text
Linux: $LINUX_TARGET
D archive: $D_ARCHIVE_TARGET
Cloud staging: $CLOUD_STAGE_TARGET
\`\`\`

Plan:

\`\`\`text
$PLAN_JSONL
\`\`\`

Secret policy:

- secret paths are listed by path/hash only if encountered
- secret contents are not printed
- cloud staging excludes secrets, DB volumes, runtime state, and local data DB

EOF

echo "plan_written=$PLAN_JSONL"
echo "summary_written=$SUMMARY"
