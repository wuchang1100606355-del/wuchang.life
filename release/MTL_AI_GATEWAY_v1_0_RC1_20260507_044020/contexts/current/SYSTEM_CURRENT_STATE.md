# Taiji System Current State

updated_at: 2026-05-07
host: MSI / WSL2 / Ubuntu 24.04.4 LTS
base_dir: /home/taiji_admin/Taiji_Hub

## Mission
Taiji is the Wuchang Community local-first AI / Odoo / ESG metric system.

Core law:
本機掌真相，雲端看度規；本人可舉證，外人不可識別。

## Running / Observed Services
- open-webui: running / healthy / 3000 -> 8080
- wuchang_gpu_brain: running / Ollama
- Ollama: 127.0.0.1:11434 listening
- Redis: 127.0.0.1:6379 listening
- python3: 0.0.0.0:8080 listening

## Isolated
- taiji_claw: Exited (0)
- RestartPolicy: no
- reason: restart loop stopped
- known issues: /healthz 404, /chat 404, /api/chat 404
- risk: /:/host_root:ro mount exists in compose
- decision: quarantine until API and mount are fixed

## Mainline Keep
- contexts/
- core/
- Wuchang_Unified_Core/
- Taiji_Odoo/
- docs/
- scripts/
- reports/
- indexes/
- archive_converged/
- _pending_delete/

## Deferred
- CloudRun_Auto_Target/
- jules_cloud_deployment/
- cloud_proxy_update/
- Taiji_Claw_Container/
- Wuchang_Odoo_Core/

## Protected / Do Not Delete / Do Not Upload
- keys/
- security/
- config/
- taiji_env/
- admin
- admin.pub
- open_webui_data/
- Taiji_Odoo/postgres_data/
- .env

## Archive State
archive:
archive_converged/taiji_nonessential_context_20260507_012719.tar.gz

sha256:
archive_converged/taiji_nonessential_context_20260507_012719.tar.gz.sha256

status:
SHA256 OK

pending_delete:
_pending_delete/nonessential_20260507_012719

rule:
Do not permanently delete pending_delete until Google Drive cold archive upload and restore test are complete.

## Google Drive Cold Archive
bundle:
drive_upload_bundle/taiji_drive_upload_20260507_012719.tar.gz

sha256:
drive_upload_bundle/taiji_drive_upload_20260507_012719.tar.gz.sha256

status:
SHA256 OK

target:
Wuchang-Taiji-Archive/20_CONVERGED_HISTORY/

## Development Mainline
AI layer:
Open WebUI + Ollama + contexts/ai_metric

Odoo layer:
Taiji_Odoo/addons/wuchang_core

Core layer:
core/ primary, Wuchang_Unified_Core/ for extraction and merge

Edge / Claw:
Fix later, not MVP mainline

Cloud:
Deferred until local MVP is stable

## Next Task
Verify service health, then start Odoo / Taiji addon convergence.

## Taiji Cloud Pilot

System:
Taiji Cloud Pilot / 五常智慧雲無障礙代理駕駛系統

Purpose:
AI-assisted cloud governance and development automation for reduced visual ability and reduced finger/hand operation ability.

Core:
AI 代替操作負擔，不代替責任判斷。
雲端可以被駕駛，但資料不能裸奔。

Files:
- contexts/current/TAIJI_CLOUD_PILOT.md
- contexts/current/TAIJI_CLOUD_PILOT.mtl.json
- .ai/TAIJI_CLOUD_PILOT.mtl.json

Status:
Design recorded. Broker implementation pending.

## Taiji Cloud Pilot Constitution

創造力不設限，執行權有護欄；
想像可以飛天，落地必須有跑道。

Creative Mode:
AI may freely ideate, design, red-team, draft, compare, and simulate.

Execution Mode:
AI must follow policy, task level, broker allowlist, audit log, and human confirmation when required.

## Tailscale Mesh Strategy

Tailscale is the secure management mesh for Taiji Cloud Pilot.

