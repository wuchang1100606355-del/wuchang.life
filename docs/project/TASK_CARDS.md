# Task Cards

- Generated: `2026-05-27T04:39:04.806481+00:00`
- Count: `21`

## Rules

```text
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。
```

## TASK_ID: M01_eamtp_7d_internal_intent_state_language

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Commit: `244cea1 Add EAMTP-7D internal intent-state language`
- Next: Keep as base packet language; extend only through compatible schemas.

### Allowed files

- docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md
- schemas/eamtp_7d_packet.schema.json
- runtime/router/eamtp_7d_translator.py
- runtime/dead_letter/eamtp_policy_gate.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md \
  schemas/eamtp_7d_packet.schema.json \
  runtime/router/eamtp_7d_translator.py \
  runtime/dead_letter/eamtp_policy_gate.py
```

### Agent prompt

```text
TASK_ID: M01_eamtp_7d_internal_intent_state_language

目標：
EAMTP-7D internal intent-state language

允許讀取 / 修改：
- docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md
- schemas/eamtp_7d_packet.schema.json
- runtime/router/eamtp_7d_translator.py
- runtime/dead_letter/eamtp_policy_gate.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M02_router_guard_dry_run_merlin_physical_boundary

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Commit: `d4df60c Add EAMTP router guard dry-run and Merlin router boundary`
- Next: Expose dry-run route only after gateway adapter review.

### Allowed files

- docs/governance/EAMTP_ROUTER_GUARD_DRYRUN.md
- docs/governance/W7TP_ROUTER_FIELD_MERLIN_BOUNDARY.md
- runtime/router/eamtp_router_guard_dryrun.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/EAMTP_ROUTER_GUARD_DRYRUN.md \
  docs/governance/W7TP_ROUTER_FIELD_MERLIN_BOUNDARY.md \
  runtime/router/eamtp_router_guard_dryrun.py
```

### Agent prompt

```text
TASK_ID: M02_router_guard_dry_run_merlin_physical_boundary

目標：
Router Guard Dry-Run + Merlin physical boundary

允許讀取 / 修改：
- docs/governance/EAMTP_ROUTER_GUARD_DRYRUN.md
- docs/governance/W7TP_ROUTER_FIELD_MERLIN_BOUNDARY.md
- runtime/router/eamtp_router_guard_dryrun.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M03_merlin_intent_driver_plan_only

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `399724f Add Merlin intent driver plan-only governance`
- Next: Add more intent classes only as plan-only tickets.

### Allowed files

- docs/governance/MERLIN_INTENT_DRIVER_GOVERNANCE.md
- runtime/router/merlin_intent_driver.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_INTENT_DRIVER_GOVERNANCE.md \
  runtime/router/merlin_intent_driver.py
```

### Agent prompt

```text
TASK_ID: M03_merlin_intent_driver_plan_only

目標：
Merlin Intent Driver plan-only

允許讀取 / 修改：
- docs/governance/MERLIN_INTENT_DRIVER_GOVERNANCE.md
- runtime/router/merlin_intent_driver.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M04_merlin_apply_queue_human_review

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `4184356 Add Merlin apply queue human-review governance`
- Next: Maintain ticket-only boundary; no router login.

### Allowed files

- docs/governance/MERLIN_APPLY_QUEUE_GOVERNANCE.md
- runtime/router/merlin_apply_queue.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_APPLY_QUEUE_GOVERNANCE.md \
  runtime/router/merlin_apply_queue.py
```

### Agent prompt

```text
TASK_ID: M04_merlin_apply_queue_human_review

目標：
Merlin Apply Queue human-review

允許讀取 / 修改：
- docs/governance/MERLIN_APPLY_QUEUE_GOVERNANCE.md
- runtime/router/merlin_apply_queue.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M05_merlin_approval_gate_record_only

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `a914329 Add Merlin approval gate record-only governance`
- Next: Use exact approval phrase; still no automatic execution.

### Allowed files

- docs/governance/MERLIN_APPROVAL_GATE_GOVERNANCE.md
- runtime/router/merlin_approval_gate.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_APPROVAL_GATE_GOVERNANCE.md \
  runtime/router/merlin_approval_gate.py
