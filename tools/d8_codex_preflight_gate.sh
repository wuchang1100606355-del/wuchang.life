#!/usr/bin/env bash
set -u
cd /home/taiji_admin/Taiji_Hub || exit 40
python3 tools/d8_codex_preflight_gate.py "$@"
exit $?
