#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-/home/taiji_admin/Taiji_Hub}"
OUT_DIR="$ROOT/W7TP_FIELD_ATLAS/gei_context/snapshot_outputs"
TS="$(date +%Y%m%d_%H%M%S)"
YAML_OUT="$OUT_DIR/gei_context_snapshot_${TS}.yaml"
MD_OUT="$OUT_DIR/gei_context_snapshot_${TS}.md"

mkdir -p "$OUT_DIR"

HOST_NOW="$(hostname)"
USER_NOW="$(whoami)"
GIT_BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || echo UNKNOWN)"
GIT_HEAD="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo UNKNOWN)"
STATUS_SUMMARY="$(git -C "$ROOT" status --short 2>/dev/null | wc -l | tr -d ' ')"

cat > "$YAML_OUT" <<YAML
snapshot_id: GEI_CONTEXT_SNAPSHOT_${TS}
status: CONTEXT_ONLY
timestamp: $(date -Is)
host: ${HOST_NOW}
user: ${USER_NOW}
root: ${ROOT}

git:
  branch: ${GIT_BRANCH}
  head: ${GIT_HEAD}
  changed_file_count: ${STATUS_SUMMARY}

refs:
  universe_event_registry: W7TP_FIELD_ATLAS/00_universe_event_registry.yaml
  universe_registry: W7TP_FIELD_ATLAS/01_universe_registry.yaml
  governed_hive_master_index: W7TP_FIELD_ATLAS/02_governed_hive_master_index.yaml
  governed_hive_task_board: W7TP_FIELD_ATLAS/task_boards/W7TP_GOVERNED_HIVE_TASK_BOARD_V1.yaml
  gei_context_index: W7TP_FIELD_ATLAS/gei_context/W7TP_GEI_CONTEXT_INDEX_V1.yaml

governance:
  context_only: true
  no_secret_read: true
  no_runtime_write: true
  no_db_write: true
  no_service_restart: true

decision_level:
  level: L0_NOTE
  can_authorize_action: false

red_team_reflection:
  negative_effects:
    - snapshot_may_become_stale
    - snapshot_must_not_be_treated_as_runtime_truth
  mitigation:
    - include_host_git_head_timestamp
    - require_decision_packet_for_actions
YAML

cat > "$MD_OUT" <<MD
# GEI Context Snapshot

- snapshot_id: GEI_CONTEXT_SNAPSHOT_${TS}
- status: CONTEXT_ONLY
- timestamp: $(date -Is)
- host: ${HOST_NOW}
- user: ${USER_NOW}
- root: ${ROOT}
- git_branch: ${GIT_BRANCH}
- git_head: ${GIT_HEAD}
- changed_file_count: ${STATUS_SUMMARY}

## References

- W7TP_FIELD_ATLAS/00_universe_event_registry.yaml
- W7TP_FIELD_ATLAS/01_universe_registry.yaml
- W7TP_FIELD_ATLAS/02_governed_hive_master_index.yaml
- W7TP_FIELD_ATLAS/task_boards/W7TP_GOVERNED_HIVE_TASK_BOARD_V1.yaml
- W7TP_FIELD_ATLAS/gei_context/W7TP_GEI_CONTEXT_INDEX_V1.yaml

## Boundary

This snapshot is context only. It does not authorize copy, sync, restart, deploy, DB write, or secret access.
MD

ln -sfn "$YAML_OUT" "$OUT_DIR/latest_gei_context_snapshot.yaml"
ln -sfn "$MD_OUT" "$OUT_DIR/latest_gei_context_snapshot.md"

echo "GEI_SNAPSHOT_YAML=$YAML_OUT"
echo "GEI_SNAPSHOT_MD=$MD_OUT"
