#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/taiji_admin/Taiji_Hub"
cd "$ROOT"

mkdir -p logs runtime/memos runtime/ledger security

TS="$(date +%Y%m%d_%H%M%S)"
LOG="logs/taiji_full_boot_${TS}.log"
MEMO="runtime/memos/taiji_full_boot_${TS}.md"

exec > >(tee -a "$LOG") 2>&1

say() { echo "[$(date -Is)] $*"; }

curl_ok() {
  curl -fsS "$1" >/dev/null 2>&1
}

start_container_if_exists() {
  local name="$1"
  if docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
    say "[Docker] start $name"
    docker update --restart unless-stopped "$name" >/dev/null 2>&1 || true
    docker start "$name" >/dev/null 2>&1 || true
  else
    say "[Docker] skip missing $name"
  fi
}

restart_service_if_exists() {
  local svc="$1"
  if systemctl list-unit-files | grep -q "^${svc}"; then
    say "[systemd] restart $svc"
    sudo systemctl restart "$svc" || true
  else
    say "[systemd] skip missing $svc"
  fi
}

say "===== Taiji Full Boot start ====="

say "[0] stop legacy manual gateway loops"
pkill -f "scripts/start_gateway.sh" 2>/dev/null || true
pkill -f "scripts/taiji_guard.sh" 2>/dev/null || true

say "[1] start core containers"
start_container_if_exists "wuchang_gpu_brain"
start_container_if_exists "open-webui"
start_container_if_exists "taiji_claw_safe"
start_container_if_exists "taiji_claw"
start_container_if_exists "taiji_pos_google_voice_tool"
start_container_if_exists "taiji_device_resilience_adapter"

say "[2] restart core systemd services"
sudo systemctl daemon-reload || true
restart_service_if_exists "taiji-runtime-core.service"
restart_service_if_exists "taiji-runtime-api.service"
restart_service_if_exists "taiji.service"
restart_service_if_exists "taiji-gateway.service"
restart_service_if_exists "taiji-openwebui-bridge.service"

say "[3] wait services"
sleep 5

say "[4] health probes"
echo "--- Gateway 8081 ---"
curl -s http://127.0.0.1:8081/health || true
echo
echo "--- OpenWebUI Bridge 8098 ---"
curl -s http://127.0.0.1:8098/v1/models || true
echo
echo "--- Runtime API 8099 ---"
curl -s http://127.0.0.1:8099/runtime/system || true
echo
echo "--- Clow / Claw 9004 ---"
curl -s http://127.0.0.1:9004/ || true
echo
echo "--- OpenWebUI 3000 ---"
curl -sI http://127.0.0.1:3000 | head -5 || true
echo

say "[5] write state memo"
{
echo "# Taiji Full Boot Memo"
echo
echo "timestamp: $(date -Is)"
echo "host: $(hostname)"
echo "user: $(whoami)"
echo
echo "## Ports"
ss -ltnp 2>/dev/null | grep -E '3000|8081|8098|8099|9004|9011|9012|9120|11434' || true
echo
echo "## Systemd"
systemctl --no-pager --type=service 2>/dev/null | grep -E 'taiji|openwebui|ollama' || true
echo
echo "## Docker"
docker ps || true
echo
echo "## Tailscale"
tailscale status 2>/dev/null | sed -E 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+/[REDACTED_EMAIL]/g' || true
echo
echo "## Gateway"
curl -s http://127.0.0.1:8081/health || true
echo
echo "## Bridge Models"
curl -s http://127.0.0.1:8098/v1/models || true
echo
echo "## Runtime Status"
curl -s http://127.0.0.1:8099/runtime/status || true
echo
echo "## Latest Ledger"
ls -lt runtime/ledger/*.json 2>/dev/null | head -5 || true
} | tee "$MEMO" >/dev/null

cat "$MEMO" | logger -t taiji-full-boot || true

say "[6] sandbox call"
curl -s -X POST http://127.0.0.1:8098/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"taiji-runtime-core","messages":[{"role":"user","content":"小J，請確認 Taiji Full Boot、OpenWebUI、Runtime、Clow、度規張量與上下文分片目前是否在線。"}]}' \
  | python3 -m json.tool || true

say "[7] open OpenWebUI"
if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -Command "Start-Process 'http://localhost:3000'" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:3000" >/dev/null 2>&1 || true
fi

TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"

say "===== Taiji Full Boot complete ====="
echo
echo "OpenWebUI local:     http://localhost:3000"
if [ -n "$TS_IP" ]; then
  echo "OpenWebUI tailscale: http://${TS_IP}:3000"
  echo "Gateway tailscale:   http://${TS_IP}:8081/health"
  echo "Bridge tailscale:    http://${TS_IP}:8098/v1/models"
fi
echo "Gateway local:       http://localhost:8081/health"
echo "Bridge local:        http://localhost:8098/v1/models"
echo "Memo:                $MEMO"
echo "Log:                 $LOG"
