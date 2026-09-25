#!/usr/bin/env bash
set -eu

cd /home/taiji_admin/Taiji_Hub

python3 tools/intent_field/p2_sandbox_runtime_harness.py --dry-run
