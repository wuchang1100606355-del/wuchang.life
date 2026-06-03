#!/bin/bash
echo "========================================="
echo "       📡 即時網格雷達掃描器 📡"
echo "========================================="
pgrep -f "uvicorn jules_cloud_api:app" > /dev/null && echo "[OK] mu_0 度規拓樸 Runtime API running" || echo "[CHECK] mu_0 度規拓樸 Runtime API not_running"
pgrep -f "sister_j_edge_cortex.py" > /dev/null && echo "[OK] mu_1 度規轉譯閘道器 running" || echo "[CHECK] mu_1 度規轉譯閘道器 not_running"
pgrep -f "taiji_router_node.py" > /dev/null && echo "[OK] mu_2 拓樸路由節點 running" || echo "[CHECK] mu_2 拓樸路由節點 not_running"
echo "========================================="
