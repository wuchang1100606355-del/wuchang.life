#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/dependency_relocation_v0_1/relocation.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PLAN_JSONL="$SOURCE_ROOT/Taiji_Governance/system_info/dependency_relocation_plan_2026-05-12.jsonl"
LINKS_CSV="$SOURCE_ROOT/Taiji_Governance/system_info/dependency_links_2026-05-12.csv"
APPLY_LOG="$SOURCE_ROOT/Taiji_Governance/logs/dependency_relocation_apply_2026-05-12.jsonl"

if [ ! -f "$PLAN_JSONL" ]; then
  echo "missing plan: $PLAN_JSONL" >&2
  exit 1
fi

mkdir -p "$CLOUD_STAGE" "$LOCAL_DEP_TARGET" "$(dirname "$APPLY_LOG")"

if [ -d /mnt/d ]; then
  mkdir -p "$D_LOCK_TARGET"
  d_status="ready"
else
  d_status="missing_mount"
fi

printf 'source_path,category,sha256,cloud_path,local_path,d_lock_path,write_direction,reverse_sync_allowed\n' > "$LINKS_CSV"

copy_one() {
  local src="$1"
  local dst="$2"
  mkdir -p "$(dirname "$dst")"
  cp -a "$src" "$dst"
}

while IFS= read -r line; do
  rel="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["path"])')"
  category="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["category"])')"
  sha="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha256"])')"
  cloud_allowed="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["targets"]["cloud_allowed"])')"
  src="$SOURCE_ROOT/$rel"
  cloud_path=""
  local_path="$LOCAL_DEP_TARGET/$rel"
  d_path=""

  copy_one "$src" "$local_path"

  if [ "$cloud_allowed" = "True" ]; then
    cloud_path="$CLOUD_STAGE/$rel"
    copy_one "$src" "$cloud_path"
  fi

  if [ "$d_status" = "ready" ]; then
    d_path="$D_LOCK_TARGET/$rel"
    copy_one "$src" "$d_path"
  else
    d_path="PENDING_D_MOUNT:$D_LOCK_TARGET/$rel"
  fi

  printf '%s,%s,%s,%s,%s,%s,%s,%s\n' "$rel" "$category" "$sha" "$cloud_path" "$local_path" "$d_path" "$WRITE_DIRECTION" "$REVERSE_SYNC_ALLOWED" >> "$LINKS_CSV"
done < "$PLAN_JSONL"

if command -v tar >/dev/null 2>&1; then
  tar -C "$(dirname "$CLOUD_STAGE")" -czf "$SOURCE_ROOT/Taiji_Governance/system_info/Taiji_Dependency_Cloud_Readonly_20260512.tar.gz" "$(basename "$CLOUD_STAGE")"
fi

printf '{"ts":"2026-05-12T00:00:00+08:00","event":"dependency_relocation_applied","cloud_stage":"%s","local_target":"%s","d_lock_target":"%s","d_status":"%s","reverse_sync_allowed":false,"secret_material_included":false,"google_drive_upload_performed":false}\n' \
  "$CLOUD_STAGE" "$LOCAL_DEP_TARGET" "$D_LOCK_TARGET" "$d_status" >> "$APPLY_LOG"

echo "cloud_stage=$CLOUD_STAGE"
echo "local_target=$LOCAL_DEP_TARGET"
echo "d_lock_target=$D_LOCK_TARGET"
echo "d_status=$d_status"
echo "links_csv=$LINKS_CSV"

