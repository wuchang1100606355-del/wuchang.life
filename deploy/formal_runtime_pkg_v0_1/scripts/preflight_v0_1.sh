#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

command -v python3 >/dev/null 2>&1

python3 -m py_compile "$ROOT_DIR/runtime_adapters/formal_tensor_runtime_adapter_v0_1.py"
python3 -m py_compile "$ROOT_DIR/deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py"

if [ -f "$ROOT_DIR/services/gateway/policies/formal_tensor_validator.py" ]; then
  python3 -m py_compile "$ROOT_DIR/services/gateway/policies/formal_tensor_validator.py"
fi

echo "formal runtime package v0.1 preflight ok"
