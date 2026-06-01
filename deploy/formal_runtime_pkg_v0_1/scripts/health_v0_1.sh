#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

python3 - "$TAIJI_BIND_HOST" "$TAIJI_PORT" <<'PY'
import json
import sys
import urllib.request

host = sys.argv[1]
port = int(sys.argv[2])
with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5) as response:
    print(json.dumps(json.load(response), ensure_ascii=False, indent=2, sort_keys=True))
PY
