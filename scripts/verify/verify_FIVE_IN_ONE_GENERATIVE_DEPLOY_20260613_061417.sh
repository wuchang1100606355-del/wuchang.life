#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub
python3 -m json.tool "packets/deploy/five_in_one/FIVE_IN_ONE_GENERATIVE_DEPLOY_20260613_061417.json" >/dev/null
grep -q "GENERATIVE_DEPLOYMENT_PACKET_READY" "docs/deploy/five_in_one/FIVE_IN_ONE_GENERATIVE_DEPLOY_20260613_061417.md"
grep -q "本會看統計，不看個資" "docs/deploy/five_in_one/FIVE_IN_ONE_GENERATIVE_DEPLOY_20260613_061417.md"
sha256sum -c "docs/evidence/deploy/five_in_one/FIVE_IN_ONE_GENERATIVE_DEPLOY_20260613_061417.sha256"
echo "STATE=PASS_VERIFY"
