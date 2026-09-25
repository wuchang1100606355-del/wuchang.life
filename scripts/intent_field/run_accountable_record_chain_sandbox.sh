#!/usr/bin/env bash
set -eu

cd /home/taiji_admin/Taiji_Hub

python3 tools/intent_field/accountable_record_chain.py --dry-run
