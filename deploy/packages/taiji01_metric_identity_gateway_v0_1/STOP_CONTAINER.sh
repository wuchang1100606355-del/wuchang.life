#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT/deploy/packages/taiji01_metric_identity_gateway_v0_1"
docker compose down
