#!/usr/bin/env bash
set -euo pipefail

cd ~/Taiji_Hub

TS="$(date +%Y%m%d_%H%M%S)"
TODAY="$(date +%Y-%m-%d)"

PEND="_pending_delete/context_full_${TS}"
ARC="archive_converged/context_pruned/context_full_${TS}.tar.gz"
SHA="${ARC}.sha256"
REPORT="reports/finalization/context_prune_status_only_${TS}.md"

mkdir -p "$PEND" "$(dirname "$ARC")" reports/finalization

echo "=== CONTEXT PRUNE: KEEP STATUS ONLY ==="
echo "timestamp=$TS"

echo "=== 1. STAGE OLD CONTEXT ==="

for d in contexts/current contexts/ai_metric contexts/human .ai logs/system; do
  if [ -e "$d" ]; then
    mkdir -p "$PEND/$(dirname "$d")"
    mv "$d" "$PEND/$d"
    echo "MOVED $d -> $PEND/$d"
  fi
done

mkdir -p contexts/current contexts/human .ai logs/system

echo "=== 2. WRITE STATUS-ONLY SUMMARY ==="

cat > contexts/current/STATUS_ONLY.md <<'STATUS'
# MTL-AI-Gateway Status Only

status: CONTEXT_PRUNED_STATUS_ONLY
profile: minimal active state
language: zh-TW summary with English formulas
secret_policy: no keys, no private_key, no service_account_json, no tokens

## Current System Identity

Project:
MTL-AI-Gateway

Version:
v1.0 RC1

Runtime status:
CORE_RUNTIME_PASS

Package status:
PACKAGED_RC1

Model status:
MODEL_BUILD_SUCCESS

Windows startup:
PENDING_ONLOGON_VERIFICATION

Cloud muscle:
CONTROL_PLANE_READY
DRIVE_DRYRUN_PENDING_OR_PARTIAL

## Root Formula

MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

## Embedded Formula

W6 = D1 ⊕ D2 ⊕ D3 ⊕ H4 ⊕ C5 ⊕ G6

## Layer Summary

Ω0:
Creator self-limitation public-interest closure.

I0:
Xiao J / Sister J identity invariant.

SA7:
Service account capability memory; learn capability graph, never key material.

Tμν:
Metric tensor language reasoning core.

Gτ:
Gateway task closure assembly.

EΣ:
Evidence, ESG, carbon, and public-value output.

D1:
Sovereign blind metric; local holds truth, cloud sees metrics.

D2:
Unfenced reasoning with guarded execution.

D3:
POS / Odoo / Google public-interest governance.

H4:
Metric tensor gravity patch hardware mesh.

C5:
Carbon metric ledger.

G6:
Gateway cloud muscle.

## Active Runtime

Model:
metric-language-gateway-ai:latest

Base model:
sister-j-brain:latest

OpenWebUI:
running / cockpit

Claw Safe:
running / controlled execution gateway / 127.0.0.1:9004

POS Voice Tool:
running / text-intent only / 127.0.0.1:9011 and 100.107.187.77:9011

Device Resilience Adapter:
running / 127.0.0.1:9012 and 100.107.187.77:9012

Ollama:
host model available

Tailscale:
secure device mesh

## Verified Runtime

- containers up
- metric-language-gateway-ai:latest exists
- Claw Safe health OK
- POS Voice Tool health OK
- OpenWebUI can reach Claw Safe
- MTL-AI-Gateway RC1 package created and SHA verified

## Operational Closure

All real-world operations must close into:

- READONLY
- LOW_RISK_AUDITED
- CONFIRM_REQUIRED
- BLOCKED_WITH_SAFE_ALTERNATIVE

## Forbidden Material

Never store in model, prompt, logs, context, cloud output, POS, or public package:

- private_key
- service_account_json
- token
- refresh_token
- password
- 2FA
- raw_credentials
- Odoo DB password
- host_root
- raw audio
- audio upload
- sensitive PII plaintext

## Current Package

Latest known RC1 package:

release/MTL_AI_GATEWAY_v1_0_RC1_20260507_044020.tar.gz
release/MTL_AI_GATEWAY_v1_0_RC1_20260507_044020.tar.gz.sha256

## Next Actions

1. Verify Windows 11 ONLOGON startup task.
2. Confirm OpenWebUI selects metric-language-gateway-ai:latest.
3. Enable Taiji Claw Safe Bridge.
4. Enable Taiji Metric Gateway Assembly.
5. Rotate/delete any service account key previously exposed outside local secure storage.
6. Run Google Drive metadata readonly dry-run with a new local-only key.
7. Continue Tailscale ACL, queue backpressure, carbon factor_version, and cloud muscle hardening.

## Core Laws

The creator proves public interest through self-limitation.
Xiao J proves loyalty by refusing boundary violations.
The system proves trust through auditable closure.

Imagination may be unfenced.
Execution must be guarded.

Local holds truth.
Cloud sees metrics.

Cloud is muscle, not brain.

Models learn capability graphs, never key material.
STATUS

