#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "=== VERIFY FINAL MTL-AI GATEWAY ASSEMBLY ==="

FILES=(
  "prompts/FINAL_MTL_AI_ASSEMBLY_EN_ONLY_PREFIX.md"
  "contexts/current/FINAL_MTL_AI_ASSEMBLY_STATE.md"
  "contexts/ai_metric/FINAL_MTL_AI_ASSEMBLY.mtl.json"
  "contexts/current/FINAL_MTL_AI_ASSEMBLY.mtl.json"
  ".ai/FINAL_MTL_AI_ASSEMBLY.mtl.json"
  "openwebui_tools/taiji_metric_gateway_assembly_tool.py"
)

for f in "${FILES[@]}"; do
  test -f "$f"
  echo "OK_FILE: $f"
done

grep -R "MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ" prompts/FINAL_MTL_AI_ASSEMBLY_EN_ONLY_PREFIX.md >/dev/null
grep -R "BACKGROUND_EFFECTIVE" contexts/current/FINAL_MTL_AI_ASSEMBLY_STATE.md >/dev/null
grep -R "metric_tensor_language_reasoning_core" contexts/ai_metric/FINAL_MTL_AI_ASSEMBLY.mtl.json >/dev/null
grep -R "Cloud is muscle" prompts/FINAL_MTL_AI_ASSEMBLY_EN_ONLY_PREFIX.md >/dev/null

python3 - <<'PY'
from pathlib import Path
import re, sys
files = [
    "prompts/FINAL_MTL_AI_ASSEMBLY_EN_ONLY_PREFIX.md",
    "contexts/current/FINAL_MTL_AI_ASSEMBLY_STATE.md",
    "contexts/ai_metric/FINAL_MTL_AI_ASSEMBLY.mtl.json",
    "contexts/current/FINAL_MTL_AI_ASSEMBLY.mtl.json",
    ".ai/FINAL_MTL_AI_ASSEMBLY.mtl.json",
]
bad = []
pat = re.compile(r"[\u4e00-\u9fff]")
for f in files:
    text = Path(f).read_text(encoding="utf-8")
    if pat.search(text):
        bad.append(f)
if bad:
    print("FAILED_CJK_FOUND:", bad)
    sys.exit(1)
print("OK_EN_ONLY_NO_CJK")
PY

echo "OK: FINAL_MTL_AI_GATEWAY_ASSEMBLY_BACKGROUND_EFFECTIVE"