```

### Agent prompt

```text
TASK_ID: M05_merlin_approval_gate_record_only

目標：
Merlin Approval Gate record-only

允許讀取 / 修改：
- docs/governance/MERLIN_APPROVAL_GATE_GOVERNANCE.md
- runtime/router/merlin_approval_gate.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M06_merlin_human_execution_checklist

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `f9f4e51 Add Merlin human execution checklist generator`
- Next: Generate manual UI checklist for approved records only.

### Allowed files

- docs/governance/MERLIN_HUMAN_EXECUTION_CHECKLIST_GOVERNANCE.md
- runtime/router/merlin_human_execution_checklist.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_HUMAN_EXECUTION_CHECKLIST_GOVERNANCE.md \
  runtime/router/merlin_human_execution_checklist.py
```

### Agent prompt

```text
TASK_ID: M06_merlin_human_execution_checklist

目標：
Merlin Human Execution Checklist

允許讀取 / 修改：
- docs/governance/MERLIN_HUMAN_EXECUTION_CHECKLIST_GOVERNANCE.md
- runtime/router/merlin_human_execution_checklist.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M07_merlin_execution_result_recorder

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Commit: `47fe151 Add Merlin execution result recorder`
- Next: Record completed / abandoned / failed / observation_only results.

### Allowed files

- docs/governance/MERLIN_EXECUTION_RESULT_RECORDER.md
- runtime/router/merlin_execution_result_recorder.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_EXECUTION_RESULT_RECORDER.md \
  runtime/router/merlin_execution_result_recorder.py
```

### Agent prompt

```text
TASK_ID: M07_merlin_execution_result_recorder

目標：
Merlin Execution Result Recorder

允許讀取 / 修改：
- docs/governance/MERLIN_EXECUTION_RESULT_RECORDER.md
- runtime/router/merlin_execution_result_recorder.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M08_merlin_redacted_full_config_inventory

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `491b8ab Add Merlin router redacted config inventory spec`
- Next: Keep local inventory untracked; validate before W7TP use.

### Allowed files

- docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md
- configs/merlin/router_inventory_redacted.template.json
- configs/merlin/README.md

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md \
  configs/merlin/router_inventory_redacted.template.json \
  configs/merlin/README.md
```

### Agent prompt

```text
TASK_ID: M08_merlin_redacted_full_config_inventory

目標：
Merlin redacted full config inventory

允許讀取 / 修改：
- docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md
- configs/merlin/router_inventory_redacted.template.json
- configs/merlin/README.md

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M09_merlin_redacted_inventory_validator_eamtp_adapter

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `fa54950 Add Merlin redacted inventory validator`
- Next: Convert only redacted local inventory into pending_review EAMTP.

### Allowed files

- docs/governance/MERLIN_REDACTED_INVENTORY_VALIDATOR.md
- tools/merlin_inventory_validator.py
- docs/governance/MERLIN_INVENTORY_EAMTP_ADAPTER.md
- tools/merlin_inventory_to_eamtp.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_REDACTED_INVENTORY_VALIDATOR.md \
  tools/merlin_inventory_validator.py \
  docs/governance/MERLIN_INVENTORY_EAMTP_ADAPTER.md \
  tools/merlin_inventory_to_eamtp.py
```

### Agent prompt

```text
TASK_ID: M09_merlin_redacted_inventory_validator_eamtp_adapter

目標：
Merlin redacted inventory validator + EAMTP adapter

允許讀取 / 修改：
- docs/governance/MERLIN_REDACTED_INVENTORY_VALIDATOR.md
- tools/merlin_inventory_validator.py
- docs/governance/MERLIN_INVENTORY_EAMTP_ADAPTER.md
- tools/merlin_inventory_to_eamtp.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M10_w7tp_ha_mesh_plan_only_governance

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `b899952 Add W7TP HA mesh plan-only governance`
- Next: Analyze legacy HA scripts; never execute sudo/SSH/rsync/crontab/iptables.

### Allowed files

