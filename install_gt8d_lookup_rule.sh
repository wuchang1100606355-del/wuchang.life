#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(pwd)}"
cd "$ROOT"
test -f config/gt8d_lookup/route_table.json || { echo STATE=MISSING_ROUTE_TABLE; exit 2; }
test -f runtime/gt8d_lookup/gt8d_route_resolver.py || { echo STATE=MISSING_RESOLVER; exit 2; }
chmod +x runtime/gt8d_lookup/gt8d_route_resolver.py
printf "STATE=GT8D_RULE_APPLY_CHECK\nHOST=%s\nROOT=%s\n\n" "$(hostname)" "$ROOT"
python3 runtime/gt8d_lookup/gt8d_route_resolver.py --mode local "會員要用 LINE WORKS 通知，但雲端只回候選結果，本地還原"
printf "\n---\n"
python3 runtime/gt8d_lookup/gt8d_route_resolver.py --mode local "請把 Odoo POS 候選動作轉 7D 封包，不要寫資料庫"
printf "\nSTATE=GT8D_RULE_APPLY_PASS\nSECRET_READ=FALSE\nMEMBER_PLAINTEXT_READ=FALSE\nDB_WRITE=FALSE\nSERVICE_RESTART=FALSE\nDEPLOY=FALSE\n"
