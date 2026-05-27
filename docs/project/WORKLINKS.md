# Worklinks

Scope: Wuchang Smart Cloud / XiaoJ / W7TP mainline work entrypoints

- Generated: `2026-05-27T02:27:56.299129+00:00`
- Source: `/home/taiji_admin/Taiji_Hub/docs/project/PROJECT_CONTROL_BOARD.md`
- Rule: copy one block at a time; do not run unrelated task blocks together.

## Global Safe Entry

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git --no-pager log --oneline -5
git diff --cached --name-only
git diff --name-only
```

## Mainline Worklinks

### M01｜EAMTP-7D internal intent-state language

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Latest Commit: `244cea1 Add EAMTP-7D internal intent-state language`
- Next: Keep as base packet language; extend only through compatible schemas.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md
code schemas/eamtp_7d_packet.schema.json
code runtime/router/eamtp_7d_translator.py
code runtime/dead_letter/eamtp_policy_gate.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/eamtp_7d_translator.py --summary 'worklink smoke low risk' --intent-type ask --entry local --source-field local_ops --target-field router | python3 runtime/dead_letter/eamtp_policy_gate.py
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md \
  schemas/eamtp_7d_packet.schema.json \
  runtime/router/eamtp_7d_translator.py \
  runtime/dead_letter/eamtp_policy_gate.py
```

### M02｜Router Guard Dry-Run + Merlin physical boundary

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Latest Commit: `d4df60c Add EAMTP router guard dry-run and Merlin router boundary`
- Next: Expose dry-run route only after gateway adapter review.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/EAMTP_ROUTER_GUARD_DRYRUN.md
code docs/governance/W7TP_ROUTER_FIELD_MERLIN_BOUNDARY.md
code runtime/router/eamtp_router_guard_dryrun.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/eamtp_router_guard_dryrun.py --summary 'worklink router guard dry-run smoke' --intent-type ask --entry local --source-field local_ops --target-field router
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/EAMTP_ROUTER_GUARD_DRYRUN.md \
  docs/governance/W7TP_ROUTER_FIELD_MERLIN_BOUNDARY.md \
  runtime/router/eamtp_router_guard_dryrun.py
```

### M03｜Merlin Intent Driver plan-only

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `399724f Add Merlin intent driver plan-only governance`
- Next: Add more intent classes only as plan-only tickets.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/MERLIN_INTENT_DRIVER_GOVERNANCE.md
code runtime/router/merlin_intent_driver.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/merlin_intent_driver.py --intent observe_status --note 'worklink smoke only'
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_INTENT_DRIVER_GOVERNANCE.md \
  runtime/router/merlin_intent_driver.py
```

### M04｜Merlin Apply Queue human-review

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `4184356 Add Merlin apply queue human-review governance`
- Next: Maintain ticket-only boundary; no router login.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/MERLIN_APPLY_QUEUE_GOVERNANCE.md
code runtime/router/merlin_apply_queue.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/merlin_apply_queue.py --intent observe_status --note 'worklink smoke only'
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_APPLY_QUEUE_GOVERNANCE.md \
  runtime/router/merlin_apply_queue.py
```

### M05｜Merlin Approval Gate record-only

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `a914329 Add Merlin approval gate record-only governance`
- Next: Use exact approval phrase; still no automatic execution.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/MERLIN_APPROVAL_GATE_GOVERNANCE.md
code runtime/router/merlin_approval_gate.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/merlin_approval_gate.py --latest-pending --phrase 'approve' || true
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_APPROVAL_GATE_GOVERNANCE.md \
  runtime/router/merlin_approval_gate.py
```

### M06｜Merlin Human Execution Checklist

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `f9f4e51 Add Merlin human execution checklist generator`
- Next: Generate manual UI checklist for approved records only.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/MERLIN_HUMAN_EXECUTION_CHECKLIST_GOVERNANCE.md
code runtime/router/merlin_human_execution_checklist.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/merlin_human_execution_checklist.py --latest-approved || true
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_HUMAN_EXECUTION_CHECKLIST_GOVERNANCE.md \
  runtime/router/merlin_human_execution_checklist.py