- docs/governance/W7TP_HA_MESH_PLAN_ONLY.md
- docs/governance/HA_MESH_LEGACY_SCRIPT_ANALYZER.md
- configs/w7tp/ha_mesh_inventory.template.json
- schemas/w7tp_ha_mesh_inventory.schema.json
- tools/ha_mesh_script_analyzer.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/W7TP_HA_MESH_PLAN_ONLY.md \
  docs/governance/HA_MESH_LEGACY_SCRIPT_ANALYZER.md \
  configs/w7tp/ha_mesh_inventory.template.json \
  schemas/w7tp_ha_mesh_inventory.schema.json \
  tools/ha_mesh_script_analyzer.py
```

### Agent prompt

```text
TASK_ID: M10_w7tp_ha_mesh_plan_only_governance

目標：
W7TP HA Mesh plan-only governance

允許讀取 / 修改：
- docs/governance/W7TP_HA_MESH_PLAN_ONLY.md
- docs/governance/HA_MESH_LEGACY_SCRIPT_ANALYZER.md
- configs/w7tp/ha_mesh_inventory.template.json
- schemas/w7tp_ha_mesh_inventory.schema.json
- tools/ha_mesh_script_analyzer.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M11_w7tp_causal_ledger_plan_only_layer

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Commit: `2338ad1 Add W7TP causal ledger plan-only layer`
- Next: Use causal packets for audit links; no production finance or Odoo ledger writes.

### Allowed files

- docs/governance/W7TP_CAUSAL_LEDGER_PLAN_ONLY.md
- schemas/w7tp_causal_event_packet.schema.json
- runtime/router/w7tp_causal_event_builder.py
- tools/causal_ledger_text_analyzer.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/W7TP_CAUSAL_LEDGER_PLAN_ONLY.md \
  schemas/w7tp_causal_event_packet.schema.json \
  runtime/router/w7tp_causal_event_builder.py \
  tools/causal_ledger_text_analyzer.py
```

### Agent prompt

```text
TASK_ID: M11_w7tp_causal_ledger_plan_only_layer

目標：
W7TP Causal Ledger plan-only layer

允許讀取 / 修改：
- docs/governance/W7TP_CAUSAL_LEDGER_PLAN_ONLY.md
- schemas/w7tp_causal_event_packet.schema.json
- runtime/router/w7tp_causal_event_builder.py
- tools/causal_ledger_text_analyzer.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M12_merlin_redacted_inventory_fill_helper

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Commit: `9830277 Add Merlin redacted inventory fill helper`
- Next: Use allowlisted --set updates for local redacted inventory; never commit local.json.

### Allowed files

- tools/merlin_inventory_fill_helper.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/merlin_inventory_fill_helper.py
```

### Agent prompt

```text
TASK_ID: M12_merlin_redacted_inventory_fill_helper

目標：
Merlin redacted inventory fill helper

允許讀取 / 修改：
- tools/merlin_inventory_fill_helper.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M13_readonly_service_health_checker

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `60e656c Add readonly service health checker`
- Next: Use GET-only health summaries before deciding whether a service needs action.

### Allowed files

- tools/service_health_readonly.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/service_health_readonly.py
```

### Agent prompt

```text
TASK_ID: M13_readonly_service_health_checker

目標：
Readonly service health checker

允許讀取 / 修改：
- tools/service_health_readonly.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M14_runtime_shadow_inventory

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `5e6ff90 Add runtime shadow inventory tool`
- Next: Use inventory-only reports before any cleanup or archive decision.

### Allowed files

- tools/runtime_shadow_inventory.py
- docs/project/RUNTIME_SHADOW_INVENTORY.md

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/runtime_shadow_inventory.py \
  docs/project/RUNTIME_SHADOW_INVENTORY.md
```

### Agent prompt

```text
TASK_ID: M14_runtime_shadow_inventory

目標：
Runtime shadow inventory

允許讀取 / 修改：
- tools/runtime_shadow_inventory.py
- docs/project/RUNTIME_SHADOW_INVENTORY.md

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M15_eamtp_packet_summarizer

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `7bb86c3 Add EAMTP packet summarizer`
- Next: Use read-only packet summaries before router/gateway integration reviews.

### Allowed files

- tools/eamtp_packet_summarizer.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/eamtp_packet_summarizer.py
```

### Agent prompt

```text
TASK_ID: M15_eamtp_packet_summarizer

目標：
EAMTP packet summarizer

