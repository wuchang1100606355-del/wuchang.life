#!/usr/bin/env bash
set -euo pipefail

latest_intent_id=""
selected_task_id=""
selected_source=""
selected_carrier=""
current_attachment_designated=""
live_state_checked=""
old_context_role=""

emit() {
  printf 'STATE=%s\n' "$1"
  printf 'LATEST_INTENT_ID=%s\n' "${latest_intent_id:-LOCALIZED_UNKNOWN}"
  printf 'SELECTED_TASK_ID=%s\n' "${selected_task_id:-LOCALIZED_UNKNOWN}"
  printf 'SELECTED_CONTEXT_SOURCE=%s\n' "${selected_source:-LOCALIZED_UNKNOWN}"
  printf 'SELECTED_CONTEXT_CARRIER=%s\n' "${selected_carrier:-LOCALIZED_UNKNOWN}"
  printf 'OLD_CONTEXT_ROLE=%s\n' "${old_context_role:-LOCALIZED_UNKNOWN}"
  printf 'decision=%s\n' "$2"
}

run_self_test() {
  local script="$0"
  local output status

  status=0
  output="$("$script" \
    --latest-intent-id ROUTING_FIX \
    --selected-task-id ROUTING_FIX \
    --selected-source LATEST_EXPLICIT_USER_INTENT \
    --selected-carrier INLINE_CURRENT_TURN \
    --current-attachment-designated false \
    --live-state-checked true \
    --old-context-role EVIDENCE_ONLY)" || status=$?
  [[ "$status" -eq 0 ]] || return 1
  grep -Fxq 'STATE=PASS_CURRENT_TASK_CONTEXT' <<<"$output" || return 1

  status=0
  output="$("$script" \
    --latest-intent-id ROUTING_FIX \
    --selected-task-id ROUTING_FIX \
    --selected-source LATEST_EXPLICIT_USER_INTENT \
    --selected-carrier CURRENT_TURN_ATTACHMENT \
    --current-attachment-designated true \
    --live-state-checked true \
    --old-context-role EVIDENCE_ONLY)" || status=$?
  [[ "$status" -eq 0 ]] || return 1
  grep -Fxq 'STATE=PASS_CURRENT_TASK_CONTEXT' <<<"$output" || return 1

  status=0
  output="$("$script" \
    --latest-intent-id ROUTING_FIX \
    --selected-task-id OLD_REGISTRATION \
    --selected-source ATTACHED_OLD_TASK \
    --selected-carrier HISTORICAL_ATTACHMENT \
    --current-attachment-designated false \
    --live-state-checked true \
    --old-context-role EVIDENCE_ONLY)" || status=$?
  [[ "$status" -eq 1 ]] || return 1
  grep -Fxq 'STATE=HOLD_TASK_CONTEXT_ROLLBACK' <<<"$output" || return 1

  status=0
  output="$("$script" \
    --latest-intent-id ROUTING_FIX \
    --selected-task-id OLD_RUN \
    --selected-source PRIOR_RUN \
    --selected-carrier PRIOR_RUN \
    --current-attachment-designated false \
    --live-state-checked true \
    --old-context-role EVIDENCE_ONLY)" || status=$?
  [[ "$status" -eq 1 ]] || return 1
  grep -Fxq 'STATE=HOLD_TASK_CONTEXT_ROLLBACK' <<<"$output" || return 1

  status=0
  output="$("$script" \
    --latest-intent-id ROUTING_FIX \
    --selected-task-id OLD_REGISTRATION \
    --selected-source LATEST_EXPLICIT_USER_INTENT \
    --selected-carrier INLINE_CURRENT_TURN \
    --current-attachment-designated false \
    --live-state-checked true \
    --old-context-role EVIDENCE_ONLY)" || status=$?
  [[ "$status" -eq 1 ]] || return 1
  grep -Fxq 'STATE=HOLD_TASK_CONTEXT_ROLLBACK' <<<"$output" || return 1

  status=0
  output="$("$script" \
    --latest-intent-id ROUTING_FIX \
    --selected-task-id ROUTING_FIX \
    --selected-source LATEST_EXPLICIT_USER_INTENT \
    --selected-carrier INLINE_CURRENT_TURN \
    --current-attachment-designated false \
    --live-state-checked false \
    --old-context-role EVIDENCE_ONLY)" || status=$?
  [[ "$status" -eq 1 ]] || return 1
  grep -Fxq 'STATE=HOLD_TASK_CONTEXT_ROLLBACK' <<<"$output" || return 1

  status=0
  output="$("$script" \
    --latest-intent-id ROUTING_FIX \
    --selected-task-id ROUTING_FIX \
    --selected-source LATEST_EXPLICIT_USER_INTENT \
    --selected-carrier INLINE_CURRENT_TURN \
    --current-attachment-designated false \
    --live-state-checked true \
    --old-context-role EXECUTION_AUTHORITY)" || status=$?
  [[ "$status" -eq 1 ]] || return 1
  grep -Fxq 'STATE=HOLD_TASK_CONTEXT_ROLLBACK' <<<"$output" || return 1


  # Reuse remains legal: current instruction owns the task; old results are evidence.
  status=0
  output="$("$script" \
    --latest-intent-id REUSE_VERIFIED_RESULT \
    --selected-task-id REUSE_VERIFIED_RESULT \
    --selected-source LATEST_EXPLICIT_USER_INTENT \
    --selected-carrier INLINE_CURRENT_TURN \
    --current-attachment-designated false \
    --live-state-checked true \
    --old-context-role EVIDENCE_ONLY)" || status=$?
  [[ "$status" -eq 0 ]] || return 1
  grep -Fxq 'STATE=PASS_CURRENT_TASK_CONTEXT' <<<"$output" || return 1

  # A shell caller using errexit must not reach an action after HOLD.
  # The marker is stdout only; no runtime or filesystem mutation is performed.
  status=0
  output="$(bash -c 'set -e; "$1" --unknown-argument; echo ACTION_REACHED' _ "$script")" || status=$?
  [[ "$status" -eq 1 ]] || return 1
  grep -Fxq 'STATE=HOLD_TASK_CONTEXT_ROLLBACK' <<<"$output" || return 1
  if grep -Fxq 'ACTION_REACHED' <<<"$output"; then
    return 1
  fi

  echo 'STATE=PASS_TASK_CONTEXT_PRECEDENCE_GATE_SELF_TEST'
}

