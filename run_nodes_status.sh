#!/bin/bash
set -euo pipefail

if [ "${TAIJI_ALLOW_REMOTE_NODE_RUN:-false}" != "true" ]; then
  echo "blocked: run_nodes_status.sh performs SSH transfer and remote execution."
  echo "Use read-only node status probes or manifest/preflight instead."
  exit 2
fi

NODES=(
  "taiji_01@100.71.224.18"
  "taiji_02@100.111.139.7"
)

for NODE in "${NODES[@]}"; do
  echo "===== $NODE ====="
  tar czf - -C ~/Taiji_Hub main.py core | \
  ssh "$NODE" "cd ~/wuchang_node/Taiji_Hub 2>/dev/null || mkdir -p ~/wuchang_node/Taiji_Hub && tar xzf - && python3 main.py && uptime && echo STATUS_OK"
done

echo "ALL_NODES_STATUS_OK"