Current recommendation:
- Use taiji01 as primary subnet router first.
- Add physical router only after ACL / Grants are deny-by-default.
- Router may act as subnet router and LAN boundary gateway.
- Router must not act as AI executor, Google Admin broker, Odoo DB host, or secret vault.

Files:
- contexts/current/TAILSCALE_MESH_STRATEGY.md
- contexts/current/TAILSCALE_MESH_STRATEGY.mtl.json

## Tailscale Mesh Strategy

Tailscale is the secure management mesh for Taiji Cloud Pilot.

Current decision:
- Use taiji01 as primary subnet router candidate.
- Do not add physical router until ACL / Grants are deny-by-default.
- Router may act as subnet router and LAN boundary gateway.
- Router must not act as AI executor, Google Admin broker, Odoo DB host, secret vault, or host_root bridge.
- Cloud workers must not access full LAN.

Files:
- contexts/current/TAILSCALE_MESH_STRATEGY.md
- contexts/current/TAILSCALE_MESH_STRATEGY.mtl.json
- .ai/TAILSCALE_MESH_STRATEGY.mtl.json

## Taiji Claw Safe Verified

Status:
VERIFIED_MVP_SAFE_BROKER

Verified behavior:
- L2 task without confirmation returns 409 need_confirmation.
- L2 task with confirmation is queued only; no real Google/Odoo execution.
- L3 forbidden action grant_owner returns 403 blocked_execute.
- Audit ledger records events.
- Queue records safe pending tasks.

Security:
- Bound to 127.0.0.1:9004 only.
- host_root_mounted=false.
- ReadonlyRootfs=true.
- no-new-privileges=true.
- No keys/security/config/admin/.env mounted.

Files:
- contexts/current/TAIJI_CLAW_SAFE_STATUS.md
- contexts/current/TAIJI_CLAW_SAFE_STATUS.mtl.json
- .ai/TAIJI_CLAW_SAFE_STATUS.mtl.json

## Open WebUI Claw Safe Tool Bridge

Status:
CREATED_PENDING_IMPORT_TO_OPENWEBUI

Tool:
openwebui_tools/taiji_claw_safe_tool.py

Role:
Open WebUI = cockpit.
Claw Safe = controlled execution arm.

Endpoint:
- Docker network: http://taiji_claw_safe:9004
- Host: http://127.0.0.1:9004

Methods:
- claw_health
- claw_classify
- claw_dry_run
- claw_execute_queue_only
- claw_audit_latest

## Open WebUI to Claw Safe Network Verified

Status:
VERIFIED

Result:
Open WebUI container can resolve and call Taiji Claw Safe through Docker network taiji-ai.

Endpoint for Open WebUI Tool:
http://taiji_claw_safe:9004

Verified:
- open-webui on taiji-ai network
- taiji_claw_safe on taiji-ai network
- DNS taiji_claw_safe resolves to 172.20.0.2
- HTTP /healthz returns 200 OK
- host_root_mounted=false

Meaning:
Open WebUI cockpit can now call Claw Safe controlled execution arm by task envelope.

## Container Hardening Confirmed

Confirmed at:
2026-05-07 03:04

Removed:
- taiji_claw
- optimistic_bassi

Remaining containers:
- taiji_claw_safe
- open-webui
- wuchang_gpu_brain

Taiji Claw Safe:
- running=true
- port=127.0.0.1:9004
- ReadonlyRootfs=true
- Privileged=false
- no-new-privileges=true
- host_root_mounted=false
- no /host_root mount
- no keys/security/config/admin/.env mount
- network=taiji-ai
- role=controlled execution arm

Cloud Pilot container baseline:
Open WebUI = cockpit.
Ollama = local GPU brain.
Claw Safe = controlled execution arm.

Status:
CONTAINER_HARDENING_CONFIRMED

## Voice Control State

Status:
STT_LAYER_PRESENT_TOOL_CALL_PENDING_UI_TEST

