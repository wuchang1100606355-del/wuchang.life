#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/migration/dependency_relocation_v0_1/relocation.env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PLAN_JSONL="$SOURCE_ROOT/Taiji_Governance/system_info/dependency_relocation_plan_2026-05-12.jsonl"
VERIFY_JSONL="$SOURCE_ROOT/Taiji_Governance/system_info/dependency_relocation_verify_2026-05-12.jsonl"
: > "$VERIFY_JSONL"

check_sha() {
  local src="$1"
  local expected="$2"
  local actual
  actual="sha256:$(sha256sum "$src" | awk '{print $1}')"
  [ "$actual" = "$expected" ]
}

while IFS= read -r line; do
  rel="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["path"])')"
  sha="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha256"])')"
  cloud_allowed="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["targets"]["cloud_allowed"])')"
  local_ok=false
  cloud_ok="not_applicable"

  if [ -f "$LOCAL_DEP_TARGET/$rel" ] && check_sha "$LOCAL_DEP_TARGET/$rel" "$sha"; then
    local_ok=true
  fi
  if [ "$cloud_allowed" = "True" ]; then
    cloud_ok=false
    if [ -f "$CLOUD_STAGE/$rel" ] && check_sha "$CLOUD_STAGE/$rel" "$sha"; then
      cloud_ok=true
    fi
  fi
  printf '{"path":"%s","local_ok":%s,"cloud_ok":"%s","sha256":"%s"}\n' "$rel" "$local_ok" "$cloud_ok" "$sha" >> "$VERIFY_JSONL"
done < "$PLAN_JSONL"

python3 - <<PY
import json
from pathlib import Path
p = Path("$VERIFY_JSONL")
rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
bad = [r for r in rows if not r["local_ok"] or r["cloud_ok"] == "False"]
print(f"checked={len(rows)}")
print(f"bad={len(bad)}")
if bad:
    print("first_bad=", bad[:5])
    raise SystemExit(1)
PY

echo "verify_jsonl=$VERIFY_JSONL"
echo "verify_ok"

