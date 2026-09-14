#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法：verify_completed_work_reuse_gate.sh \
  --prior-status REUSABLE|INCOMPLETE|NOT_FOUND \
  --prior-run-id VALUE \
  --prior-result-ref VALUE \
  --prior-scope-id VALUE \
  --requested-scope-id VALUE \
  --scope-relation EXACT|PRIOR_SUBSET|DISJOINT|UNKNOWN \
  --prior-stage VALUE \
  --requested-stage VALUE \
  --delta-trigger NONE|USER_EXPLICIT_RERUN|NEW_AUTHORITY_DECISION|SOURCE_CHANGED|PRIOR_VERIFIER_FAILED \
  --repeat-authorization true|false \
  --user-said-done true|false \
  --output-policy METADATA_ONLY|CONTENT_EXPLICITLY_AUTHORIZED|NOT_APPLICABLE \
  --data-kind AI_CONVERSATION|OTHER \
  --content-output-authorization true|false
EOF
}

emit() {
  local state="$1"
  local decision="$2"
  printf 'STATE=%s\n' "$state"
  printf 'PRIOR_RUN_ID=%s\n' "${prior_run_id:-LOCALIZED_UNKNOWN}"
  printf 'PRIOR_RESULT_REF=%s\n' "${prior_result_ref:-LOCALIZED_UNKNOWN}"
  printf 'decision=%s\n' "$decision"
}

run_self_test() {
  local script="$0"
  local output

  output="$($script \
    --prior-status REUSABLE \
    --prior-run-id RUN-1 \
    --prior-result-ref task://result-1 \
    --prior-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --requested-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --scope-relation EXACT \
    --prior-stage READ_ALL_NODE_CONVERSATIONS \
    --requested-stage READ_ALL_NODE_CONVERSATIONS \
    --delta-trigger NONE \
    --repeat-authorization false \
    --user-said-done true \
    --output-policy METADATA_ONLY \
    --data-kind AI_CONVERSATION \
    --content-output-authorization false)"
  grep -Fq 'STATE=REUSE_PRIOR_COMPLETED_WORK' <<<"$output"

  output="$($script \
    --prior-status NOT_FOUND \
    --prior-run-id '' \
    --prior-result-ref '' \
    --prior-scope-id UNKNOWN \
    --requested-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --scope-relation UNKNOWN \
    --prior-stage READ_ALL_NODE_CONVERSATIONS \
    --requested-stage READ_ALL_NODE_CONVERSATIONS \
    --delta-trigger NONE \
    --repeat-authorization false \
    --user-said-done true \
    --output-policy METADATA_ONLY \
    --data-kind AI_CONVERSATION \
    --content-output-authorization false)"
  grep -Fq 'STATE=HOLD_PRIOR_RESULT_COORDINATE_REQUIRED' <<<"$output"

  output="$($script \
    --prior-status REUSABLE \
    --prior-run-id RUN-1 \
    --prior-result-ref task://result-1 \
    --prior-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --requested-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --scope-relation EXACT \
    --prior-stage READ_ALL_NODE_CONVERSATIONS \
    --requested-stage READ_ALL_NODE_CONVERSATIONS \
    --delta-trigger SOURCE_CHANGED \
    --repeat-authorization true \
    --user-said-done true \
    --output-policy METADATA_ONLY \
    --data-kind AI_CONVERSATION \
    --content-output-authorization false)"
  grep -Fq 'STATE=PASS_REPEAT_AUTHORIZED' <<<"$output"

  output="$($script \
    --prior-status REUSABLE \
    --prior-run-id RUN-1 \
    --prior-result-ref task://result-1 \
    --prior-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --requested-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --scope-relation EXACT \
    --prior-stage READ_ALL_NODE_CONVERSATIONS \
    --requested-stage APPLY_EXISTING_DEVICE_SETTINGS \
    --delta-trigger NONE \
    --repeat-authorization false \
    --user-said-done true \
    --output-policy NOT_APPLICABLE \
    --data-kind OTHER \
    --content-output-authorization false)"
  grep -Fq 'STATE=PASS_NEW_STAGE' <<<"$output"

  output="$($script \
    --prior-status REUSABLE \
    --prior-run-id RUN-LOCAL \
    --prior-result-ref task://local-result \
    --prior-scope-id TAIJI01_AND_MSI_LOCAL_AI \
    --requested-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --scope-relation PRIOR_SUBSET \
    --prior-stage READ_ALL_NODE_CONVERSATIONS \
    --requested-stage READ_ALL_NODE_CONVERSATIONS \
    --delta-trigger NONE \
    --repeat-authorization false \
    --user-said-done true \
    --output-policy METADATA_ONLY \
    --data-kind AI_CONVERSATION \
    --content-output-authorization false)"
  grep -Fq 'STATE=CONTINUE_UNCOVERED_SCOPE_ONLY' <<<"$output"

  output="$($script \
    --prior-status NOT_FOUND \
    --prior-run-id '' \
    --prior-result-ref '' \
    --prior-scope-id NONE \
    --requested-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
    --scope-relation DISJOINT \
    --prior-stage NONE \
    --requested-stage READ_ALL_NODE_CONVERSATIONS \
    --delta-trigger NONE \
    --repeat-authorization false \
    --user-said-done false \
    --output-policy CONTENT_EXPLICITLY_AUTHORIZED \
    --data-kind AI_CONVERSATION \
    --content-output-authorization false)"
  grep -Fq 'STATE=HOLD_CONTENT_OUTPUT_NOT_AUTHORIZED' <<<"$output"

  echo 'STATE=PASS_COMPLETED_WORK_REUSE_GATE_SELF_TEST'
}

