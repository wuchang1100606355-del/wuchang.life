#!/bin/bash
set -e

if [ "${TAIJI_ALLOW_REMOTE_NODE_RUN:-false}" != "true" ]; then
  echo "blocked: run_nodes.sh performs SSH transfer and remote execution."
  echo "Use manifest/preflight/metric-governed deployment instead."
  exit 2
fi

NODES=(
  "taiji_01@100.71.224.18"
  "taiji_02@100.111.139.7"
)

for NODE in "${NODES[@]}"; do
  echo "===== $NODE ====="
  tar czf - -C ~/Taiji_Hub main.py core | \
  ssh "$NODE" "mkdir -p ~/wuchang_node/Taiji_Hub && cd ~/wuchang_node/Taiji_Hub && tar xzf - && python3 main.py"
done

echo "ALL_NODES_OK"
