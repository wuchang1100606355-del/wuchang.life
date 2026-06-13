#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub
python3 -m json.tool "packets/compliance/network/LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.json" >/dev/null
grep -q "LOCAL_NETWORK_COMPLIANCE_ADDENDUM_READY" "docs/compliance/network/LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.md"
grep -q "中華電信固定 IP" "docs/compliance/network/LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.md"
grep -q "ASUS DDNS" "docs/compliance/network/LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.md"
grep -q "固定 IP 與 ASUS DDNS 是入口資源" "docs/compliance/network/LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.md"
sha256sum -c "docs/evidence/compliance/network/LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.sha256"
echo "STATE=PASS_VERIFY"
