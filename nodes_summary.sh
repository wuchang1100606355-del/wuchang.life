#!/bin/bash

NODES=(
  "taiji_01@100.71.224.18"
  "taiji_02@100.111.139.7"
)

for NODE in "${NODES[@]}"; do
  STATUS=$(ssh "$NODE" "uptime | awk -F'load average:' '{print \$2}'" 2>/dev/null)
  echo "$NODE => LOAD:$STATUS"
done
