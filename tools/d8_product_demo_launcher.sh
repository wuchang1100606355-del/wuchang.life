#!/usr/bin/env bash
set -u
cd /home/taiji_admin/Taiji_Hub || exit 40
python3 tools/d8_product_demo_launcher.py "$@"
exit $?
