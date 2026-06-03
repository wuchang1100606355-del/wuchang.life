#!/usr/bin/env bash
cd /home/taiji_admin/Taiji_Hub
mkdir -p logs

docker update --restart unless-stopped taiji_claw >/dev/null 2>&1 || true
docker start taiji_claw >/dev/null 2>&1 || true

while true; do
  if ! curl -fsS http://localhost:8081/health >/dev/null 2>&1; then
    echo "[guard] gateway offline, starting $(date)"
    pkill -f "uvicorn services.gateway.main:app" 2>/dev/null || true
    nohup uvicorn services.gateway.main:app --host 127.0.0.1 --port 8081 >> logs/gateway.log 2>&1 &
  fi

  if ! curl -fsS http://localhost:9004/ >/dev/null 2>&1; then
    echo "[guard] claw offline, restarting $(date)"
    docker start taiji_claw >/dev/null 2>&1 || true
  fi

  sleep 5
done
