#!/usr/bin/env bash
set -euo pipefail

TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"

cd "$TARGET"

required=(
  "schemas/formal_tensor_packet.schema.json"
  "services/gateway/policies/formal_tensor_validator.py"
  "tests/test_formal_tensor_validator.py"
  "runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py"
  "deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL_V011.sh"
  "deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STATUS_LOCAL_V011.sh"
)

for path in "${required[@]}"; do
  if [ ! -f "$path" ]; then
    echo "missing: $path" >&2
    exit 1
  fi
done

python3 -m json.tool schemas/formal_tensor_packet.schema.json >/dev/null
python3 -m py_compile services/gateway/policies/formal_tensor_validator.py
python3 -m py_compile runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py
python3 -m py_compile deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry_v0_1_1.py

if command -v pytest >/dev/null 2>&1; then
  PYTHONPATH=. pytest -q tests/test_formal_tensor_validator.py
else
  PYTHONPATH=. python3 -m pytest -q tests/test_formal_tensor_validator.py
fi

bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/HASH_SCRIPT.sh >/dev/null

echo "post_migration_runtime_check_ok"