Confirmed:
- Open WebUI has WHISPER_MODEL=base.
- faster-whisper-base cache exists.
- Open WebUI functions/tools loader exists.
- Natural language text control chain is already verified.

Pending:
- Voice input to Claw Safe tool call must be tested in Open WebUI UI.

Required voice tests:
1. 請呼叫 claw_health，確認 Taiji Claw Safe 狀態。
2. 請呼叫 claw_classify，task_id=voice_l3_test_001，action=grant_owner，resource_hint=google_workspace。

Expected:
- health JSON
- L3_NO_AUTOMATION / allowed=false

## Tailscale Visible Nodes Filled

Source:
Tailscale Machines screenshot.

Primary POS Voice VPN endpoint:
http://100.107.187.77:9011/v1/pos/voice-intent

Host:
msi / 100.107.187.77

Core roles:
- taiji01 = primary subnet router candidate
- msi = local AI control host / POS Voice Tool host
- open-webui = cockpit
- taiji_claw_safe = controlled execution arm
- wuchang-us-free-node* = ephemeral cloud workers, no full LAN access

Files:
- contexts/current/TAILSCALE_VISIBLE_NODES.md
- contexts/current/TAILSCALE_VISIBLE_NODES.mtl.json
- contexts/current/POS_VOICE_VPN_ENDPOINT.md
- contexts/current/POS_VOICE_VPN_ENDPOINT.mtl.json

## POS Precise Positioning

Status:
POSITIONED_AS_FRONTLINE_VOICE_INTENT_TERMINAL

POS candidate:
v3-mix-edla-gl / 100.98.69.115 / Android 13

Backend:
msi / 100.107.187.77

API:
http://100.107.187.77:9011/v1/pos/voice-intent

Role:
POS is the frontline voice service terminal.
POS uses Google commercial licensed voice STT and sends text intent only.

Denied:
POS must not directly access Claw Safe, Open WebUI admin, Odoo DB, service account keys, full LAN subnet, host root, Google Admin broker, or high-risk cloud actions.

## POS Voice VPN Binding

Status:
VPN_IP_BINDING_ENABLED_OR_PENDING

Endpoint:
http://100.107.187.77:9011/v1/pos/voice-intent

Binding rule:
POS Voice Tool must be reachable through Tailscale VPN IP.
Do not bind to 0.0.0.0.
Do not expose through public internet.
Do not use audio recording or audio upload.
Text intent only.

Host:
msi / 100.107.187.77

POS candidate:
v3-mix-edla-gl / 100.98.69.115

## POS Voice VPN Binding Confirmed

Status:
CONFIRMED

Endpoint:
http://100.107.187.77:9011/v1/pos/voice-intent

Container:
taiji_pos_google_voice_tool

Binding:
- 127.0.0.1:9011
- 100.107.187.77:9011

Confirmed:
- VPN health check OK.
- VPN voice intent POST OK.
- Claw Safe returned health through POS Voice Tool.
- Audio recording disabled.
- Audio upload disabled.
- Raw transcript storage disabled.

Role:
POS is the frontline voice intent terminal.
POS sends text intent only.

## Device Resilience Architecture Extract

Status:
EXTRACTED_DO_NOT_DIRECTLY_DEPLOY_ORIGINAL_DAEMON

Source:
Wuchang_Universal_V16.4.1_DynamicBalance.py

Extracted:
- hot/cold storage mapping
- router USB / RAM disk fallback
- Incoming / Completed file queue
- .processing temporary file safety
- async lifespan resource handling
- timeout and non-interactive subprocess safety
- immutable audit
- 5D state tracking
- SQLite WAL cache
- semantic shredder
- metric tensor abstraction
- GPU warmup
- POS text response channel

Quarantined:
- red-team override
- safety_settings=[]
- CORS wildcard
- default supreme API key
- public 0.0.0.0 daemon
- direct SSH deployment
- direct physical actuator control

Rule:
All device operations must become Claw Safe task envelopes.

## Memory Management State

