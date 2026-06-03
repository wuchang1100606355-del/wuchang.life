#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

command -v python3 >/dev/null 2>&1

python3 -m py_compile "$ROOT_DIR/runtime_adapters/taiji_formal_tensor_runtime_v0_1_0_adapter.py"
python3 -m py_compile "$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py"

if [ -f "$ROOT_DIR/services/gateway/policies/formal_tensor_validator.py" ]; then
  python3 -m py_compile "$ROOT_DIR/services/gateway/policies/formal_tensor_validator.py"
fi

echo "preflight ok: taiji_formal_tensor_runtime_v0_1_0"