if [[ "${1:-}" == "--self-test" ]]; then
  run_self_test
  exit 0
fi

while (($#)); do
  case "$1" in
    --latest-intent-id) latest_intent_id="${2:-}"; shift 2 ;;
    --selected-task-id) selected_task_id="${2:-}"; shift 2 ;;
    --selected-source) selected_source="${2:-}"; shift 2 ;;
    --selected-carrier) selected_carrier="${2:-}"; shift 2 ;;
    --current-attachment-designated) current_attachment_designated="${2:-}"; shift 2 ;;
    --live-state-checked) live_state_checked="${2:-}"; shift 2 ;;
    --old-context-role) old_context_role="${2:-}"; shift 2 ;;
    *) emit HOLD_TASK_CONTEXT_ROLLBACK 'task-context gate received an unknown argument'; exit 1 ;;
  esac
done

case "$selected_source" in
  LATEST_EXPLICIT_USER_INTENT|CURRENT_LIVE_STATE|CURRENT_VALID_AUTHORITY|PRIOR_RUN|ATTACHED_OLD_TASK) ;;
  *) emit HOLD_TASK_CONTEXT_ROLLBACK 'selected context source is missing or invalid'; exit 1 ;;
esac

case "$selected_carrier" in
  INLINE_CURRENT_TURN|CURRENT_TURN_ATTACHMENT|HISTORICAL_ATTACHMENT|PRIOR_RUN|SYSTEM_STATE) ;;
  *) emit HOLD_TASK_CONTEXT_ROLLBACK 'selected context carrier is missing or invalid'; exit 1 ;;
esac

for value in "$current_attachment_designated" "$live_state_checked"; do
  case "$value" in
    true|false) ;;
    *) emit HOLD_TASK_CONTEXT_ROLLBACK 'task-context boolean input is invalid'; exit 1 ;;
  esac
done

case "$old_context_role" in
  EVIDENCE_ONLY|EXECUTION_AUTHORITY) ;;
  *) emit HOLD_TASK_CONTEXT_ROLLBACK 'old context role is missing or invalid'; exit 1 ;;
esac

if [[ -z "$latest_intent_id" || -z "$selected_task_id" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'latest or selected task coordinate is missing'
  exit 1
fi

if [[ "$old_context_role" != "EVIDENCE_ONLY" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'old attachment and prior run must remain evidence only'
  exit 1
fi

if [[ "$selected_source" == "PRIOR_RUN" || "$selected_source" == "ATTACHED_OLD_TASK" || \
      "$selected_carrier" == "HISTORICAL_ATTACHMENT" || "$selected_carrier" == "PRIOR_RUN" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'a prior run or historical attachment was selected as the current task'
  exit 1
fi

if [[ "$selected_source" != "LATEST_EXPLICIT_USER_INTENT" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'live state and authority constrain execution but cannot replace the latest intent'
  exit 1
fi

if [[ "$selected_carrier" == "CURRENT_TURN_ATTACHMENT" && "$current_attachment_designated" != "true" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'the current-turn attachment was not explicitly designated as the request'
  exit 1
fi

if [[ "$selected_carrier" != "INLINE_CURRENT_TURN" && "$selected_carrier" != "CURRENT_TURN_ATTACHMENT" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'the latest explicit intent must come from the current user turn'
  exit 1
fi

if [[ "$selected_task_id" != "$latest_intent_id" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'selected task does not match the latest explicit user intent'
  exit 1
fi

if [[ "$live_state_checked" != "true" ]]; then
  emit HOLD_TASK_CONTEXT_ROLLBACK 'current live state has not been checked'
  exit 1
fi

emit PASS_CURRENT_TASK_CONTEXT 'latest explicit user intent selected; old contexts remain evidence only'
