#!/usr/bin/env bash
set -euo pipefail

TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"

if [ ! -d "$TARGET" ]; then
  echo "target missing: $TARGET" >&2
  exit 1
fi

cd "$TARGET"

echo "target=$(pwd)"
echo "python=$(command -v python3 || true)"

python3 -m py_compile runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py
python3 -m py_compile deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry_v0_1_1.py

find deploy runtime_adapters Taiji_Governance -type f \
  ! -name 'SHA256SUMS' \
  ! -path '*/.git/*' \
  -print0 | sort -z | xargs -0 sha256sum > Taiji_Governance/progress/wsl_native_migration_sha256_2026-05-11.txt

echo "sha256_written=Taiji_Governance/progress/wsl_native_migration_sha256_2026-05-11.txt"
echo "post_migration_verify_ok"
