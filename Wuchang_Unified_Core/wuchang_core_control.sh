#!/bin/bash
set -euo pipefail

MODE="${TAIJI_BOOT_MODE:-status}"
BASE_DIR="$HOME/Taiji_Hub/Wuchang_Unified_Core"
BIND_HOST="${TAIJI_BIND_HOST:-127.0.0.1}"
cd "$BASE_DIR" || exit 1
echo -e "\033[1;34m======================================================\033[0m"
echo -e "\033[1;34m     五常太極大陣 - Runtime status/control (${MODE})\033[0m"
echo -e "\033[1;34m======================================================\033[0m"

status_proc() {
    local label="$1"
    local pattern="$2"
    if pgrep -f "$pattern" > /dev/null; then
        echo "[$label] running"
        return 0
    fi
    echo "[$label] not_running"
    return 1
}

if [ "$MODE" != "1" ] && [ "$MODE" != "start" ]; then
    status_proc "mu_0 度規拓樸 Runtime API" "uvicorn jules_cloud_api:app" || true
    status_proc "mu_1 度規轉譯閘道器" "sister_j_edge_cortex.py" || true
    status_proc "mu_2 拓樸路由節點" "taiji_router_node.py" || true
    echo "[guard] status-only; no auto-start"
    exit 0
fi

if ! pgrep -f "uvicorn jules_cloud_api:app" > /dev/null; then
    cd "$BASE_DIR/01_Cloud_Core" && nohup python3 -m uvicorn jules_cloud_api:app --host "$BIND_HOST" --port 8000 > local_api.log 2>&1 &
    echo "[mu_0 度規拓樸 Runtime API] 檢查後受控啟動"
else echo "[mu_0 度規拓樸 Runtime API] running"; fi
if ! pgrep -f "sister_j_edge_cortex.py" > /dev/null; then
    cd "$BASE_DIR/02_Edge_Nodes" && nohup python3 sister_j_edge_cortex.py > edge_cortex.log 2>&1 &
    echo "[mu_1 度規轉譯閘道器] 檢查後受控啟動"
else echo "[mu_1 度規轉譯閘道器] running"; fi
if ! pgrep -f "taiji_router_node.py" > /dev/null; then
    cd "$BASE_DIR/02_Edge_Nodes" && nohup python3 taiji_router_node.py > router_node.log 2>&1 &
    echo "[mu_2 拓樸路由節點] 檢查後受控啟動"
else echo "[mu_2 拓樸路由節點] running"; fi
