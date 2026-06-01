# Worktree Remediation Plan Before Production Copy Set

Generated at: 2026-06-02T00:49:52+08:00
Current HEAD: `7643882`
Previous canonical cutover HEAD: `fbba14b`
Mode: `plan-only remediation`

## Governance Boundary

- This report is a plan only. No remediation action was executed.
- Classification uses committed path-only evidence. Drift file contents were not read.
- No delete, reset, checkout, copy, deploy, DB write, or service restart was executed.
- `git_space/scripts_git_bundle_backup.sh` is a listing-only utility exception and remains excluded from the production copy set.

## Input Evidence

- `reports/server_handoff/dirty_worktree_reconcile_20260602_004526.md`
- `evidence/server_handoff/dirty_worktree/git_status_porcelain_20260602_004526.txt`
- `evidence/server_handoff/dirty_worktree/git_typechange_20260602_004526.txt`
- `evidence/server_handoff/dirty_worktree/untracked_files_20260602_004526.txt`

## Dirty Summary

```text
TOTAL=491
 M=478
 T=8
 D=1
??=4
staged=0
```

## Counts By Category

| Category | Count |
| --- | ---: |
| `COMMIT_PRODUCTION_CANDIDATE` | 328 |
| `COMMIT_EVIDENCE_OR_DOC` | 145 |
| `EXCLUDE_GENERATED_NOISE` | 3 |
| `RESTORE_DELETED_NOISE` | 1 |
| `HUMAN_REVIEW_REQUIRED` | 2 |
| `TYPECHANGE_REVIEW_REQUIRED` | 8 |
| `UNTRACKED_REVIEW_REQUIRED` | 4 |

## Proposed Commit Batches

### Batch A: Evidence And Documentation

- Source category: `COMMIT_EVIDENCE_OR_DOC`
- Proposed action: review path list, verify no generated state is mixed in, then stage only approved files in a separate executable packet.

### Batch B: Runtime And Odoo Candidates

- Source category: `COMMIT_PRODUCTION_CANDIDATE`
- Proposed action: split into smaller runtime, Odoo, deploy, and tooling batches. Preserve executable mode intentionally where required. Run syntax/schema tests before each commit.

### Batch C: Generated Noise Exclusions

- Source category: `EXCLUDE_GENERATED_NOISE`
- Proposed action: confirm ignore policy or discard strategy in a separately approved packet. Do not include these paths in production copy set.

### Batch D: Deleted Noise Restoration Review

- Source category: `RESTORE_DELETED_NOISE`
- Proposed action: treat Windows alternate-data-stream metadata as noise. Any restore or ignore action requires a separate approved packet.

### Batch E: Manual Decisions

- Source categories: `HUMAN_REVIEW_REQUIRED`, `TYPECHANGE_REVIEW_REQUIRED`, `UNTRACKED_REVIEW_REQUIRED`
- Proposed action: resolve path ownership and intended filesystem semantics before any staging packet.

## Risk Notes

### `Dockerfile.ai`

- Root-level container build input. Do not stage automatically.
- Require human review to decide whether its drift is only mode normalization or an intentional production build change.

### `index.html`

- Root-level UI entry point. Do not stage automatically.
- Require human review to decide whether it is a runtime artifact, a preview artifact, or generated output.

### `dashboard/preview.html:Zone.Identifier`

- Windows alternate-data-stream metadata path.
- Classify as `RESTORE_DELETED_NOISE`; exclude from production copy set.
- Do not restore, delete, or ignore it until a separate remediation packet is approved.

## Exact Paths By Category


### `COMMIT_PRODUCTION_CANDIDATE`

