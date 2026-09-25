#!/usr/bin/env bash
set -eu

cd /home/taiji_admin/Taiji_Hub

tmp_log="$(mktemp)"
python3 tools/intent_field/intent_field_product_preflight.py --dry-run | tee "$tmp_log"

out="$(awk -F= '/^OUT=/{print $2}' "$tmp_log" | tail -1)"
rm -f "$tmp_log"

if [ -z "$out" ]; then
  echo "STATE=HOLD_INTENT_FIELD_PRODUCT_PREFLIGHT"
  echo "OUT="
  echo "DRY_RUN=FAIL"
  echo "DB_WRITE=false"
  echo "DEPLOY=false"
  echo "RESTART=false"
  exit 2
fi

python3 tools/intent_field/verify_intent_field_packet.py "$out"
