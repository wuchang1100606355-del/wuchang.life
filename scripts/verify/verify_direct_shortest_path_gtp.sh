#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ACCOUNT_AI_SKILL_ROOT="/home/taiji_admin/.codex/skills/account-ai-conversation-governance"
TRACE_FILE_SKILL_ROOT="/home/taiji_admin/.codex/skills/trace-file-8d-adi-causality"

fail() {
  echo "STATE=HOLD_VERIFY"
  echo "reason=$1"
  exit 1
}

[ -f AGENTS.md ] || fail "AGENTS.md missing"
[ -x scripts/verify/verify_completed_work_reuse_gate.sh ] || fail "completed-work reuse gate missing or not executable"
[ -x scripts/verify/verify_skill_first_gate.sh ] || fail "skill-first gate missing or not executable"
[ -f "$ACCOUNT_AI_SKILL_ROOT/SKILL.md" ] || fail "account AI conversation governance skill missing"
[ -x "$ACCOUNT_AI_SKILL_ROOT/scripts/preflight.py" ] || fail "account AI conversation skill preflight missing or not executable"
[ -x "$ACCOUNT_AI_SKILL_ROOT/scripts/backend_exec.py" ] || fail "account AI conversation backend executor missing or not executable"
[ -f "$ACCOUNT_AI_SKILL_ROOT/config/account_ai_sources.json" ] || fail "account AI source registry missing"
[ -f "$ACCOUNT_AI_SKILL_ROOT/references/source_registry.schema.json" ] || fail "account AI source registry schema missing"
[ -x "$ACCOUNT_AI_SKILL_ROOT/scripts/inventory_metadata.py" ] || fail "account AI metadata inventory parser missing or not executable"
[ -x "$ACCOUNT_AI_SKILL_ROOT/scripts/verify_coverage.py" ] || fail "account AI coverage verifier missing or not executable"
[ -f "$ACCOUNT_AI_SKILL_ROOT/tests/test_capabilities.py" ] || fail "account AI capability tests missing"
[ -f "$TRACE_FILE_SKILL_ROOT/SKILL.md" ] || fail "trace-file skill missing"
grep -Fq 'account-ai-conversation-governance' "$TRACE_FILE_SKILL_ROOT/SKILL.md" \
  || fail "trace-file skill lacks conversation-inventory routing boundary"

required_terms=(
  "Direct Shortest Path Rule"
  "Generative Transfer Priority Gate"
  "Main Chain Rule"
  "Redteam Rule"
  "No Detour Rule"
  "W3_GENERATIVE_TRANSFER_DEPLOY"
  "STATE=HOLD_MAIN_CHAIN_DEVIATION"
  "Completed Work Reuse Hard Gate"
  "PRIOR_RESULT_STATUS"
  "PRIOR_RUN_ID"
  "PRIOR_RESULT_REF"
  "PRIOR_SCOPE_ID"
  "REQUESTED_SCOPE_ID"
  "SCOPE_RELATION"
  "DELTA_TRIGGER"
  "REPEAT_AUTHORIZATION"
  "OUTPUT_POLICY"
  "DATA_KIND"
  "CONTENT_OUTPUT_AUTHORIZATION"
  "STATE=HOLD_PRIOR_RESULT_COORDINATE_REQUIRED"
  "STATE=REUSE_PRIOR_COMPLETED_WORK"
  "STATE=CONTINUE_UNCOVERED_SCOPE_ONLY"
  "限定範圍沒有命中，不等於全域不存在"
  "ERROR_DUPLICATE_COMPLETED_WORK"
  "技能優先執行硬閘"
  "SKILL_MATCH_STATUS"
  "MATCHED_SKILLS"
  "SELECTED_SKILLS"
  "SKILL_CAN_COMPLETE"
  "SKILL_READ_COMPLETE"
  "SKILL_EXECUTION_REQUIRED"
  "STATE=HOLD_APPLICABLE_SKILL_NOT_USED"
  "人工智慧對話資料輸出硬閘"
  "REQUIRED_SKILL=account-ai-conversation-governance"
  "STATE=HOLD_CONTENT_OUTPUT_NOT_AUTHORIZED"
  "全系統、本帳號所轄全部人工智慧"
  "ACCOUNT_ORGANIZATION_SPACES"
  "HOLD_ACCOUNT_ORGANIZATION_SPACES_UNRESOLVED"
)