- ` M` `bin/7d-boot-verify`
- ` M` `bin/7d-formation-boot-verify`
- ` M` `bin/7d-formation-packet-test`
- ` M` `bin/7d-formation-status`
- ` M` `bin/7d-status`
- ` M` `bin/check-taiji-metric-guard`
- ` M` `bin/check-taiji-metric-stack`
- ` M` `bin/cloud-api-bridge`
- ` M` `bin/cloud-api-bridge-sa`
- ` M` `bin/phase7-final-report`
- ` M` `bin/phase7-persistent-verify`
- ` M` `bin/phase7-system-snapshot`
- ` M` `bin/redteam-local-audit`
- ` M` `bin/start_7d_formal_tensor_runtime.sh`
- ` M` `bin/stop_7d_formal_tensor_runtime.sh`
- ` M` `bin/taiji-action-run`
- ` M` `bin/taiji-break-glass-off`
- ` M` `bin/taiji-break-glass-on`
- ` M` `bin/taiji-distributed-admin-sync-check`
- ` M` `bin/taiji-enter-new-system`
- ` M` `bin/taiji-guarded-run`
- ` M` `bin/taiji-metric-preflight`
- ` M` `bin/taiji-system-probe`
- ` M` `bin/test-service-account-auth`
- ` M` `bin/validate-cloud-architecture`
- ` M` `bin/verify-action-registry`
- ` M` `bin/wuchang-boot-verify`
- ` M` `bin/wuchang-pos-terminal-enable`
- ` M` `bin/wuchang-push-patent-v08-linux-nodes`
- ` M` `boot/healthcheck.sh`
- ` M` `boot/preflight.sh`
- ` M` `boot/read_startup_state_packet.sh`
- ` M` `boot/safe_shutdown.sh`
- ` M` `boot/start_03_ui.sh`
- ` M` `boot/start_admin_node.sh`
- ` M` `boot/start_docker_stack.sh`
- ` M` `boot/start_edge_node.sh`
- ` M` `boot/start_gateway.sh`
- ` M` `boot/start_native_claw.sh`
- ` M` `boot/start_xiaoj_intent_field_on_login.sh`
- ` M` `boot/taiji_login_readonly_check.sh`
- ` M` `commander/bin/commander_health.py`
- ` M` `commander/bin/commander_health.sh`
- ` M` `commander/bin/global_broadcast_report.sh`
- ` M` `commander/bin/node_sync_dryrun.sh`
- ` M` `connectors/five_metric_client.py`
- ` M` `connectors/five_metric_gate.py`
- ` M` `deploy_jules.sh`
- ` M` `deploy_taiji_safe.ps1`
- ` M` `deploy_v21_3.sh`
- ` M` `deploy/docker/docker-compose.runtime.yml`
- ` M` `deploy/docker/Dockerfile.runtime`
- ` M` `deploy/formal_runtime_pkg_v0_1/docker-compose.yml`
- ` M` `deploy/formal_runtime_pkg_v0_1/Dockerfile`
- ` M` `deploy/formal_runtime_pkg_v0_1/env.example`
- ` M` `deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py`
- ` M` `deploy/formal_runtime_pkg_v0_1/scripts/hash_manifest_v0_1.sh`
- ` M` `deploy/formal_runtime_pkg_v0_1/scripts/health_v0_1.sh`
- ` M` `deploy/formal_runtime_pkg_v0_1/scripts/preflight_v0_1.sh`
- ` M` `deploy/formal_runtime_pkg_v0_1/scripts/rollback_v0_1.sh`
- ` M` `deploy/formal_runtime_pkg_v0_1/scripts/start_v0_1.sh`
- ` M` `deploy/formal_runtime_pkg_v0_1/scripts/stop_v0_1.sh`
- ` M` `deploy/formal_runtime_pkg_v0_1/systemd/taiji-formal-runtime-pkg-v0-1.service`
- ` M` `deploy/host_refactor/taiji01_file_restructure_v0_1/APPLY_HOST_RESTRUCTURE.sh`
- ` M` `deploy/host_refactor/taiji01_file_restructure_v0_1/BUILD_HOST_RESTRUCTURE_PLAN.sh`
- ` M` `deploy/host_refactor/taiji01_file_restructure_v0_1/DRY_RUN_HOST_RESTRUCTURE.sh`
- ` M` `deploy/host_refactor/taiji01_file_restructure_v0_1/HOST_READONLY_INVENTORY.sh`
- ` M` `deploy/host_refactor/taiji01_file_restructure_v0_1/ROLLBACK_HOST_RESTRUCTURE.sh`
- ` M` `deploy/migration/dependency_relocation_v0_1/BUILD_MODEL_ARTIFACT_MANIFEST.sh`
- ` M` `deploy/migration/dependency_relocation_v0_1/OPEN_ADMIN_AUTH_WINDOW.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/APPLY_MIGRATION.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/BUILD_MIGRATION_PLAN.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/CREATE_C_SCENARIO_FOLDERS.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/CREATE_D_MEMBER_VAULT_FOLDERS.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/D_ACCESS_REVIEW_LOG.schema.json`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/D_ACCESS_REVIEW_TEMPLATE.json`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/DRY_RUN.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/PREPARE_ORG_SHARED_STAGING.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/ROLLBACK_STAGING_ONLY.sh`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/VERIFY_MIGRATION.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/MIGRATE_APPLY_NO_DB_VOLUMES.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/MIGRATE_APPLY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/MIGRATE_DRY_RUN.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/migration_plan.json`
- ` M` `deploy/migration/wsl_native_migration_v0_1/POST_MIGRATION_RUNTIME_CHECK.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/POST_MIGRATION_VERIFY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/ROLLBACK_MIGRATION_COPY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/SYNC_RUNTIME_ARTIFACTS_ONLY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/MIGRATE_APPLY_NO_DB_VOLUMES.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/MIGRATE_APPLY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/MIGRATE_DRY_RUN.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/migration_plan.json`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/POST_MIGRATION_RUNTIME_CHECK.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/POST_MIGRATION_VERIFY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/ROLLBACK_MIGRATION_COPY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/SYNC_RUNTIME_ARTIFACTS_ONLY.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/WSL_NATIVE_STATUS.sh`
- ` M` `deploy/migration/wsl_native_migration_v0_1/WSL_NATIVE_STATUS.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/COLLECT_RUNTIME_NODE_INFO.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/DEBUG_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/docker-compose.yml`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/Dockerfile`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/HASH_SCRIPT.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/HEALTH.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/MANIFEST.json`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/PREFLIGHT.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/ROLLBACK.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry_v0_1_1.py`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/SHA256SUMS`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL_V011.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STATUS_LOCAL_V011.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STATUS_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STOP_LOCAL_V011.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STOP_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/systemd.service`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/DEBUG_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/docker-compose.yml`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/Dockerfile`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/env.example`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/HASH_SCRIPT.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/HEALTH.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/MANIFEST.json`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/PREFLIGHT.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/ROLLBACK.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/runtime_entry_v0_1_1.py`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/SHA256SUMS`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL_V011.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/STATUS_LOCAL_V011.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/STATUS_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/STOP_LOCAL_V011.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/STOP_LOCAL.sh`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/systemd.service`
- ` M` `deploy/packages/taiji01_metric_identity_gateway_v0_1/START_CONTAINER.sh`
- ` M` `deploy/packages/taiji01_metric_identity_gateway_v0_1/STATUS_CONTAINER.sh`
- ` M` `deploy/packages/taiji01_metric_identity_gateway_v0_1/STOP_CONTAINER.sh`
- ` M` `deploy/pages/deploy_wuchang_homepage_no_dns.sh`
- ` M` `deploy/scripts/bootstrap_runtime.sh`
- ` M` `deploy/scripts/preflight_check.sh`
- ` M` `deploy/scripts/runtime_status.sh`
- ` M` `deploy/scripts/start_runtime.sh`
- ` M` `deploy/scripts/stop_runtime.sh`
- ` M` `deploy/sync/taiji01_memory_sync_v0_1/PULL_FROM_TAIJI01.sh`
- ` M` `deploy/sync/taiji01_memory_sync_v0_1/PUSH_TO_TAIJI01_MANUAL_ONLY.sh`
- ` M` `deploy/sync/taiji01_memory_sync_v0_1/STATUS_MEMORY_SYNC.sh`
- ` M` `deploy/systemd/taiji-audit.service`
- ` M` `deploy/systemd/taiji-gateway.service`
- ` M` `deploy/systemd/taiji-runtime.service`
- ` M` `dispatch_usb_dlq.sh`
- ` M` `dispatch_usb.sh`
- ` M` `docker-compose.ai.yml`
- ` M` `feed_all.sh`
- ` M` `feed_j.sh`
- ` M` `full_system.sh`
- ` M` `git_space/scripts_git_central_status.sh`
- ` M` `ignite_jules_cloud_run.sh`
- ` M` `install_service.sh`
- ` M` `jules_cloud_deployment/wuchang_commander.sh`
- ` M` `jules_core_v21_2.py`
- ` M` `jules_core_v21_3.py`
- ` M` `jules_core_v21_4.py`
- ` M` `legacy_core/sister_j_agent_core.py`
- ` M` `legacy_core/taiji_8_0_api_gateway.py`
- ` M` `legacy_core/taiji_8_0_main.py`
- ` M` `legacy_core/taiji_f5_protocol.py`
- ` M` `legacy_core/taiji_native_claw.py`
- ` M` `legacy_core/taiji_patent_v3_engine.py`
- ` M` `legacy_core/taiji_redis_engine.py`
- ` M` `legacy_core/taiji_unified_gateway_edge.py`
- ` M` `legacy_core/wuchang_dual_j_workspace_auth.py`
- ` M` `legacy_core/wuchang_gemini_router.py`
- ` M` `legacy_core/wuchang_live_server.py`
- ` M` `legacy_core/wuchang_live_workspace_8000.py`
- ` M` `legacy_core/wuchang_llm_core.py`
- ` M` `legacy_core/wuchang_local_reconstruction_service.py`
- ` M` `legacy_core/wuchang_pos_voice_engine.py`
- ` M` `legacy_core/wuchang_tailscale_deployer.py`
- ` M` `legacy_core/wuchang_translation_service.py`
- ` M` `migrate_to_hub.sh`
- ` M` `models/J_Local_Creator.Modelfile`
- ` M` `models/Wuchang_Adjutant.Modelfile`
- ` M` `nodes_roles.sh`
- ` M` `nodes_summary.sh`
- ` M` `pull_usb_run.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832/scripts/oneclick_full_mtl_ai_pipeline.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832/scripts/oneclick_mtl_ai_assembly.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832/scripts/review/verify_final_governance_baseline.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832/scripts/review/verify_final_mtl_ai_gateway_assembly.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_043832/scripts/review/verify_mtl_ai_en_only_concept_architecture.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_044020/scripts/oneclick_full_mtl_ai_pipeline.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_044020/scripts/oneclick_mtl_ai_assembly.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_044020/scripts/review/verify_final_governance_baseline.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_044020/scripts/review/verify_final_mtl_ai_gateway_assembly.sh`
- ` M` `release/MTL_AI_GATEWAY_v1_0_RC1_20260507_044020/scripts/review/verify_mtl_ai_en_only_concept_architecture.sh`
- ` M` `run_nodes_status.sh`
- ` M` `run_nodes.sh`
- ` M` `run_queue.sh`
- ` M` `runtime_adapters/formal_tensor_runtime_adapter_v0_1.py`
- ` M` `runtime_adapters/taiji_formal_tensor_runtime_v0_1_0_adapter.py`
- ` M` `runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py`
- ` M` `runtime/7d_formal_tensor_runtime_8126.py`
- ` M` `runtime/7d_formation_runtime_8127.py`
- ` M` `runtime/check_7d_full.sh`
- ` M` `runtime/check_7d.sh`
- ` M` `runtime/dead_letter/eamtp_policy_gate.py`
- ` M` `runtime/router/eamtp_7d_translator.py`
- ` M` `runtime/router/eamtp_router_guard_dryrun.py`
- ` M` `runtime/router/merlin_apply_queue.py`
- ` M` `runtime/router/merlin_approval_gate.py`
- ` M` `runtime/router/merlin_human_execution_checklist.py`
- ` M` `runtime/router/merlin_intent_driver.py`
- ` M` `runtime/router/w7tp_causal_event_builder.py`
- ` M` `runtime/start_7d_bagua_runtime.sh`
- ` M` `runtime/taiji_metric_preflight.py`
- ` M` `runtime/utsl_runtime_8128.py`
- ` M` `schemas/formal_tensor_packet.schema.json`
- ` M` `schemas/pos_service_intent.schema.json`
- ` M` `schemas/tensor_packet.schema.json`
- ` M` `scripts/apply_container_memory_policy.sh`
- ` M` `scripts/check_8d_browser_control_gate.py`
- ` M` `scripts/check_patent_system_conformity.sh`
- ` M` `scripts/cloud_muscle/google_drive_inventory_dryrun.py`
- ` M` `scripts/community_3d_map_index.sh`
- ` M` `scripts/diagnose_ollama_network.sh`
- ` M` `scripts/fix_openwebui_ollama.sh`
- ` M` `scripts/gpu_power_logger.sh`
- ` M` `scripts/intake_self_member.sh`
- ` M` `scripts/issue_7d_code.sh`
- ` M` `scripts/member_intake_oneclick_test.sh`
- ` M` `scripts/member_phone_login_oneclick.sh`
- ` M` `scripts/oneclick_full_mtl_ai_pipeline.sh`
- ` M` `scripts/oneclick_mtl_ai_assembly.sh`
- ` M` `scripts/package_mtl_ai_gateway_rc1.sh`
- ` M` `scripts/prune_context_keep_status_only.sh`
- ` M` `scripts/repair_member_session_binding.sh`
- ` M` `scripts/review/verify_final_governance_baseline.sh`
- ` M` `scripts/review/verify_final_mtl_ai_gateway_assembly.sh`
- ` M` `scripts/review/verify_mtl_ai_en_only_concept_architecture.sh`
- ` M` `scripts/security_state_field.sh`
- ` M` `scripts/start_gateway_guard.sh`
- ` M` `scripts/start_gateway.sh`
- ` M` `scripts/taiji_ai_probe.sh`
- ` M` `scripts/taiji_archive_and_stage_delete.sh`
- ` M` `scripts/taiji_container_probe.sh`
- ` M` `scripts/taiji_file_convergence_probe.sh`
- ` M` `scripts/taiji_full_boot.sh`
- ` M` `scripts/taiji_guard.sh`
- ` M` `scripts/taiji_layer_latency_probe.sh`
- ` M` `scripts/taiji_login_readonly_check.sh`
- ` M` `scripts/taiji_memory_probe.sh`
- ` M` `scripts/taiji_status.sh`
- ` M` `scripts/taiji-tool`
- ` M` `scripts/tailscale_mesh_probe.sh`
- ` M` `services/gateway/app.py`
- ` M` `services/gateway/policies/formal_tensor_validator.py`
- ` M` `services/google_login/simple_google_login_server.py`
- ` M` `services/line_login/simple_line_login_server.py`
- ` M` `setup_jules_daemon.sh`
- ` M` `smart_dispatch.sh`
- ` M` `Taiji_AutoBuild/scripts/00_readonly_probe.sh`
- ` M` `Taiji_AutoBuild/scripts/01_import_chatgpt_export.py`
- ` M` `Taiji_AutoBuild/scripts/02_start_vector_lite.sh`
- ` M` `Taiji_AutoBuild/scripts/03_collect_runtime_snapshot.sh`
- ` M` `Taiji_AutoBuild/scripts/04_system_total_probe.py`
- ` M` `Taiji_AutoBuild/scripts/05_red_blue_exchange.py`
- ` M` `Taiji_AutoBuild/scripts/06_metric_predictive_alert.py`
- ` M` `taiji_boot_memory_v1.sh`
- ` M` `taiji_hub.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/__init__.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/__manifest__.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/controllers/__init__.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/controllers/google_auth.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/controllers/line_auth.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/models/__init__.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/models/pm3_memory_index.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/models/res_users_proxy.py`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/security/ir.model.access.csv`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_behavior_vector_database_views.xml`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_desensitized_dashboard_views.xml`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_fixed_vector_state_window_views.xml`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_memory_index_views.xml`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_vector_state_window_views.xml`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/views/web_login_templates.xml`
- ` M` `Taiji_Odoo/addons/pm3_runtime_sync/views/web_login_templates.xml.disabled`
- ` M` `Taiji_Odoo/scripts/pm3_reload.sh`
- ` M` `Taiji_Vector_Runtime_Lite/app/__init__.py`
- ` M` `Taiji_Vector_Runtime_Lite/app/main.py`
- ` M` `Taiji_Vector_Runtime_Lite/manifest.yml`
- ` M` `test_fire.py`
- ` M` `tests/test_formal_tensor_validator.py`
- ` M` `tests/test_runtime_entry.py`
- ` M` `tools/causal_ledger_text_analyzer.py`
- ` M` `tools/container_offload_linter.py`
- ` M` `tools/eamtp_packet_summarizer.py`
- ` M` `tools/generate_patent_printable_pdf.py`
- ` M` `tools/generate_readonly_boot_patent_package.py`
- ` M` `tools/ha_mesh_script_analyzer.py`
- ` M` `tools/indexer_oneshot_job_linter.py`
- ` M` `tools/merlin_inventory_fill_helper.py`
- ` M` `tools/merlin_inventory_to_eamtp.py`
- ` M` `tools/merlin_inventory_validator.py`
- ` M` `tools/open_project_dashboard.sh`
- ` M` `tools/project_board_generator.py`
- ` M` `tools/project_dashboard_generator.py`
- ` M` `tools/relative_identity_7d_code_spec_linter.py`
- ` M` `tools/runtime_shadow_inventory.py`
- ` M` `tools/safe_git_stage.py`
- ` M` `tools/service_health_readonly.py`
- ` M` `tools/task_card_generator.py`
- ` M` `tools/w7tp_local_7d_automation_smoke_gate_linter.py`
- ` M` `tools/w7tp_local_7d_automation_smoke_runner.py`
- ` M` `tools/w7tp_nl_to_7d_task_packet_linter.py`
- ` M` `tools/w7tp_smoke_all.sh`
- ` M` `tools/w7tp_tri_party_7d_runtime_dryrun_linter.py`
- ` M` `tools/worklink_builder.py`
- ` M` `tools/xiaoj_converged_governance_architecture_linter.py`
- ` M` `tools/xiaoj_dual_brain_metrics_capture_linter.py`
- ` M` `W7TP_FIELD_ATLAS/gei_context/scripts/generate_gei_snapshot.sh`
- ` M` `wuchang_cognition_archive/scripts/verify_cognition_archive.sh`
- ` M` `wuchang_grand_unification.sh`
- ` M` `Wuchang_Unified_Core/02_Edge_Nodes/wuchang_ai_cerebellum.py`
- ` M` `Wuchang_Unified_Core/systemd_ignition.sh`
- ` M` `Wuchang_Unified_Core/wuchang_core_control.sh`
- ` M` `Wuchang_Unified_Core/wuchang_radar.sh`

