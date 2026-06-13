#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub
python3 -m json.tool "packets/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.json" >/dev/null
grep -q "COMPLIANCE_SETTINGS_GENERATIVE_WRITE_READY" "docs/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.md"
grep -q "admin@wuchang.life" "docs/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.md"
grep -q "wuchang.life" "docs/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.md"
grep -q "DNS health = HOLD" "docs/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.md"
grep -q "本會看統計，不看個資" "docs/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.md"
sha256sum -c "docs/evidence/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.sha256"
echo "STATE=PASS_VERIFY"