允許讀取 / 修改：
- tools/eamtp_packet_summarizer.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M16_w7tp_smoke_all_checker

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `657a8a6 Add W7TP smoke all checker`
- Next: Run before integration commits to verify mainline tools are still usable.

### Allowed files

- tools/w7tp_smoke_all.sh

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/w7tp_smoke_all.sh
```

### Agent prompt

```text
TASK_ID: M16_w7tp_smoke_all_checker

目標：
W7TP smoke all checker

允許讀取 / 修改：
- tools/w7tp_smoke_all.sh

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M17_safe_git_stage_allowlist_tool

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `c14a9da Add safe git stage allowlist tool`
- Next: Use before multi-agent commits to preview/stage only allowlisted canonical files.

### Allowed files

- tools/safe_git_stage.py
- docs/project/git_stage_allowlist.txt
- tests/test_safe_git_stage.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/safe_git_stage.py \
  docs/project/git_stage_allowlist.txt \
  tests/test_safe_git_stage.py
```

### Agent prompt

```text
TASK_ID: M17_safe_git_stage_allowlist_tool

目標：
Safe git stage allowlist tool

允許讀取 / 修改：
- tools/safe_git_stage.py
- docs/project/git_stage_allowlist.txt
- tests/test_safe_git_stage.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M18_project_dashboard_html_generator

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `447f6c1 Add project dashboard generator`
- Next: Open local dashboard to copy task commands and inspect mainline status.

### Allowed files

- tools/project_dashboard_generator.py
- docs/project/PROJECT_DASHBOARD.html

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/project_dashboard_generator.py \
  docs/project/PROJECT_DASHBOARD.html
```

### Agent prompt

```text
TASK_ID: M18_project_dashboard_html_generator

目標：
Project dashboard HTML generator

允許讀取 / 修改：
- tools/project_dashboard_generator.py
- docs/project/PROJECT_DASHBOARD.html

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M19_project_dashboard_launcher

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `59a2880 Add project dashboard launcher`
- Next: Use this launcher to regenerate and open the local project dashboard.

### Allowed files

- tools/open_project_dashboard.sh

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/open_project_dashboard.sh
```

### Agent prompt

```text
TASK_ID: M19_project_dashboard_launcher

目標：
Project dashboard launcher

允許讀取 / 修改：
- tools/open_project_dashboard.sh

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M20_multi_agent_task_card_generator

- Status: `done_clean`
- Done: `100%`
- Risk: `low`
- Commit: `70ab9aa Fix task cards markdown newline generation`
- Next: Use generated task cards to delegate isolated work to code agents.

### Allowed files

- tools/task_card_generator.py
- docs/project/TASK_CARDS.md

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  tools/task_card_generator.py \
  docs/project/TASK_CARDS.md
```

### Agent prompt

```text
TASK_ID: M20_multi_agent_task_card_generator

目標：
Multi-agent task card generator

允許讀取 / 修改：
- tools/task_card_generator.py
- docs/project/TASK_CARDS.md

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```

## TASK_ID: M21_container_server_offload_plan_only

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Commit: `1528c34 Add container server offload plan skeleton`
- Next: Use offload registry and linter before moving background containers to pure Linux server nodes.

### Allowed files

- docs/governance/W7TP_CONTAINER_SERVER_OFFLOAD_PLAN.md
- configs/containers/container_offload_registry.template.json
- schemas/w7tp_container_offload_registry.schema.json
- tools/container_offload_linter.py

### Git preview

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/W7TP_CONTAINER_SERVER_OFFLOAD_PLAN.md \
  configs/containers/container_offload_registry.template.json \
  schemas/w7tp_container_offload_registry.schema.json \
  tools/container_offload_linter.py
```

### Agent prompt

```text
TASK_ID: M21_container_server_offload_plan_only

目標：
Container server offload plan-only

允許讀取 / 修改：
- docs/governance/W7TP_CONTAINER_SERVER_OFFLOAD_PLAN.md
- configs/containers/container_offload_registry.template.json
- schemas/w7tp_container_offload_registry.schema.json
- tools/container_offload_linter.py

規則：
本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。

完成後只回報 created files、modified files、smoke result、git preview。
```
