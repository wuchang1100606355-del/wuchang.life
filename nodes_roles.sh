#!/bin/bash
echo "MSI_LOCAL => ROLE: LLM_CONTROL"
ssh taiji_01@100.71.224.18 "echo taiji_01 => ROLE: CPU_WORKER && nproc && free -h | awk '/Mem:/ {print \$2}'"
ssh taiji_02@100.111.139.7 "echo taiji_02 => ROLE: CPU_WORKER && nproc && free -h | awk '/Mem:/ {print \$2}'"
