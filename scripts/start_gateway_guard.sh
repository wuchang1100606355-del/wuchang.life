#!/usr/bin/env bash
cd ~/Taiji_Hub
while true; do
  echo "[Taiji Gateway Guard] start $(date)"
  uvicorn services.gateway.main:app --host 127.0.0.1 --port 8081
  echo "[Taiji Gateway Guard] stopped $(date), restart in 2s"
  sleep 2
done
