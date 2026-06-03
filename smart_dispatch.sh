#!/bin/bash

NODE1="taiji_01@100.71.224.18"
NODE2="taiji_02@100.111.139.7"

LOAD1=$(ssh $NODE1 "uptime | awk -F'load average:' '{print \$2}' | cut -d',' -f1")
LOAD2=$(ssh $NODE2 "uptime | awk -F'load average:' '{print \$2}' | cut -d',' -f1")

echo "LOAD1=$LOAD1"
echo "LOAD2=$LOAD2"

# 比較誰比較閒
if (( $(echo "$LOAD1 < $LOAD2" | bc -l) )); then
  TARGET=$NODE1
else
  TARGET=$NODE2
fi

echo "DISPATCH TO: $TARGET"

ssh $TARGET "cd ~/wuchang_node/Taiji_Hub && python3 main.py"