if [[ "${1:-}" == "--self-test" ]]; then
  run_self_test
  exit 0
fi

prior_status=""
prior_run_id=""
prior_result_ref=""
prior_scope_id=""
requested_scope_id=""
scope_relation=""
prior_stage=""
requested_stage=""
delta_trigger=""
repeat_authorization=""
user_said_done=""
output_policy=""
data_kind=""
content_output_authorization=""

while (($#)); do
  case "$1" in
    --prior-status) prior_status="${2:-}"; shift 2 ;;
    --prior-run-id) prior_run_id="${2:-}"; shift 2 ;;
    --prior-result-ref) prior_result_ref="${2:-}"; shift 2 ;;
    --prior-scope-id) prior_scope_id="${2:-}"; shift 2 ;;
    --requested-scope-id) requested_scope_id="${2:-}"; shift 2 ;;
    --scope-relation) scope_relation="${2:-}"; shift 2 ;;
    --prior-stage) prior_stage="${2:-}"; shift 2 ;;
    --requested-stage) requested_stage="${2:-}"; shift 2 ;;
    --delta-trigger) delta_trigger="${2:-}"; shift 2 ;;
    --repeat-authorization) repeat_authorization="${2:-}"; shift 2 ;;
    --user-said-done) user_said_done="${2:-}"; shift 2 ;;
    --output-policy) output_policy="${2:-}"; shift 2 ;;
    --data-kind) data_kind="${2:-}"; shift 2 ;;
    --content-output-authorization) content_output_authorization="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 64 ;;
  esac
done

case "$prior_status" in
  REUSABLE|INCOMPLETE|NOT_FOUND) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '先前成果狀態無效'; exit 0 ;;
esac

case "$delta_trigger" in
  NONE|USER_EXPLICIT_RERUN|NEW_AUTHORITY_DECISION|SOURCE_CHANGED|PRIOR_VERIFIER_FAILED) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '變更理由無效'; exit 0 ;;
esac

case "$repeat_authorization" in
  true|false) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '重做授權值無效'; exit 0 ;;
esac

case "$user_said_done" in
  true|false) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '使用者已完成聲明值無效'; exit 0 ;;
esac

case "$scope_relation" in
  EXACT|PRIOR_SUBSET|DISJOINT|UNKNOWN) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '作用域關係無效'; exit 0 ;;
