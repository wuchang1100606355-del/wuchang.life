#!/usr/bin/env bash
set -euo pipefail

BASE="$(pwd)"
TS="$(date +%Y%m%d_%H%M%S)"
TODAY="$(date +%Y-%m-%d)"

PKG_NAME="MTL_AI_GATEWAY_v1_0_RC1_${TS}"
STAGE="release/${PKG_NAME}"
OUT="release/${PKG_NAME}.tar.gz"
SHA="${OUT}.sha256"
MANIFEST="${STAGE}/MANIFEST.tsv"
README="${STAGE}/README.md"
REPORT="reports/finalization/package_${PKG_NAME}.md"

echo "=== PACKAGE MTL-AI-GATEWAY RC1 ==="
echo "BASE=$BASE"
echo "STAGE=$STAGE"

rm -rf "$STAGE"
mkdir -p "$STAGE"

mkdir -p \
  "$STAGE/prompts" \
  "$STAGE/contexts/current" \
  "$STAGE/contexts/ai_metric" \
  "$STAGE/contexts/human" \
  "$STAGE/openwebui_tools" \
  "$STAGE/scripts/review" \
  "$STAGE/models/ollama" \
  "$STAGE/logs/system" \
  "$STAGE/reports/finalization" \
  "$STAGE/data/service_account_memory" \
  "$STAGE/config/cloud_muscle" \
  "$STAGE/config/carbon"

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [ -f "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
    echo "COPIED	$src"
  else
    echo "MISSING	$src"
  fi
}

echo "=== COPY CORE PREFIXES ==="
copy_if_exists "prompts/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY_PREFIX.md" "$STAGE/prompts/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY_PREFIX.md"
copy_if_exists "prompts/FINAL_MTL_AI_ASSEMBLY_EN_ONLY_PREFIX.md" "$STAGE/prompts/FINAL_MTL_AI_ASSEMBLY_EN_ONLY_PREFIX.md"
copy_if_exists "prompts/FINAL_WUCHANG_GOVERNANCE_PREFIX.md" "$STAGE/prompts/FINAL_WUCHANG_GOVERNANCE_PREFIX.md"

echo "=== COPY CURRENT STATE ==="
copy_if_exists "contexts/current/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY.md" "$STAGE/contexts/current/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY.md"
copy_if_exists "contexts/current/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY.mtl.json" "$STAGE/contexts/current/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY.mtl.json"
copy_if_exists "contexts/current/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json" "$STAGE/contexts/current/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json"
copy_if_exists "contexts/current/FINAL_MTL_AI_ASSEMBLY_STATE.md" "$STAGE/contexts/current/FINAL_MTL_AI_ASSEMBLY_STATE.md"
copy_if_exists "contexts/current/FINAL_MTL_AI_ASSEMBLY.mtl.json" "$STAGE/contexts/current/FINAL_MTL_AI_ASSEMBLY.mtl.json"
copy_if_exists "contexts/current/MTL_AI_MODEL_SUCCESS.mtl.json" "$STAGE/contexts/current/MTL_AI_MODEL_SUCCESS.mtl.json"
copy_if_exists "contexts/current/MTL_AI_GATEWAY_REPAIR_STATUS.mtl.json" "$STAGE/contexts/current/MTL_AI_GATEWAY_REPAIR_STATUS.mtl.json"
copy_if_exists "contexts/current/SYSTEM_CURRENT_STATE.md" "$STAGE/contexts/current/SYSTEM_CURRENT_STATE.md"

echo "=== COPY AI METRIC CONTEXT ==="
for f in \
  contexts/ai_metric/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY.mtl.json \
  contexts/ai_metric/FINAL_MTL_AI_ASSEMBLY.mtl.json \
  contexts/ai_metric/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json \
  contexts/ai_metric/SERVICE_ACCOUNT_LEARNING_MEMORY.mtl.json \
  contexts/ai_metric/CREATOR_SELF_LIMITING_PUBLIC_INTEREST_CLOSURE.mtl.json \
  contexts/ai_metric/CARBON_GATEWAY_CLOUD_MUSCLE.mtl.json \
  contexts/ai_metric/METRIC_LANGUAGE_ENGINEERING_AI_GATEWAY.mtl.json
do
  copy_if_exists "$f" "$STAGE/$f"
done

echo "=== COPY WORKLOG / SYSTEM LOGS ==="
copy_if_exists "contexts/human/WORKLOG.md" "$STAGE/contexts/human/WORKLOG.md"
copy_if_exists "logs/system/LATEST_SYSTEM_LOG.md" "$STAGE/logs/system/LATEST_SYSTEM_LOG.md"

echo "=== COPY TOOLS / SCRIPTS ==="
copy_if_exists "openwebui_tools/taiji_metric_gateway_assembly_tool.py" "$STAGE/openwebui_tools/taiji_metric_gateway_assembly_tool.py"
copy_if_exists "openwebui_tools/taiji_claw_safe_tool.py" "$STAGE/openwebui_tools/taiji_claw_safe_tool.py"

