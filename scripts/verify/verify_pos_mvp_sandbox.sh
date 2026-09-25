#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub
export POS_MVP_RUN_DIR="${POS_MVP_RUN_DIR:-/home/taiji_admin/Taiji_Hub/runtime/sandbox/pos_mvp_autodev_run}"

python3 runtime/sandbox/pos_mvp_autodev/verify/verify_pos_mvp_sandbox.py

route_output="$(python3 runtime/gt8d_lookup/gt8d_route_resolver.py --route "POS 點餐 菜單 訂單 本地還原 order_candidate")"
grep -q "ROUTE_CODE=ODOO_POS_ACTION" <<<"$route_output"
grep -q "LOCAL_RECONSTRUCTION_REQUIRED=TRUE" <<<"$route_output"
grep -q "DB_WRITE=FALSE" <<<"$route_output"

python3 -m json.tool runtime/sandbox/pos_mvp_autodev/menu/menu.json >/dev/null
python3 -m json.tool packets/pos_mvp/POS_MVP_SANDBOX_PACKET.json >/dev/null
sha256sum -c "$POS_MVP_RUN_DIR/evidence/sha256_manifest.txt"

echo "STATE=POS_MVP_SANDBOX_AUTODEV_PASS"