for term in "${required_terms[@]}"; do
  grep -Fq "$term" AGENTS.md || fail "missing required term: $term"
done

if grep -Eq 'sk-[A-Za-z0-9_-]{10,}|AIza[A-Za-z0-9_-]{10,}|[Bb]earer[[:space:]]+[A-Za-z0-9._~+/=-]{10,}|BEGIN PRIVATE KEY' AGENTS.md; then
  fail "raw key pattern found in AGENTS.md"
fi

if grep -Eq '身分證|身份證|電話|地址|生日|電子信箱|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' AGENTS.md; then
  fail "member PII marker found in AGENTS.md"
fi

scripts/verify/verify_completed_work_reuse_gate.sh --self-test \
  | grep -Fq 'STATE=PASS_COMPLETED_WORK_REUSE_GATE_SELF_TEST' \
  || fail "completed-work reuse gate self-test failed"

scripts/verify/verify_skill_first_gate.sh --self-test \
  | grep -Fq 'STATE=PASS_SKILL_FIRST_GATE_SELF_TEST' \
  || fail "skill-first gate self-test failed"

backend_output="$(TMPDIR=/dev/shm $ACCOUNT_AI_SKILL_ROOT/scripts/backend_exec.py -- /usr/bin/printf 'PRIVATE_BACKEND_TEST_MARKER')"
grep -Fq '"state": "PASS_BACKEND_EXECUTION"' <<<"$backend_output" \
  || fail "skill backend execution failed"
grep -Fq '"raw_output_returned": false' <<<"$backend_output" \
  || fail "skill backend did not suppress raw output"
if grep -Fq 'PRIVATE_BACKEND_TEST_MARKER' <<<"$backend_output"; then
  fail "skill backend leaked raw output"
fi

skill_preflight_output="$($ACCOUNT_AI_SKILL_ROOT/scripts/preflight.py \
  --workspace-root "$ROOT" \
  --prior-status REUSABLE \
  --prior-run-id PRIOR-LOCAL-COVERAGE \
  --prior-result-ref task://prior-local-coverage \
  --prior-scope-id TAIJI01_AND_MSI_LOCAL_AI \
  --requested-scope-id ACCOUNT_ALL_AI_ALL_SYSTEMS \
  --scope-relation PRIOR_SUBSET \
  --prior-stage READ_ALL_NODE_CONVERSATIONS \
  --requested-stage READ_ALL_NODE_CONVERSATIONS \
  --delta-trigger NONE \
  --repeat-authorization false \
  --user-said-done true \
  --backend-execution true \
  --raw-tool-output-frontend false \
  --data-kind AI_CONVERSATION \
  --output-policy METADATA_ONLY \
  --content-output-authorization false)"
grep -Fq '"state": "CONTINUE_UNCOVERED_SCOPE_ONLY"' <<<"$skill_preflight_output" \
  || fail "skill preflight did not preserve prior subset coverage"

python3 -m json.tool "$ACCOUNT_AI_SKILL_ROOT/config/account_ai_sources.json" >/dev/null \
  || fail "account AI source registry is not valid JSON"

skill_test_output="$(TMPDIR=/dev/shm $ACCOUNT_AI_SKILL_ROOT/scripts/backend_exec.py -- \
  /usr/bin/env TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/python3 "$ACCOUNT_AI_SKILL_ROOT/tests/test_capabilities.py" -q)"
grep -Fq '"state": "PASS_BACKEND_EXECUTION"' <<<"$skill_test_output" \
  || fail "account AI capability tests failed"
grep -Fq '"raw_output_returned": false' <<<"$skill_test_output" \
  || fail "account AI capability tests exposed raw output"

echo "STATE=PASS_VERIFY"