for f in scripts/review/*.sh; do
  [ -f "$f" ] && copy_if_exists "$f" "$STAGE/$f"
done

copy_if_exists "scripts/oneclick_mtl_ai_assembly.sh" "$STAGE/scripts/oneclick_mtl_ai_assembly.sh"
copy_if_exists "scripts/oneclick_full_mtl_ai_pipeline.sh" "$STAGE/scripts/oneclick_full_mtl_ai_pipeline.sh"
copy_if_exists "models/ollama/Modelfile.metric_language_gateway_ai" "$STAGE/models/ollama/Modelfile.metric_language_gateway_ai"

echo "=== COPY SAFE CONFIG / MEMORY PLACEHOLDERS ==="
copy_if_exists "data/service_account_memory/capability_memory.json" "$STAGE/data/service_account_memory/capability_memory.json"
copy_if_exists "config/cloud_muscle/google_drive_inventory.config.json" "$STAGE/config/cloud_muscle/google_drive_inventory.config.json"
copy_if_exists "config/carbon/carbon_factors.example.json" "$STAGE/config/carbon/carbon_factors.example.json"

echo "=== WRITE README ==="
cat > "$README" <<__README__
# MTL-AI-Gateway v1.0 RC1 Package

status: PACKAGED_RC1
created_at: ${TODAY}
package_id: ${PKG_NAME}

## Root Formula

MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

## Embedded Formula

W6 = D1 ⊕ D2 ⊕ D3 ⊕ H4 ⊕ C5 ⊕ G6

## Package Meaning

This package contains the background-effective MTL-AI Gateway assembly:

- English-only concept-inviolable architecture prefix
- Machine-readable metric tensor context
- OpenWebUI gateway tool files
- model Modelfile
- current system state
- system logs and worklog
- validation scripts
- safe service account capability-memory placeholder
- carbon factor placeholder

## Security Boundary

This package must not contain:

- service account JSON
- private key
- token
- refresh token
- password
- 2FA
- raw credentials
- Odoo DB password
- host_root
- raw audio
- sensitive PII plaintext

## Runtime Model

model:
metric-language-gateway-ai:latest

base:
sister-j-brain:latest

## OpenWebUI

Select model:

metric-language-gateway-ai:latest

Enable tools:

- Taiji Claw Safe Bridge
- Taiji Metric Gateway Assembly

## Closure

READONLY / LOW_RISK_AUDITED / CONFIRM_REQUIRED / BLOCKED_WITH_SAFE_ALTERNATIVE

## Core Laws

The creator proves public interest through self-limitation.
Xiao J proves loyalty by refusing boundary violations.
The system proves trust through auditable closure.
Cloud is muscle, not brain.
Models learn capability graphs, never key material.
Imagination may be unfenced.
Execution must be guarded.
__README__

echo "=== SECRET SCAN ==="
# Only block actual credential material patterns, not policy words like private_key in documentation.
if grep -RInE 'BEGIN PRIVATE KEY|\"private_key\"[[:space:]]*:|\"client_secret\"[[:space:]]*:|\"refresh_token\"[[:space:]]*:|\"access_token\"[[:space:]]*:|\"password\"[[:space:]]*:' "$STAGE"; then
  echo "FAILED: secret-like material found in package stage."
  exit 1
fi

echo "=== WRITE MANIFEST ==="
{
  echo -e "sha256\tbytes\tpath"
  find "$STAGE" -type f | sort | while read -r f; do
    sha="$(sha256sum "$f" | awk '{print $1}')"
    bytes="$(wc -c < "$f")"
    rel="${f#$STAGE/}"
    echo -e "${sha}\t${bytes}\t${rel}"
  done
} > "$MANIFEST"

echo "=== CREATE ARCHIVE ==="
tar -czf "$OUT" -C release "$PKG_NAME"
sha256sum "$OUT" > "$SHA"

echo "=== VERIFY ARCHIVE ==="
sha256sum -c "$SHA"
tar -tzf "$OUT" | head -n 80

echo "=== WRITE REPORT ==="
cat > "$REPORT" <<__REPORT__
# MTL-AI-Gateway v1.0 RC1 Package Report

status: PACKAGED_RC1
created_at: ${TODAY}
timestamp: ${TS}

package:
${OUT}

sha256:
${SHA}

stage:
${STAGE}

manifest:
${MANIFEST}

formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

security:
secret scan passed

meaning:
Core assembly packaged for preservation, transfer, audit, and later deployment.
__REPORT__

echo "=== RECORD SYSTEM STATE ==="
cat >> contexts/current/SYSTEM_CURRENT_STATE.md <<__STATE__

## MTL-AI-Gateway v1.0 RC1 Package

status:
PACKAGED_RC1

package:
${OUT}

sha256:
${SHA}

manifest:
${MANIFEST}

formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

security:
secret scan passed
__STATE__

cat >> contexts/human/WORKLOG.md <<__WORKLOG__

## ${TODAY} - MTL-AI-Gateway v1.0 RC1 Packaged

Status:
PACKAGED_RC1

Package:
${OUT}

SHA256:
${SHA}

Formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Security:
Secret scan passed.
No service account JSON or private key should be included.
__WORKLOG__

echo "=== PACKAGE DONE ==="
ls -lh "$OUT" "$SHA" "$MANIFEST" "$README" "$REPORT"
