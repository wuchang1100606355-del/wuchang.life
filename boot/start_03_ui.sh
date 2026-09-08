#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
LOGDIR="$ROOT/runtime/logs"
LEDGER="$ROOT/runtime/ledger/ui_03_events.jsonl"
DEAD="$ROOT/runtime/dead_letter/ui_03_rejected.jsonl"

mkdir -p "$LOGDIR" "$ROOT/runtime/ledger" "$ROOT/runtime/dead_letter"

port_open() {
  ss -ltn 2>/dev/null | grep -q ":$1 "
}

log() {
  printf '{"ts":"%s","service":"03_ui","event":"%s","detail":"%s"}\n' \
    "$(date -Is)" "$1" "$2" >> "$LEDGER"
}

reject() {
  printf '{"ts":"%s","service":"03_ui","reason":"%s","detail":"%s"}\n' \
    "$(date -Is)" "$1" "$2" >> "$DEAD"
}

# 03 舊式自啟與資料庫改寫設計已停用。現行介面由既有容器管理，
# 此檔只保留一次性唯讀觀測，避免再次建立平行 OpenWebUI 或改寫舊資料庫。
if port_open 8080; then ow="ok"; else ow="fail"; fi
if port_open 9002; then gw="ok"; else gw="fail"; fi
printf '{"ts":"%s","service":"03_ui_retired_probe","openwebui_8080":"%s","gateway_9002":"%s"}\n' \
  "$(date -Is)" "$ow" "$gw" >> "$LEDGER"
[ "$ow" = "ok" ] && [ "$gw" = "ok" ]
