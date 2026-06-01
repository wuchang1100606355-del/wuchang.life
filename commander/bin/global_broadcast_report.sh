#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/Taiji_Hub"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$ROOT/runtime/broadcast/global_broadcast_$TS.md"
JSON_OUT="$ROOT/runtime/broadcast/w7tp_global_broadcast_$TS.json"

mkdir -p "$ROOT/runtime/broadcast" "$ROOT/commander/reports"

{
  echo "# 五常全域廣播全局回報"
  echo
  echo "- time: $TS"
  echo "- workspace: $ROOT"
  echo "- mode: readonly_broadcast"
  echo
  echo "## 七維狀態"
  echo "- D1 身分維：指揮官 / 本機主控"
  echo "- D2 時序維：登入後全局回報"
  echo "- D3 空間拓樸維：MSI → WSL → Taiji_Hub → Tailscale 節點"
  echo "- D4 資源維：8080 / 9002 / 8069 / 11434 / 9004 / 2222"
  echo "- D5 風險維：只讀；不 kill；不輸出 secret；不自啟服務"
  echo "- D6 治理維：節點同步需本人確認"
  echo "- D7 任務維：全局廣播、節點同步設計、命令矩陣"
  echo
  echo "## ports"
  ss -ltnp 2>/dev/null | grep -E ":8080|:9002|:8069|:11434|:9004|:2222" || true
  echo
  echo "## docker"
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
  echo
  echo "## tailscale"
  tailscale status 2>/dev/null || true
} | tee "$OUT"

python3 - <<PY
import json, time, hashlib, pathlib
root = pathlib.Path.home() / "Taiji_Hub"
packet = {
  "w7tp_version": "1.0",
  "packet_type": "w7tp.global_broadcast",
  "source_node": "msi",
  "target_node": "all_nodes",
  "D1_identity": "commander_local_owner_review",
  "D2_time": "login_global_report",
  "D3_topology": "msi_wsl_taiji_hub_tailscale_mesh",
  "D4_resource": "local_ports_and_nodes",
  "D5_risk": "readonly_no_secret_no_kill_no_autostart",
  "D6_governance": "operator_review_required_for_remote_exec",
  "D7_intent": "broadcast_status_and_sync_plan",
  "allowed_actions": ["health_report", "dry_run_sync_plan", "write_local_report"],
  "forbidden_actions": ["secret_export", "db_volume_delete", "process_kill_without_confirm", "remote_exec_without_confirm"],
  "created_at": int(time.time())
}
raw = json.dumps(packet, ensure_ascii=False, sort_keys=True).encode()
packet["digest"] = hashlib.sha256(raw).hexdigest()
path = pathlib.Path("$JSON_OUT")
path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
print("JSON_PACKET=", path)
PY

cp "$OUT" "$ROOT/commander/reports/"
echo "REPORT=$OUT"