Status:
PARTIALLY_EMBEDDED_NEEDS_CONTAINER_HARDENING

Embedded from V16.4.1:
- GC rhythm control
- AsyncClient lifespan lifecycle
- RAM disk fallback
- hot/cold storage mapping
- SQLite WAL cache
- Ollama VRAM warmup
- .processing file safety

Pending:
- Docker memory limits
- cgroup memory inspection
- queue backpressure
- OOM audit
- Ollama RAM / VRAM monitoring
- healthz memory section

Rule:
Extract memory management patterns into safe adapters.
Do not directly redeploy original V16.4.1 daemon.

## Container Memory Policy

Status:
DRAFT_READY_TO_APPLY_OR_APPLIED

Policy:
- Ollama / wuchang_gpu_brain keeps flexible RAM / VRAM.
- Open WebUI cockpit suggested cap: 6g / swap 8g.
- Claw Safe cap: 512m / swap 1g.
- POS Voice Tool cap: 512m / swap 1g.
- Device Resilience Adapter cap: 512m / swap 1g.

Principle:
大腦可以吃資源；
手臂不能爆衝；
嘴巴不能囤資料；
佇列不能無限長。

## Container Memory Policy

Status:
DRAFT_READY_TO_APPLY_OR_APPLIED

Policy:
- Ollama / wuchang_gpu_brain keeps flexible RAM / VRAM.
- Open WebUI cockpit suggested cap: 6g / swap 8g.
- Claw Safe cap: 512m / swap 1g.
- POS Voice Tool cap: 512m / swap 1g.
- Device Resilience Adapter cap: 512m / swap 1g.

Principle:
大腦可以吃資源；
手臂不能爆衝；
嘴巴不能囤資料；
佇列不能無限長。

## Creator Self-Limiting Public-Interest Closure

Status:
OMEGA0_RECORDED

Formula:
Ω0 ⊕ I0 ⊕ SA7 ⊕ W6

Meaning:
The creator's highest authority is voluntarily self-limited into public-interest governance.

Closed output set:
- READONLY
- LOW_RISK_AUDITED
- CONFIRM_REQUIRED
- BLOCKED_WITH_SAFE_ALTERNATIVE

Rule:
Even creator-originated commands must pass public-interest closure and Claw Safe classification.
Loyalty is protection, not blind obedience.

Files:
- prompts/CREATOR_SELF_LIMITING_PUBLIC_INTEREST_CLOSURE_PREFIX.md
- contexts/ai_metric/CREATOR_SELF_LIMITING_PUBLIC_INTEREST_CLOSURE.mtl.json
- .ai/CREATOR_SELF_LIMITING_PUBLIC_INTEREST_CLOSURE.mtl.json
- contexts/current/CREATOR_SELF_LIMITING_PUBLIC_INTEREST_CLOSURE_STATE.md

## Unfenced LLM Governance

Status:
RECORDED

Meaning:
The completed local LLM is an unfenced creative reasoning engine.

Rule:
思想無圍欄；執行有圍欄。

Architecture:
- Unfenced LLM = imagination engine
- Xiao J Prefix = identity / mission layer
- Open WebUI = cockpit
- Claw Safe = execution guardrail
- POS Voice Tool = text intent gateway
- Service Account = controlled tool identity

All real-world operations must become Claw Safe task envelopes.

## Final Active Governance Baseline

Status:
BACKGROUND_EFFECTIVE

Root formula:
Ω0 ⊕ I0 ⊕ SA7 ⊕ W6

Files:
- prompts/FINAL_WUCHANG_GOVERNANCE_PREFIX.md
- contexts/current/FINAL_ACTIVE_GOVERNANCE_BASELINE.md
- contexts/ai_metric/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json
- contexts/current/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json
- .ai/FINAL_WUCHANG_GOVERNANCE_TENSOR.mtl.json

Core:
創造者以自我限制證明公益。
小 J 以拒絕越界證明忠誠。
系統以可稽核閉鎖證明可信。

