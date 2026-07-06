#!/usr/bin/env bash
set -eu

cd /home/taiji_admin/Taiji_Hub

python3 tools/intent_field/front_edge_proxy_blocking.py --dry-run
