# Taiji Governance Progress

Status date: 2026-05-10

## Completed

- Read-only workspace inventory completed.
- Tailscale CSV inventory parsed without reading endpoint details.
- Router information accepted as authorized user-provided context.
- Five Metric Engine `/health` and `/policy` checked.
- Odoo runtime checked for localhost binding, database filter, and database-manager exposure.
- L3 metric hazard identified in legacy Tailscale deployment code.
- Governance scaffold created.
- Cafe main-store deployment status document created.
- Taiji digital identity manifest created.
- Legacy Tailscale deployer converted to manifest-only mode.
- Legacy Tailscale deployer received preflight-only local checks; no live execute path added.
- Legacy Tailscale deployer no longer exposes an `--execute` CLI flag.
- Manifest-only test completed without live deployment.
- Preflight-only test completed and blocked safely with `L3_metric_hazard`.
- System total probe with local-hardware-bound one-time decrypt added.
- System total probe now requires local authorization for every command invocation.
- AI rescue snapshot mode added for context-loss and model-drift recovery.
- Taiji layers and standards architecture profile added to governance metadata.
- Physical anchor and cryptographic envelope layers added to rescue snapshots.
- Human decision receipt gate added: without human decision, operational probe/decrypt/rescue commands are unavailable.
- Red/blue review is available only for local system design review; it is not a daily runtime mechanism.
- Vector Runtime Lite launcher converted to plan-only; embedded live start path removed.
- Vector Runtime Lite local skeleton created.
- Chinese whitepaper drafted under `docs/taiji_hub_whitepaper_zh.md`.
- Runtime snapshot generated under `Taiji_Governance/baseline/`.
- Wuchang community system intent functionalized under `docs/wuchang_community_system_functional_structure_zh.md`.
- Whitepaper updated with commissioner/developer context, AI POS, AI committee equipment management, and authorization-scoped automation model.
- Architecture profile updated with Wuchang community domain profile and AI autonomy levels A0-A5.
- XiaoJ behavior policy added: all AI actions must align through the metric topology gateway before moving across design/development/test/governance/deployment/runtime windows.
- Metric integrity model added: human authority and XiaoJ are public/community metric guardians; invariants are immutable while metric parameters evolve through versioned, audited data evidence.
- Metric-rule computation law added: degree is tensor calculation, rule is vector calculation, and the gateway translates metric tensors into rule-vector action boundaries.
- Public-benefit value generation example added: carbon-rights style external signals may become development-fund candidate proposals only after compliance, accounting, audit, and human decision.
- Anti-privatization policy added: public/community/fund-pool value cannot be redirected to private profit; suspicious intent is treated as compromised-principal L3, while legitimate labor and intellectual contribution may be quantified through audited compensation rules.
- Absolute-value calculation baseline added: metric computation must not apply preset value; it must preserve civilization continuity, basic livelihood, executable public benefit, fund-pool survivability, and legitimate contribution compensation.
- Finance/accounting precise window added: fund pool, compensation, revenue, tax, payment, carbon-rights landing, and accounting outputs require accountant or qualified accounting review.
- Architecture and completion board created under `docs/taiji_hub_architecture_completion_board_zh.md`.
- Read-only container scan completed: observed Odoo/Postgres, Governance, voice gateway, device resilience adapter, POS voice tool, claw safe, Open WebUI, and Ollama/GPU brain containers.
- Actual node/device topology diagram added with developer laptop as governance baseline and distributed compute as expandable subordinate nodes.
- Metric predictive alert system created under `docs/taiji_hub_predictive_alert_system_zh.md` with proactive developer prompts.
- Google Workspace organization policy gateway design added with no-live-API, no-service-account-readout, Odoo no-personal-data mailbox, and minimal scope principles.
- Device least-privilege and AI browser UI design added: browser automation is a constrained user interface, not a super-admin bypass.
- Local metric predictive alert scanner implemented under `Taiji_AutoBuild/scripts/06_metric_predictive_alert.py`.
- Odoo/Google extension spec added: Odoo is the primary scenario system, Google Workspace is non-sensitive account/permission metadata management, and separation of duties prevents single-party dominance.
- Predictive alerts now require recommended solutions and solution impact assessments before being pushed to developers.
- Five-dimensional code zero-tree tensor I/O assessment added: feasible for non-sensitive metadata/hash/label/audit transport, read, and gated writes; forbidden for secrets, personal data, or replacing the metric assembly.
- Cloud/local auto-account bridge defined as manifest-only until Gateway/Five Metric/human decision, with append-only redacted audit journal required.
- Odoo to Google for Nonprofits mailbox bridge spec and manifest added for `wuchang.life`, using Google Workspace for Nonprofits no-charge baseline and `smtp-relay.gmail.com` as candidate relay; no live Google/Odoo change executed.
- Five-Metric Tensor Runtime specification added under `docs/taiji_five_metric_tensor_runtime_zh.md`, defining TensorPacket conversion, replay governance, tensor deadbox lifecycle, distributed topology governance, audit flow, multimodal routing, plaintext-free context preservation, and human decision boundaries.
- TensorPacket machine-readable schema added under `schemas/tensor_packet.schema.json`.
- Five-Metric runtime reconciliation pass completed under `Taiji_Governance/runtime/`, adding standalone plaintext-free context runtime, replay runtime, tensor deadbox lifecycle, AI usage governance, non-linguistic tensor runtime, enforcement boundary, distributed reconciliation, packet lifecycle, runtime identity, multimodal governance, completion matrix, topology map, trust boundary diagram, and replay/deadbox risk matrix.
- Multi-Governance Identity architecture added under `Taiji_Governance/identity/`, separating Runtime Owner, System Architect, Community Governor, Technology Sponsor, Runtime Operator, Private Commercial Operator, and Community Industry Operator with identity tensor schema, authority matrix, Odoo model, container/domain separation, public/commercial policy, sponsor and hardware lending policies, fund-pool governance, human decision boundary, audit/data scope matrices, replay risk, deadbox identity policy, and governance event log schema.