### `COMMIT_EVIDENCE_OR_DOC`

- ` M` `deploy/formal_runtime_pkg_v0_1/MANIFEST.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/ASSOCIATION_DATA_AUTHORITY_MATRIX.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/C_SCENARIO_DATA_POLICY.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/C_TO_CLOUD_REDACTION_FLOW.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/MEMBER_VAULT_D_DRIVE_BOUNDARY.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/MEMBER_VAULT_SEALED_MODE.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/NODE_TO_STORAGE_TOPOLOGY.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/ORG_DIGITAL_IDENTITY_BOUNDARY.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/ORG_SHARED_CLOUD_POLICY.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/PRE_ACTIVATION_CUTOVER_CHECKLIST.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/README.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/STORAGE_BOUNDARY_POLICY_V2_C_DRIVE_SCENARIO.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/STORAGE_BOUNDARY_POLICY_V3_ASSOCIATION_AUTHORITY.md`
- ` M` `deploy/migration/multi_target_dependency_migration_v0_1/STORAGE_BOUNDARY_POLICY.md`
- ` M` `deploy/migration/wsl_native_migration_v0_1/README_MIGRATE.md`
- ` M` `deploy/migration/wsl_native_migration_v0_1/README_RSYNC_CODE23.md`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/README_MIGRATE.md`
- ` M` `deploy/migration/wsl_native_migration_v0_1/wsl_native_migration_v0_1/README_RSYNC_CODE23.md`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/README_DEPLOY.md`
- ` M` `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/taiji_formal_tensor_runtime_v0_1_0/README_DEPLOY.md`
- ` M` `docs/distributed_voice_nodes.md`
- ` M` `docs/taiji_five_metric_formal_notation_runtime_zh.md`
- ` M` `docs/taiji_five_metric_tensor_runtime_zh.md`
- ` M` `docs/taiji_hub_architecture_completion_board_zh.md`
- ` M` `docs/taiji_hub_device_least_privilege_browser_ui_zh.md`
- ` M` `docs/taiji_hub_five_dim_zero_tree_tensor_io_assessment_zh.md`
- ` M` `docs/taiji_hub_google_workspace_policy_gateway_zh.md`
- ` M` `docs/taiji_hub_odoo_google_extension_spec_zh.md`
- ` M` `docs/taiji_hub_odoo_google_nonprofit_mail_bridge_zh.md`
- ` M` `docs/taiji_hub_predictive_alert_system_zh.md`
- ` M` `docs/taiji_hub_whitepaper_zh.md`
- ` M` `docs/taiji_natural_intent_pos_gateway_zh.md`
- ` M` `docs/wuchang_community_system_functional_structure_zh.md`
- ` M` `examples/intent_manifests/l3_block_payment_execute.sample.json`
- ` M` `examples/intent_manifests/payment_prepare.sample.json`
- ` M` `examples/intent_manifests/pos_order_create.sample.json`
- ` M` `examples/intent_manifests/service_request.sample.json`
- ` M` `patent_filing/readonly_boot_edge_runtime_m5_v0_1/source_originals/abstract_original.docx`
- ` M` `patent_filing/readonly_boot_edge_runtime_m5_v0_1/source_originals/claims_original.docx`
- ` M` `patent_filing/readonly_boot_edge_runtime_m5_v0_1/source_originals/figures_description_original.docx`
- ` M` `patent_filing/readonly_boot_edge_runtime_m5_v0_1/source_originals/specification_original.docx`
- ` M` `requirements.txt`
- ` M` `Taiji_AutoBuild/prompts/codex_readonly_prompt.md`
- ` M` `Taiji_AutoBuild/prompts/xiaoj_master_prompt.md`
- ` M` `Taiji_Governance/architecture/layers_standards.yml`
- ` M` `Taiji_Governance/baseline/README.md`
- ` M` `Taiji_Governance/baseline/runtime_snapshot_20260510T103532Z.txt`
- ` M` `Taiji_Governance/deployments/cafe_main_redeploy_status.md`
- ` M` `Taiji_Governance/deployments/tailscale_deployment_manifest.json`
- ` M` `Taiji_Governance/deployments/tailscale_preflight_record.json`
- ` M` `Taiji_Governance/deployments/tailscale_rollback_plan.md`
- ` M` `Taiji_Governance/identity/audit_scope_matrix.md`
- ` M` `Taiji_Governance/identity/authority_boundary_matrix.md`
- ` M` `Taiji_Governance/identity/community_industry_fund_pool_policy.md`
- ` M` `Taiji_Governance/identity/container_governance_model.md`
- ` M` `Taiji_Governance/identity/data_scope_matrix.md`
- ` M` `Taiji_Governance/identity/deadbox_identity_policy.md`
- ` M` `Taiji_Governance/identity/digital_identity.yml`
- ` M` `Taiji_Governance/identity/domain_governance_map.md`
- ` M` `Taiji_Governance/identity/governance_event_log_schema.yaml`
- ` M` `Taiji_Governance/identity/hardware_lending_policy.md`
- ` M` `Taiji_Governance/identity/human_decision_boundary.md`
- ` M` `Taiji_Governance/identity/identity_architecture.md`
- ` M` `Taiji_Governance/identity/identity_tensor_schema.yaml`
- ` M` `Taiji_Governance/identity/legal_organization_identity_record.template.json`
- ` M` `Taiji_Governance/identity/legal_responsible_person_record_policy_2026-05-11.md`
- ` M` `Taiji_Governance/identity/multi_governance_identity.md`
- ` M` `Taiji_Governance/identity/odoo_identity_model.md`
- ` M` `Taiji_Governance/identity/primary_system_topology_profile_2026-05-11.md`
- ` M` `Taiji_Governance/identity/public_commercial_separation_policy.md`
- ` M` `Taiji_Governance/identity/replay_identity_risk.md`
- ` M` `Taiji_Governance/identity/runtime_owner_policy.md`
- ` M` `Taiji_Governance/identity/technology_sponsor_policy.md`
- ` M` `Taiji_Governance/identity/wuchang_association_legal_profile_2026-05-11.md`
- ` M` `Taiji_Governance/identity/wuchang_association_legal_profile_v2_2026-05-11.md`
- ` M` `Taiji_Governance/integrations/odoo_google_nonprofit_mail_bridge_manifest.json`
- ` M` `Taiji_Governance/one_time_decrypt/README.md`
- ` M` `Taiji_Governance/policies/community_association_data_authority_policy_2026-05-11.md`
- ` M` `Taiji_Governance/policies/development_efficiency_first_policy_2026-05-11.md`
- ` M` `Taiji_Governance/policies/development_no_permission_friction_policy_2026-05-11.md`
- ` M` `Taiji_Governance/policies/development_period_no_member_pii_policy_2026-05-11.md`
- ` M` `Taiji_Governance/policies/document_version_archive_policy_2026-05-11.md`
- ` M` `Taiji_Governance/policies/information_custodian_accountability_statement_2026-05-11.md`
- ` M` `Taiji_Governance/policies/member_information_sealed_vault_policy_2026-05-11.md`
- ` M` `Taiji_Governance/policies/member_information_vault_d_drive_policy_2026-05-11.md`
- ` M` `Taiji_Governance/policies/pre_activation_sanitize_rotate_policy_2026-05-11.md`
- ` M` `Taiji_Governance/progress/completion_dashboard_blocks_2026-05-11.md`
- ` M` `Taiji_Governance/progress/document_archive_mode_update_2026-05-11.md`
- ` M` `Taiji_Governance/progress/progress.md`
- ` M` `Taiji_Governance/progress/taiji_hub_architecture_completion_dashboard_v2026-05-11.md`
- ` M` `Taiji_Governance/red_blue_exchange/README.md`
- ` M` `Taiji_Governance/rescue_snapshots/README.md`
- ` M` `Taiji_Governance/rollback_points/rollback_20260512T180017+0800/ROLLBACK.sh`
- ` M` `Taiji_Governance/runtime/ai_usage/ai_usage_governance.md`
- ` M` `Taiji_Governance/runtime/ai_usage/multimodal_usage_metrics.md`
- ` M` `Taiji_Governance/runtime/ai_usage/usage_routing_policy.yaml`
- ` M` `Taiji_Governance/runtime/deadbox/deadbox_lifecycle.md`
- ` M` `Taiji_Governance/runtime/deadbox/deadbox_restore_policy.md`
- ` M` `Taiji_Governance/runtime/deadbox/deadbox_runtime.md`
- ` M` `Taiji_Governance/runtime/distributed/distributed_reconciliation.md`
- ` M` `Taiji_Governance/runtime/distributed/governance_recovery_policy.md`
- ` M` `Taiji_Governance/runtime/distributed/reconciliation_flow.md`
- ` M` `Taiji_Governance/runtime/enforcement/execution_boundary_policy.md`
- ` M` `Taiji_Governance/runtime/enforcement/governance_interceptor.md`
- ` M` `Taiji_Governance/runtime/enforcement/runtime_enforcement.md`
- ` M` `Taiji_Governance/runtime/identity/runtime_identity_layer.md`
- ` M` `Taiji_Governance/runtime/identity/topology_trust_graph.md`
- ` M` `Taiji_Governance/runtime/identity/trust_boundary_runtime.md`
- ` M` `Taiji_Governance/runtime/multimodal/multimodal_governance_policy.md`
- ` M` `Taiji_Governance/runtime/multimodal/multimodal_runtime.md`
- ` M` `Taiji_Governance/runtime/multimodal/multimodal_tensor_flow.md`
- ` M` `Taiji_Governance/runtime/non_linguistic/non_linguistic_runtime.md`
- ` M` `Taiji_Governance/runtime/non_linguistic/tensor_state_mapping.md`
- ` M` `Taiji_Governance/runtime/non_linguistic/topology_runtime.md`
- ` M` `Taiji_Governance/runtime/packet/formal_event_flow.md`
- ` M` `Taiji_Governance/runtime/packet/formal_notation_protocol.yaml`
- ` M` `Taiji_Governance/runtime/packet/formal_tensor_state_machine.md`
- ` M` `Taiji_Governance/runtime/packet/packet_lifecycle.md`
- ` M` `Taiji_Governance/runtime/packet/packet_lineage_runtime.md`
- ` M` `Taiji_Governance/runtime/packet/reuse_index.yaml`
- ` M` `Taiji_Governance/runtime/packet/tensor_packet_schema.yaml`
- ` M` `Taiji_Governance/runtime/plaintext_free/context_restore_policy.md`
- ` M` `Taiji_Governance/runtime/plaintext_free/plaintext_free_runtime.md`
- ` M` `Taiji_Governance/runtime/plaintext_free/runtime_context_boundary.md`
- ` M` `Taiji_Governance/runtime/reconciliation/deployment_artifact_audit_record.jsonl`
- ` M` `Taiji_Governance/runtime/reconciliation/deployment_artifact_generation_report.md`
- ` M` `Taiji_Governance/runtime/reconciliation/existing_file_reconciliation_list.md`
- ` M` `Taiji_Governance/runtime/reconciliation/formal_notation_audit_record.jsonl`
- ` M` `Taiji_Governance/runtime/reconciliation/formal_notation_refactor_report.md`
- ` M` `Taiji_Governance/runtime/reconciliation/governance_gap_report.md`
- ` M` `Taiji_Governance/runtime/reconciliation/governance_runtime_topology_map.md`
- ` M` `Taiji_Governance/runtime/reconciliation/missing_file_generation_list.md`
- ` M` `Taiji_Governance/runtime/reconciliation/missing_runtime_report.md`
- ` M` `Taiji_Governance/runtime/reconciliation/replay_deadbox_risk_matrix.md`
- ` M` `Taiji_Governance/runtime/reconciliation/runtime_completion_matrix.md`
- ` M` `Taiji_Governance/runtime/reconciliation/runtime_enforcement_recommendations.md`
- ` M` `Taiji_Governance/runtime/reconciliation/runtime_trust_boundary_diagram.md`
- ` M` `Taiji_Governance/runtime/reconciliation/tensor_packet_lifecycle_diagram.md`
- ` M` `Taiji_Governance/runtime/replay/replay_index_schema.yaml`
- ` M` `Taiji_Governance/runtime/replay/replay_lifecycle.md`
- ` M` `Taiji_Governance/runtime/replay/replay_runtime.md`
- ` M` `Taiji_Governance/schemas/member_vault_unseal_event.schema.json`
- ` M` `Taiji_Governance/worklist/worklist.md`
- ` M` `Taiji_Vector_Runtime_Lite/README.md`
- ` M` `Taiji_Vector_Runtime_Lite/requirements.txt`

