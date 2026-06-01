#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "=== VERIFY MTL-AI EN-ONLY CONCEPT ARCHITECTURE ==="

FILES=(
  "prompts/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE_PREFIX.md"
  "contexts/current/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.md"
  "contexts/ai_metric/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json"
  "contexts/current/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json"
  ".ai/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json"
)

for f in "${FILES[@]}"; do
  test -f "$f"
  echo "OK_FILE: $f"
done

grep -R "MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ" prompts/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE_PREFIX.md >/dev/null
grep -R "INVIOLABLE" contexts/current/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.md >/dev/null
grep -R "metric_tensor_language_reasoning_core" contexts/ai_metric/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json >/dev/null
grep -R "Cloud is muscle" prompts/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE_PREFIX.md >/dev/null

if grep -P '[\x{4E00}-\x{9FFF}]' "${FILES[@]}" >/tmp/mtl_ai_cjk_found.txt 2>/dev/null; then
  echo "FAILED: CJK characters found"
  cat /tmp/mtl_ai_cjk_found.txt
  exit 1
fi

echo "OK: FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE_BACKGROUND_EFFECTIVE"
