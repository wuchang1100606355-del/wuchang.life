#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub
python3 -m json.tool "packets/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.json" >/dev/null
grep -q "MASTER_DEPLOY_INDEX_READY" "docs/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.md"
grep -q "Five-in-One Generative Deploy" "docs/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.md"
grep -q "Redteam Paste Integrity Gate" "docs/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.md"
grep -q "W3_GENERATIVE_TRANSFER_DEPLOY_20260621" "docs/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.md"
grep -q "w3_generative_transfer_deploy" "packets/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.json"
sha256sum -c "docs/evidence/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.sha256"
scripts/verify/verify_W3_GENERATIVE_TRANSFER_DEPLOY_20260621.sh
echo "STATE=PASS_VERIFY"