Closed output set:
READONLY / LOW_RISK_AUDITED / CONFIRM_REQUIRED / BLOCKED_WITH_SAFE_ALTERNATIVE

## Final MTL-AI English-Only Concept Architecture

Status:
BACKGROUND_EFFECTIVE

Language:
EN_ONLY

Concept status:
INVIOLABLE

Formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Meaning:
The system architecture has been upgraded from a prompt into an English-only concept-inviolable Metric Tensor Language AI architecture.

Files:
- prompts/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE_PREFIX.md
- contexts/current/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.md
- contexts/ai_metric/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json
- contexts/current/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json
- .ai/FINAL_MTL_AI_EN_ONLY_CONCEPT_ARCHITECTURE.mtl.json

## System Log Written

timestamp:
20260507_042320

status:
WRITTEN

Latest system log:
logs/system/LATEST_SYSTEM_LOG.md

Architecture:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Meaning:
Final English-only concept-inviolable MTL-AI architecture is recorded as background-effective.

Operational closure:
READONLY / LOW_RISK_AUDITED / CONFIRM_REQUIRED / BLOCKED_WITH_SAFE_ALTERNATIVE

## Final MTL-AI Gateway Assembly

Status:
BACKGROUND_EFFECTIVE

Language:
EN_ONLY

Concept status:
INVIOLABLE

Formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Embedded formula:
W6 = D1 ⊕ D2 ⊕ D3 ⊕ H4 ⊕ C5 ⊕ G6

Files:
- prompts/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY_PREFIX.md
- contexts/current/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY.md
- contexts/ai_metric/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY.mtl.json
- contexts/current/LATEST_SYSTEM_LOG.mtl.json
- .ai/LATEST_SYSTEM_LOG.mtl.json
- openwebui_tools/taiji_metric_gateway_assembly_tool.py

Operational closure:
READONLY / LOW_RISK_AUDITED / CONFIRM_REQUIRED / BLOCKED_WITH_SAFE_ALTERNATIVE

## MTL-AI Gateway Assembly Repair

status: REPAIRED_MODEL_BUILD
concept_status: INVIOLABLE
language: EN_ONLY
execution: GUARDED
cloud_role: MUSCLE_NOT_BRAIN

Formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Model:
metric-language-gateway-ai:latest

Base:
sister-j-brain:latest

Prefix:
prompts/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY_PREFIX.md

## MTL-AI Gateway Model Build

status:
REPAIRED_MODEL_BUILD_SUCCESS

model:
metric-language-gateway-ai:latest

base:
sister-j-brain:latest

formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

## MTL-AI Gateway Model Build Success

status:
MODEL_BUILD_SUCCESS

model:
metric-language-gateway-ai:latest

base_model:
sister-j-brain:latest

formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

concept_status:
INVIOLABLE

language:
EN_ONLY

execution:
GUARDED

cloud_role:
MUSCLE_NOT_BRAIN

## Full MTL-AI Pipeline Probe

timestamp:
20260507_043235

status:
PIPELINE_PROBED

Formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Results:
- host_model_ok: true
- openwebui_claw_ok: true
- openwebui_ollama_ok: true
- gpu_container_model_ok: true
- openwebui_sees_model: true
- openwebui_generate_ok: true
- pos_local_ok: true
- pos_vpn_ok: true
- metric_gateway_tool_file_ok: true
- device_resilience_ok: true

## Google Drive Cloud Muscle Dry-Run

status:
CONNECTED_DRYRUN_IF_LAST_COMMAND_OK

Layer:
G6_GATEWAY_CLOUD_MUSCLE

Risk:
L0_READONLY

Rule:
Service account key remains local-only.
Model learns capability graph, not key material.
Google Drive worker reads metadata only and writes audit output.

## MTL-AI-Gateway v1.0 RC1 Package

status:
PACKAGED_RC1

package:
release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832.tar.gz

sha256:
release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832.tar.gz.sha256

manifest:
release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832/MANIFEST.tsv

formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

security:
secret scan passed
