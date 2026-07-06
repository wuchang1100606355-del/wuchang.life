#!/usr/bin/env bash
set -eu

cd /home/taiji_admin/Taiji_Hub

python3 tools/intent_field/sovereign_identity_agent.py --dry-run
