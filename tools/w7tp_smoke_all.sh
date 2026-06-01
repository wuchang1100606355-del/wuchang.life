#!/usr/bin/env bash
set +e

ROOT="/home/taiji_admin/Taiji_Hub"
cd "$ROOT" || exit 1

TS="$(date +%Y%m%d_%H%M%S)"
REPORT="runtime/reports/w7tp_smoke_all_${TS}.md"
JSONL="runtime/reports/w7tp_smoke_all_${TS}.jsonl"

mkdir -p runtime/reports runtime/proofs

PASS=0
FAIL=0
SKIP=0

run_check() {
  local id="$1"
  local name="$2"
  local cmd="$3"

  echo "## $id｜$name" >> "$REPORT"
  echo >> "$REPORT"
  echo '```bash' >> "$REPORT"
  echo "$cmd" >> "$REPORT"
  echo '```' >> "$REPORT"
  echo >> "$REPORT"

  OUT="$(bash -lc "$cmd" 2>&1)"
  RC=$?

  if [ "$RC" -eq 0 ]; then
    STATUS="PASS"
    PASS=$((PASS+1))
  else
    STATUS="FAIL"
    FAIL=$((FAIL+1))
  fi

  printf '{"id":"%s","name":"%s","status":"%s","rc":%s}\n' "$id" "$name" "$STATUS" "$RC" >> "$JSONL"

  echo "**Status:** \`$STATUS\`  " >> "$REPORT"
  echo "**RC:** \`$RC\`" >> "$REPORT"
  echo >> "$REPORT"
  echo '```text' >> "$REPORT"
  echo "$OUT" | tail -80 >> "$REPORT"
  echo '```' >> "$REPORT"
  echo >> "$REPORT"
}

skip_check() {
  local id="$1"
  local name="$2"
  local reason="$3"
  SKIP=$((SKIP+1))
  printf '{"id":"%s","name":"%s","status":"SKIP","reason":"%s"}\n' "$id" "$name" "$reason" >> "$JSONL"
  {
    echo "## $id｜$name"
    echo
    echo "**Status:** \`SKIP\`"
    echo
    echo "$reason"
    echo
  } >> "$REPORT"
}

{
  echo "# W7TP Smoke All"
  echo
  echo "- Generated: \`$(date -Iseconds)\`"
  echo "- Mode: no SSH / no restart / no router login / no DB write"
  echo
} > "$REPORT"

# M01 EAMTP basic files
run_check "M01" "EAMTP canonical files" \
  "test -f docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md && test -f schemas/eamtp_7d_packet.schema.json && test -f runtime/router/eamtp_7d_translator.py && test -f runtime/dead_letter/eamtp_policy_gate.py"

# M02 Router guard
run_check "M02" "Router guard dry-run file" \
  "test -f runtime/router/eamtp_router_guard_dryrun.py && python3 -m py_compile runtime/router/eamtp_router_guard_dryrun.py"

# M03 Merlin intent driver
run_check "M03" "Merlin intent driver compile" \
  "test -f runtime/router/merlin_intent_driver.py && python3 -m py_compile runtime/router/merlin_intent_driver.py"

# M04 Merlin apply queue
run_check "M04" "Merlin apply queue compile" \
  "test -f runtime/router/merlin_apply_queue.py && python3 -m py_compile runtime/router/merlin_apply_queue.py"

# M05 Approval gate
run_check "M05" "Merlin approval gate compile" \
  "test -f runtime/router/merlin_approval_gate.py && python3 -m py_compile runtime/router/merlin_approval_gate.py"

# M06 Human checklist
run_check "M06" "Merlin checklist compile" \
  "test -f runtime/router/merlin_human_execution_checklist.py && python3 -m py_compile runtime/router/merlin_human_execution_checklist.py"

# M07 Result recorder
run_check "M07" "Merlin result recorder help" \
  "python3 runtime/router/merlin_execution_result_recorder.py --help >/tmp/w7tp_m07_help.txt && head -40 /tmp/w7tp_m07_help.txt"

# M08 Merlin inventory spec files
run_check "M08" "Merlin inventory spec files" \
  "test -f docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md && test -f configs/merlin/router_inventory_redacted.template.json && test -f configs/merlin/README.md"

# M09 Validator + adapter
run_check "M09" "Merlin validator and adapter compile" \
  "python3 -m py_compile tools/merlin_inventory_validator.py tools/merlin_inventory_to_eamtp.py"

# M10 HA mesh analyzer
run_check "M10" "HA mesh analyzer dry-run" \
  "python3 tools/ha_mesh_script_analyzer.py --file tools/ha_mesh_script_analyzer.py --dry-run >/tmp/w7tp_m10.json && python3 - <<'PY'
import json
obj=json.load(open('/tmp/w7tp_m10.json'))
print(obj.get('decision'))
PY"

# M11 Causal ledger builder
run_check "M11" "Causal ledger low-risk packet" \
  "python3 runtime/router/w7tp_causal_event_builder.py --summary 'smoke metadata only' >/tmp/w7tp_m11.json && python3 - <<'PY'
import json
obj=json.load(open('/tmp/w7tp_m11.json'))
assert obj['policy']['decision'] == 'allow_low_risk'
print(obj['policy']['decision'])
PY"

# M12 Inventory fill helper
run_check "M12" "Merlin inventory fill helper dry-run" \
  "python3 tools/merlin_inventory_fill_helper.py --dry-run --set admin_surface.ssh_scope=lan_only"

# M13 Service health readonly
run_check "M13" "Readonly service health" \
  "python3 tools/service_health_readonly.py >/tmp/w7tp_m13.json && python3 - <<'PY'
import json
obj=json.load(open('/tmp/w7tp_m13.json'))
print('ok', obj.get('ok'), 'total', obj.get('total'))
PY"

# M14 Runtime shadow inventory
run_check "M14" "Runtime shadow inventory no-doc" \
  "python3 tools/runtime_shadow_inventory.py --no-doc --limit 10 >/tmp/w7tp_m14.json && python3 - <<'PY'
import json
obj=json.load(open('/tmp/w7tp_m14.json'))
print(obj.get('decision'), obj.get('file_count'), obj.get('total_size'))
PY"

# M15 EAMTP packet summarizer
run_check "M15" "EAMTP packet summarizer" \
  "python3 tools/eamtp_packet_summarizer.py >/tmp/w7tp_m15.json && python3 - <<'PY'
import json
obj=json.load(open('/tmp/w7tp_m15.json'))
print(obj.get('decision'), obj.get('count'))
PY"

{
  echo "## Summary"
  echo
  echo "- PASS: \`$PASS\`"
  echo "- FAIL: \`$FAIL\`"
  echo "- SKIP: \`$SKIP\`"
  echo "- JSONL: \`$JSONL\`"
} >> "$REPORT"

sha256sum "$REPORT" "$JSONL" > "runtime/proofs/w7tp_smoke_all_${TS}.sha256"

echo "REPORT=$REPORT"
echo "JSONL=$JSONL"
echo "PASS=$PASS FAIL=$FAIL SKIP=$SKIP"

if [ "$FAIL" -eq 0 ]; then
  exit 0
else
  exit 2
fi
