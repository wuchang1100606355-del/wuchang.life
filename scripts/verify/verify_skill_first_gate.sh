#!/usr/bin/env bash
set -euo pipefail

emit() {
  printf 'STATE=%s\n' "$1"
  printf 'decision=%s\n' "$2"
}

self_test() {
  local script="$0"
  local output

  output="$($script \
    --matched-skills account-ai-conversation-governance \
    --selected-skills account-ai-conversation-governance \
    --skill-can-complete FULL \
    --skill-read-complete true \
    --skill-execution-required true \
    --named-skill-requested false \
    --named-skill-available true)"
  grep -Fq 'STATE=PASS_SKILL_EXECUTION_REQUIRED' <<<"$output"

  output="$($script \
    --matched-skills account-ai-conversation-governance \
    --selected-skills NONE \
    --skill-can-complete FULL \
    --skill-read-complete false \
    --skill-execution-required false \
    --named-skill-requested false \
    --named-skill-available true)"
  grep -Fq 'STATE=HOLD_APPLICABLE_SKILL_NOT_USED' <<<"$output"

  output="$($script \
    --matched-skills NONE \
    --selected-skills NONE \
    --skill-can-complete NO_MATCH \
    --skill-read-complete false \
    --skill-execution-required false \
    --named-skill-requested false \
    --named-skill-available true)"
  grep -Fq 'STATE=PASS_NO_APPLICABLE_SKILL' <<<"$output"

  output="$($script \
    --matched-skills missing-skill \
    --selected-skills NONE \
    --skill-can-complete NO_MATCH \
    --skill-read-complete false \
    --skill-execution-required false \
    --named-skill-requested true \
    --named-skill-available false)"
  grep -Fq 'STATE=HOLD_NAMED_SKILL_MISSING' <<<"$output"

  echo 'STATE=PASS_SKILL_FIRST_GATE_SELF_TEST'
}

if [[ "${1:-}" == "--self-test" ]]; then
  self_test
  exit 0
fi

matched_skills=""
selected_skills=""
skill_can_complete=""
skill_read_complete=""
skill_execution_required=""
named_skill_requested=""
named_skill_available=""

while (($#)); do
  case "$1" in
    --matched-skills) matched_skills="${2:-}"; shift 2 ;;
    --selected-skills) selected_skills="${2:-}"; shift 2 ;;
    --skill-can-complete) skill_can_complete="${2:-}"; shift 2 ;;
    --skill-read-complete) skill_read_complete="${2:-}"; shift 2 ;;
    --skill-execution-required) skill_execution_required="${2:-}"; shift 2 ;;
    --named-skill-requested) named_skill_requested="${2:-}"; shift 2 ;;
    --named-skill-available) named_skill_available="${2:-}"; shift 2 ;;
    *) emit HOLD_SKILL_GATE_INVALID_INPUT '技能優先硬閘收到無效參數'; exit 0 ;;
  esac
done

case "$skill_can_complete" in
  FULL|PARTIAL|NO_MATCH) ;;
  *) emit HOLD_SKILL_GATE_INVALID_INPUT '技能完成能力判定無效'; exit 0 ;;
esac

for value in "$skill_read_complete" "$skill_execution_required" "$named_skill_requested" "$named_skill_available"; do
  case "$value" in
    true|false) ;;
    *) emit HOLD_SKILL_GATE_INVALID_INPUT '技能布林判定值無效'; exit 0 ;;
  esac
done

if [[ "$named_skill_requested" == "true" && "$named_skill_available" != "true" ]]; then
  emit HOLD_NAMED_SKILL_MISSING '使用者指定的技能不存在或不可讀，禁止假裝使用'
  exit 0
fi

if [[ -z "$matched_skills" || -z "$selected_skills" ]]; then
  emit HOLD_SKILL_GATE_INVALID_INPUT '技能比對與選用結果不得空白'
  exit 0
fi

if [[ "$matched_skills" == "NONE" ]]; then
  if [[ "$selected_skills" != "NONE" || "$skill_can_complete" != "NO_MATCH" ]]; then
    emit HOLD_SKILL_GATE_INVALID_INPUT '沒有適用技能時不得虛構技能選用'
    exit 0
  fi
  emit PASS_NO_APPLICABLE_SKILL '沒有適用技能，才可使用一般最小執行路徑'
  exit 0
fi

if [[ "$selected_skills" != "$matched_skills" ]]; then
  emit HOLD_APPLICABLE_SKILL_NOT_USED '適用技能未全部選用'
  exit 0
fi

if [[ "$skill_can_complete" == "NO_MATCH" || "$skill_read_complete" != "true" || "$skill_execution_required" != "true" ]]; then
  emit HOLD_APPLICABLE_SKILL_NOT_USED '適用技能未完整讀取或未安排依技能執行'
  exit 0
fi

emit PASS_SKILL_EXECUTION_REQUIRED '適用技能已完整讀取，後續必須依技能執行'
