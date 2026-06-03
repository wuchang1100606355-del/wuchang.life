#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${TAIJI_ENV_FILE:-$ROOT_DIR/deploy/env/runtime.env.example}"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

python3 - "${TAIJI_BIND_HOST:-127.0.0.1}" "${TAIJI_PORT:-8105}" <<'PY'
import json
import sys
import urllib.request

host = sys.argv[1]
port = int(sys.argv[2])
url = f"http://{host}:{port}/health"
with urllib.request.urlopen(url, timeout=5) as response:
    data = json.load(response)
print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
PY