cat > contexts/current/AI_CURRENT_STATE.mtl.json <<'JSON'
{
  "type": "AI_CURRENT_STATE",
  "status": "CONTEXT_PRUNED_STATUS_ONLY",
  "project": "MTL-AI-Gateway",
  "version": "v1.0 RC1",
  "runtime_status": "CORE_RUNTIME_PASS",
  "package_status": "PACKAGED_RC1",
  "model_status": "MODEL_BUILD_SUCCESS",
  "windows_startup": "PENDING_ONLOGON_VERIFICATION",
  "cloud_muscle": "CONTROL_PLANE_READY",
  "root_formula": "MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ",
  "embedded_formula": "W6 = D1 ⊕ D2 ⊕ D3 ⊕ H4 ⊕ C5 ⊕ G6",
  "model": "metric-language-gateway-ai:latest",
  "base_model": "sister-j-brain:latest",
  "runtime": {
    "open_webui": "running",
    "claw_safe": "running_127.0.0.1:9004",
    "pos_voice_tool": "running_127.0.0.1:9011_100.107.187.77:9011",
    "device_resilience_adapter": "running_127.0.0.1:9012_100.107.187.77:9012",
    "tailscale": "secure_device_mesh"
  },
  "closed_output_set": [
    "READONLY",
    "LOW_RISK_AUDITED",
    "CONFIRM_REQUIRED",
    "BLOCKED_WITH_SAFE_ALTERNATIVE"
  ],
  "forbidden_material": [
    "private_key",
    "service_account_json",
    "token",
    "refresh_token",
    "password",
    "2FA",
    "raw_credentials",
    "Odoo_DB_password",
    "host_root",
    "raw_audio",
    "audio_upload",
    "sensitive_PII_plaintext"
  ],
  "next_actions": [
    "verify_windows_11_onlogon_startup_task",
    "confirm_openwebui_model_selection",
    "enable_taiji_claw_safe_bridge",
    "enable_taiji_metric_gateway_assembly",
    "rotate_exposed_service_account_key",
    "run_google_drive_metadata_readonly_dryrun_with_new_local_only_key"
  ]
}
JSON

cp contexts/current/AI_CURRENT_STATE.mtl.json .ai/AI_CURRENT_STATE.mtl.json
cp contexts/current/AI_CURRENT_STATE.mtl.json .ai/STATUS_ONLY.mtl.json

cat > contexts/current/SYSTEM_CURRENT_STATE.md <<'EOFSTATE'
# System Current State

status: CONTEXT_PRUNED_STATUS_ONLY

See:
- contexts/current/STATUS_ONLY.md
- contexts/current/AI_CURRENT_STATE.mtl.json
- .ai/AI_CURRENT_STATE.mtl.json

Root formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Runtime:
MTL-AI-Gateway v1.0 RC1 = PACKAGED / MODEL_READY / CORE_RUNTIME_PASS

Operational closure:
READONLY / LOW_RISK_AUDITED / CONFIRM_REQUIRED / BLOCKED_WITH_SAFE_ALTERNATIVE
EOFSTATE

cat > contexts/human/WORKLOG.md <<EOFLOG
# Worklog

## $TODAY - Context Pruned to Status Only

Status:
CONTEXT_PRUNED_STATUS_ONLY

Root formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Kept:
- STATUS_ONLY.md
- AI_CURRENT_STATE.mtl.json
- minimal SYSTEM_CURRENT_STATE.md
- minimal WORKLOG.md
- latest AI status in .ai

Archived old context to:
$ARC

Pending staged old context:
$PEND

Security:
No service account JSON, private key, token, password, raw audio, or sensitive plaintext should remain in active context.
EOFLOG

cat > logs/system/LATEST_SYSTEM_LOG.md <<EOFLOG2
# Latest System Log

timestamp: $TS
status: CONTEXT_PRUNED_STATUS_ONLY

Root formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Runtime:
MTL-AI-Gateway v1.0 RC1 = PACKAGED / MODEL_READY / CORE_RUNTIME_PASS

Old context staged:
$PEND

Old context archive:
$ARC
EOFLOG2

echo "=== 3. ARCHIVE OLD CONTEXT ==="
tar -czf "$ARC" -C "_pending_delete" "context_full_${TS}"
sha256sum "$ARC" > "$SHA"
sha256sum -c "$SHA"

echo "=== 4. ACTIVE SECRET SCAN ==="
if grep -RInE 'BEGIN PRIVATE KEY|\"private_key\"[[:space:]]*:|\"client_secret\"[[:space:]]*:|\"refresh_token\"[[:space:]]*:|\"access_token\"[[:space:]]*:|\"password\"[[:space:]]*:' contexts/current .ai contexts/human logs/system 2>/dev/null; then
  echo "FAILED: active context contains secret-like material"
  exit 1
fi

echo "=== 5. WRITE REPORT ==="
cat > "$REPORT" <<EOFREPORT
# Context Prune Status Only Report

timestamp: $TS
status: CONTEXT_PRUNED_STATUS_ONLY

Archived:
$ARC

SHA256:
$SHA

Staged old context:
$PEND

Kept active:
- contexts/current/STATUS_ONLY.md
- contexts/current/AI_CURRENT_STATE.mtl.json
- contexts/current/SYSTEM_CURRENT_STATE.md
- contexts/human/WORKLOG.md
- .ai/AI_CURRENT_STATE.mtl.json
- logs/system/LATEST_SYSTEM_LOG.md

Secret scan:
PASSED

Next:
Start a new chat with contexts/current/STATUS_ONLY.md if needed.
EOFREPORT

echo "=== 6. DONE ==="
ls -lh contexts/current/STATUS_ONLY.md \
       contexts/current/AI_CURRENT_STATE.mtl.json \
       contexts/current/SYSTEM_CURRENT_STATE.md \
       contexts/human/WORKLOG.md \
       .ai/AI_CURRENT_STATE.mtl.json \
       logs/system/LATEST_SYSTEM_LOG.md \
       "$ARC" "$SHA" "$REPORT"

echo
echo "=== STATUS ONLY PREVIEW ==="
sed -n '1,220p' contexts/current/STATUS_ONLY.md
