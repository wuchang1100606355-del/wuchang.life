#!/usr/bin/env bash
cd ~/Taiji_Hub
while true; do
  echo "[Taiji Gateway] starting $(date)"
  uvicorn services.gateway.main:app --host 127.0.0.1 --port 8081
  echo "[Taiji Gateway] stopped $(date), restarting in 2s..."
  sleep 2
done
