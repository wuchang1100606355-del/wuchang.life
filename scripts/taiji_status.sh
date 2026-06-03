#!/usr/bin/env bash
cd /home/taiji_admin/Taiji_Hub
echo "===== TAIJI STATUS ====="
echo
echo "[1] systemd"
systemctl status taiji-gateway.service taiji-openwebui-bridge.service taiji-runtime-api.service taiji-runtime-core.service taiji.service --no-pager 2>/dev/null | sed -n '1,120p' || true
echo
echo "[2] ports"
ss -ltnp 2>/dev/null | grep -E '3000|8081|8098|8099|9004|9011|9012|9120|11434' || true
echo
echo "[3] docker"
docker ps || true
echo
echo "[4] gateway"
curl -s http://127.0.0.1:8081/health | python3 -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8081/health || true
echo
echo "[5] bridge"
curl -s http://127.0.0.1:8098/v1/models | python3 -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8098/v1/models || true
echo
echo "[6] runtime"
curl -s http://127.0.0.1:8099/runtime/system | python3 -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8099/runtime/system || true
echo
echo "[7] tailscale"
tailscale status 2>/dev/null | sed -E 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+/[REDACTED_EMAIL]/g' || true
