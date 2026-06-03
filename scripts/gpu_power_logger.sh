#!/bin/bash
OUT="reports/gpu_power_log.csv"
echo "timestamp,power_watt,gpu_util,memory_used_mb,memory_total_mb" > "$OUT"
echo "開始記錄 GPU 功耗，Ctrl+C 停止"
while true; do
  TS=$(date -Is)
  nvidia-smi --query-gpu=power.draw,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits | \
  awk -v ts="$TS" -F', ' '{print ts "," $1 "," $2 "," $3 "," $4}' >> "$OUT"
  sleep 1
done