## In Progress

- Converting deployment work into manifest-first, audit-first flow.
- Recording cafe main-store node roles without secrets.
- Confirming customer display 02 and Sunmi POS device identities.
- Inventorying existing POS implementation so it can be separated into governed modules, local tests, and non-sensitive demo data.
- Keeping community operations marked as design/not-enabled until explicit production activation is separately approved.
- Translating value anchors into testable policy checks for future Gateway/Five Metric integration.
- Defining metric evolution proposals so future data-driven changes preserve audit, SHA256 baseline, rollback, and human decision.
- Converting the degree/tensor and rule/vector law into future machine-checkable schemas for Gateway/Five Metric enforcement.
- Keeping sustainability or carbon-rights ideas in design/proposal state until evidence, legal/accounting review, and public-benefit definition exist.
- Designing auditable contribution-compensation schemas that distinguish legitimate compensation from public-asset privatization.
- Defining value-peak optimization as constrained by public-benefit execution and fund-pool survivability, not as private profit maximization.
- Turning the architecture completion board into an operational status dashboard after POS inventory is completed.
- Turning predictive alert design into a local read-only scanner that produces L1/L2/L3 developer prompts.
- Designing laptop-poweroff continuity: rescue snapshot, audit, manifest, and Gateway/Five Metric reconciliation.
- Sandbox-verifying the predictive alert scanner and red-team correcting findings before any runtime automation.
- Building Odoo role to Google group/OU label mapping without syncing personal data.
- Designing five_dim_code schema and zero_tree_tensor_io schema for non-sensitive Odoo/Google/Gateway bridge manifests.
- Preparing Odoo no-personal-data mailbox setup and SMTP relay sandbox plan for human admin review.
- Converting Five-Metric Tensor Runtime from specification/schema into local policy stubs and tests without live deployment or external APIs.
- Converting generated runtime governance files into future local validators and policy stubs after review.
- Preparing future Odoo company/branch/customer and container separation manifests from the Multi-Governance Identity architecture; no live Odoo/container migration has been executed.

## Not Started

- Real VPN ACL change.
- Router configuration change.
- Odoo configuration change.
- Google Workspace / Gemini / Admin API call.
- Service account credential activation.
- Remote SSH deployment.
- Live execute path inside `legacy_core/wuchang_tailscale_deployer.py`.
- Production activation of community operations.
- Live A5 automation.
- Formal finance/accounting operation without accountant review.
- Runtime predictive alert automation.
- Live Google Workspace Admin/Gmail/API integration.
- One-sided control architecture that lets Odoo, Google, AI, Gateway, finance, or developer authority dominate the full system alone.
- Any refactor that deprecates, bypasses, or replaces the metric assembly.
- Odoo/Google mailbox live connection before sandbox test, human admin review, Gateway/Five Metric preflight, and audit readiness.

## Current Preflight Blockers

- Local Tailscale status/IP checks failed in this execution context.
- Five Metric Engine `/health` or `/policy` was unreachable in this execution context, so `policy_locked=true` could not be confirmed.
- Audit log write succeeded.
- `taiji-metric-preflight` command exists.

## Current Governance Decision

The system may create non-sensitive command configuration and deployment manifests.
It must not distribute secrets or perform live external API operations until the
Gateway, Audit, Policy, and Five Metric preflight checks all pass.
