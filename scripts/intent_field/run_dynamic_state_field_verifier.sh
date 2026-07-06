#!/usr/bin/env bash
set -eu

cd /home/taiji_admin/Taiji_Hub

python3 tools/intent_field/dynamic_state_field_verifier.py --dry-run
