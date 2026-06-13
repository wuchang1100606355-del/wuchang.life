#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub
python3 -m json.tool "packets/redteam/operation_windows/REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.json" >/dev/null
grep -q "REDTEAM_PASTE_INTEGRITY_GATE_READY" "docs/redteam/operation_windows/REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.md"
grep -q "REDTEAM_PARTIAL_FAIL" "docs/redteam/operation_windows/REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.md"
grep -q "貼上污染一律 HOLD" "docs/redteam/operation_windows/REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.md"
sha256sum -c "docs/evidence/redteam/operation_windows/REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.sha256"
echo "STATE=PASS_VERIFY"