```

### M07｜Merlin Execution Result Recorder

- Status: `done_clean`
- Done: `100%`
- Risk: `medium`
- Latest Commit: `47fe151 Add Merlin execution result recorder`
- Next: Record completed / abandoned / failed / observation_only results.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/MERLIN_EXECUTION_RESULT_RECORDER.md
code runtime/router/merlin_execution_result_recorder.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/merlin_execution_result_recorder.py --checklist latest --status observation_only --note 'worklink smoke only' || true
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_EXECUTION_RESULT_RECORDER.md \
  runtime/router/merlin_execution_result_recorder.py
```

### M08｜Merlin redacted full config inventory

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `491b8ab Add Merlin router redacted config inventory spec`
- Next: Keep local inventory untracked; validate before W7TP use.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md
code configs/merlin/router_inventory_redacted.template.json
code configs/merlin/README.md
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 tools/merlin_inventory_validator.py --file configs/merlin/router_inventory_redacted.local.json || true
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md \
  configs/merlin/router_inventory_redacted.template.json \
  configs/merlin/README.md
```

### M09｜Merlin redacted inventory validator + EAMTP adapter

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `fa54950 Add Merlin redacted inventory validator`
- Next: Convert only redacted local inventory into pending_review EAMTP.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/MERLIN_REDACTED_INVENTORY_VALIDATOR.md
code tools/merlin_inventory_validator.py
code docs/governance/MERLIN_INVENTORY_EAMTP_ADAPTER.md
code tools/merlin_inventory_to_eamtp.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 tools/merlin_inventory_to_eamtp.py --file configs/merlin/router_inventory_redacted.local.json || true
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/MERLIN_REDACTED_INVENTORY_VALIDATOR.md \
  tools/merlin_inventory_validator.py \
  docs/governance/MERLIN_INVENTORY_EAMTP_ADAPTER.md \
  tools/merlin_inventory_to_eamtp.py
```

### M10｜W7TP HA Mesh plan-only governance

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `b899952 Add W7TP HA mesh plan-only governance`
- Next: Analyze legacy HA scripts; never execute sudo/SSH/rsync/crontab/iptables.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/W7TP_HA_MESH_PLAN_ONLY.md
code docs/governance/HA_MESH_LEGACY_SCRIPT_ANALYZER.md
code configs/w7tp/ha_mesh_inventory.template.json
code schemas/w7tp_ha_mesh_inventory.schema.json
code tools/ha_mesh_script_analyzer.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 tools/ha_mesh_script_analyzer.py --file tools/ha_mesh_script_analyzer.py --dry-run || true
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/W7TP_HA_MESH_PLAN_ONLY.md \
  docs/governance/HA_MESH_LEGACY_SCRIPT_ANALYZER.md \
  configs/w7tp/ha_mesh_inventory.template.json \
  schemas/w7tp_ha_mesh_inventory.schema.json \
  tools/ha_mesh_script_analyzer.py
```

### M11｜W7TP Causal Ledger plan-only layer

- Status: `done_clean`
- Done: `100%`
- Risk: `high`
- Latest Commit: `2338ad1 Add W7TP causal ledger plan-only layer`
- Next: Use causal packets for audit links; no production finance or Odoo ledger writes.

#### Open files in VS Code

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
code docs/governance/W7TP_CAUSAL_LEDGER_PLAN_ONLY.md
code schemas/w7tp_causal_event_packet.schema.json
code runtime/router/w7tp_causal_event_builder.py
code tools/causal_ledger_text_analyzer.py
```

#### Smoke test

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
python3 runtime/router/w7tp_causal_event_builder.py --summary 'worklink causal ledger smoke metadata only'
```

#### Git preview for this item

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git status --short -- \
  docs/governance/W7TP_CAUSAL_LEDGER_PLAN_ONLY.md \
  schemas/w7tp_causal_event_packet.schema.json \
  runtime/router/w7tp_causal_event_builder.py \
  tools/causal_ledger_text_analyzer.py
```

## Commit Safety

```bash
cd /home/taiji_admin/Taiji_Hub || exit 1
git diff --cached --stat
git diff --cached --name-only
git --no-pager log --oneline -10
```

Do not use `git add .` or `git add -A`.
