#!/bin/bash
set -euo pipefail

if [ "${TAIJI_ALLOW_LEGACY_IGNITION:-false}" != "true" ]; then
  echo "blocked: legacy ignition can kill processes and bind public interfaces."
  echo "Set TAIJI_ALLOW_LEGACY_IGNITION=true only after governance review."
  exit 2
fi
# 五常大陣 - 底層全境點火引擎 (包含 AI 小腦 - 社區校準版)

# --- 階段 A：喚醒 LLM 裝甲 ---
if command -v systemctl >/dev/null 2>&1; then systemctl start ollama >/dev/null 2>&1 || true; fi
if command -v docker >/dev/null 2>&1; then
    # 僅喚醒 Open WebUI 戰術中心，剔除 POS 邏輯
    docker start open-webui >/dev/null 2>&1 || true
fi

# --- 階段 B：清理殘骸 ---
pkill -9 -u taiji_admin -f wuchang_ai_cerebellum.py || true
pkill -9 -u taiji_admin -f taiji_router_node.py || true
pkill -9 -u taiji_admin -f sister_j_edge_cortex.py || true
pkill -9 -u taiji_admin -f jules_cloud_api.py || true
pkill -9 -u taiji_admin -f uvicorn || true
sleep 1

# --- 階段 C：陣法點火 (AI 小腦最先點火，接管底層) ---
# 1. 點火 AI 小腦 (Port 9006)
su - taiji_admin -c "cd /home/taiji_admin/Taiji_Hub/Wuchang_Unified_Core/02_Edge_Nodes && nohup python3 wuchang_ai_cerebellum.py > cerebellum.log 2>&1 &"
sleep 1
# 2. 點火 雲端大腦 (Port 8000)
su - taiji_admin -c "cd /home/taiji_admin/Taiji_Hub/Wuchang_Unified_Core/01_Cloud_Core && nohup python3 -m uvicorn jules_cloud_api:app --host 0.0.0.0 --port 8000 > local_api.log 2>&1 &"
# 3. 點火 邊緣節點與城門 (Port 9005 - 已校準為正確的 taiji_router_node.py)
su - taiji_admin -c "cd /home/taiji_admin/Taiji_Hub/Wuchang_Unified_Core/02_Edge_Nodes && nohup python3 sister_j_edge_cortex.py > edge_cortex.log 2>&1 &"
su - taiji_admin -c "cd /home/taiji_admin/Taiji_Hub/Wuchang_Unified_Core/02_Edge_Nodes && nohup python3 taiji_router_node.py > router_node.log 2>&1 &"

exit 0