### `EXCLUDE_GENERATED_NOISE`

- ` M` `boot/taiji_login_readonly_check.sh.bak.20260529_074813`
- ` M` `data/voice_cache_test/test_voice.wav`
- ` M` `git_space/scripts_git_bundle_backup.sh`

### `RESTORE_DELETED_NOISE`

- ` D` `dashboard/preview.html:Zone.Identifier`

### `HUMAN_REVIEW_REQUIRED`

- ` M` `Dockerfile.ai`
- ` M` `index.html`

### `TYPECHANGE_REVIEW_REQUIRED`

- ` T` `AI_BOOTSTRAP.json`
- ` T` `AI_CONTEXT_TENSOR.mtl.json`
- ` T` `AI_CURRENT_STATE.mtl.json`
- ` T` `HUMAN_README.md`
- ` T` `SYSTEM_CURRENT_STATE.md`
- ` T` `W7TP_FIELD_ATLAS/gei_context/snapshot_outputs/latest_gei_context_snapshot.md`
- ` T` `W7TP_FIELD_ATLAS/gei_context/snapshot_outputs/latest_gei_context_snapshot.yaml`
- ` T` `W7TP_FIELD_ATLAS/runtime_status/latest_startup_state_packet.yaml`

### `UNTRACKED_REVIEW_REQUIRED`

- `??` `"172.27.16.1\357\200\2722222"`
- `??` `"dashboard/preview.html\357\200\272Zone.Identifier"`
- `??` `"taged files ===\357\200\242"`
- `??` `"taiji01\357\200\27222"`

## Next Executable Packet Suggestion

`W7TP_EXECUTABLE_PACKET | WORKTREE_REMEDIATION_BATCH_REVIEW_AND_STAGE`

Suggested first packet scope: review `TYPECHANGE_REVIEW_REQUIRED`, `UNTRACKED_REVIEW_REQUIRED`, `HUMAN_REVIEW_REQUIRED`, and generated-noise paths before staging any runtime candidate. The production copy-set manifest remains blocked until the worktree is clean.

## Safe To Proceed To Staged Batch Commit Packet

`true`, but only for a separately approved, category-scoped staging packet. This plan is not authorization to mutate the current drift.
