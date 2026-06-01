#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "=== VERIFY FINAL GOVERNANCE BASELINE ==="

test -f prompts/FINAL_WUCHANG_GOVERNANCE_PREFIX.md
test -f contexts/current/FINAL_ACTIVE_GOVERNANCE_BASELINE.md
test -f contexts/ai_metric/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json
test -f contexts/current/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json
test -f .ai/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json
test -f contexts/human/WORKLOG.md

grep -R "Ω0 ⊕ I0 ⊕ SA7 ⊕ W6" prompts/FINAL_WUCHANG_GOVERNANCE_PREFIX.md >/dev/null
grep -R "BACKGROUND_EFFECTIVE" contexts/current/FINAL_ACTIVE_GOVERNANCE_BASELINE.md >/dev/null
grep -R "BLOCKED_WITH_SAFE_ALTERNATIVE" contexts/ai_metric/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json >/dev/null
grep -R "小 J 以拒絕越界證明忠誠" prompts/FINAL_WUCHANG_GOVERNANCE_PREFIX.md >/dev/null
grep -R "Final Governance Baseline Integrated" contexts/human/WORKLOG.md >/dev/null

echo "OK: FINAL_GOVERNANCE_BASELINE_BACKGROUND_EFFECTIVE"
