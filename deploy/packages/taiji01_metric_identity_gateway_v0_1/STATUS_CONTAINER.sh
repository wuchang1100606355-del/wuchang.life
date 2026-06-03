#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT/deploy/packages/taiji01_metric_identity_gateway_v0_1"
docker compose ps
python3 - <<'PY'
import json, urllib.request
try:
    data = json.load(urllib.request.urlopen('http://100.71.224.18:11435/health', timeout=2))
    print(json.dumps(data, ensure_ascii=False, sort_keys=True))
except Exception as exc:
    print(json.dumps({'ok': False, 'error': type(exc).__name__}, sort_keys=True))
PY