esac

case "$output_policy" in
  METADATA_ONLY|CONTENT_EXPLICITLY_AUTHORIZED|NOT_APPLICABLE) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '輸出規則無效'; exit 0 ;;
esac

case "$data_kind" in
  AI_CONVERSATION|OTHER) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '資料種類無效'; exit 0 ;;
esac

case "$content_output_authorization" in
  true|false) ;;
  *) emit HOLD_REUSE_GATE_INVALID_INPUT '對話正文輸出授權值無效'; exit 0 ;;
esac

if [[ "$data_kind" == "AI_CONVERSATION" ]]; then
  if [[ "$output_policy" == "NOT_APPLICABLE" ]]; then
    emit HOLD_CONTENT_OUTPUT_NOT_AUTHORIZED '人工智慧對話資料必須明確指定只輸出中繼資料或具備正文授權'
    exit 0
  fi
  if [[ "$output_policy" == "CONTENT_EXPLICITLY_AUTHORIZED" && "$content_output_authorization" != "true" ]]; then
    emit HOLD_CONTENT_OUTPUT_NOT_AUTHORIZED '沒有目前命令的明確授權，禁止輸出人工智慧對話正文'
    exit 0
  fi
fi

if [[ -z "$prior_stage" || -z "$requested_stage" ]]; then
  emit HOLD_REUSE_GATE_INVALID_INPUT '先前階段與要求階段不得空白'
  exit 0
fi

if [[ -z "$prior_scope_id" || -z "$requested_scope_id" ]]; then
  emit HOLD_REUSE_GATE_INVALID_INPUT '先前作用域與要求作用域不得空白'
  exit 0
fi

if [[ "$prior_status" == "NOT_FOUND" ]]; then
  if [[ "$user_said_done" == "true" ]]; then
    emit HOLD_PRIOR_RESULT_COORDINATE_REQUIRED '使用者已聲明工作完成；必須找回成果座標，不得重新搜尋'
  else
    emit PASS_NO_PRIOR_RESULT '未聲明且未找到可沿用的既有成果'
  fi
  exit 0
fi

if [[ "$prior_status" == "INCOMPLETE" ]]; then
  emit CONTINUE_PRIOR_INCOMPLETE_RESULT '從既有檢查點繼續，不得重新開始取得資料'
  exit 0
fi

if [[ "$scope_relation" == "UNKNOWN" ]]; then
  emit HOLD_PRIOR_RESULT_COORDINATE_REQUIRED '無法證明作用域關係；不得重掃或宣告整體完成'
  exit 0
fi

if [[ "$scope_relation" == "PRIOR_SUBSET" ]]; then
  emit CONTINUE_UNCOVERED_SCOPE_ONLY '沿用已完成的局部成果，只處理尚未覆蓋的全系統來源'
  exit 0
fi

if [[ "$scope_relation" == "DISJOINT" ]]; then
  emit PASS_NEW_STAGE '要求作用域與既有成果不重疊'
  exit 0
fi

if [[ -z "$prior_run_id" || -z "$prior_result_ref" ]]; then
  emit HOLD_PRIOR_RESULT_COORDINATE_REQUIRED '既有成果缺少可找回的執行編號或成果座標'
  exit 0
fi

if [[ "$prior_stage" != "$requested_stage" ]]; then
  emit PASS_NEW_STAGE '要求的是不同後續階段，不是重做已完成階段'
  exit 0
fi

if [[ "$delta_trigger" == "NONE" ]]; then
  emit REUSE_PRIOR_COMPLETED_WORK '相同階段已完成且沒有有效變更；必須沿用既有成果'
  exit 0
fi

if [[ "$repeat_authorization" != "true" ]]; then
  emit HOLD_REPEAT_AUTHORIZATION_REQUIRED '雖有變更理由，但沒有明確重做授權'
  exit 0
fi

emit PASS_REPEAT_AUTHORIZED '有效變更與明確重做授權同時存在，才允許重跑相同階段'
