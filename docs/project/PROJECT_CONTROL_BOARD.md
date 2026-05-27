# Project Control Board

Scope: Wuchang Smart Cloud / XiaoJ / W7TP mainline anchors

- Generated: `2026-05-27T02:35:30.635309+00:00`
- HEAD: `c14a9da Add safe git stage allowlist tool`
- Rule: runtime reports/proofs/queues are not canonical commit targets.

## Mainline Board

| ID | Work Item | Status | Done | Risk | Latest Commit | Canonical Files | Next Step |
|---|---|---:|---:|---|---|---|---|
| M01 | EAMTP-7D internal intent-state language | done_clean | 100% | medium | 244cea1 Add EAMTP-7D internal intent-state language | `docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md`<br>`schemas/eamtp_7d_packet.schema.json`<br>`runtime/router/eamtp_7d_translator.py`<br>`runtime/dead_letter/eamtp_policy_gate.py` | Keep as base packet language; extend only through compatible schemas. |
| M02 | Router Guard Dry-Run + Merlin physical boundary | done_clean | 100% | medium | d4df60c Add EAMTP router guard dry-run and Merlin router boundary | `docs/governance/EAMTP_ROUTER_GUARD_DRYRUN.md`<br>`docs/governance/W7TP_ROUTER_FIELD_MERLIN_BOUNDARY.md`<br>`runtime/router/eamtp_router_guard_dryrun.py` | Expose dry-run route only after gateway adapter review. |
| M03 | Merlin Intent Driver plan-only | done_clean | 100% | high | 399724f Add Merlin intent driver plan-only governance | `docs/governance/MERLIN_INTENT_DRIVER_GOVERNANCE.md`<br>`runtime/router/merlin_intent_driver.py` | Add more intent classes only as plan-only tickets. |
| M04 | Merlin Apply Queue human-review | done_clean | 100% | high | 4184356 Add Merlin apply queue human-review governance | `docs/governance/MERLIN_APPLY_QUEUE_GOVERNANCE.md`<br>`runtime/router/merlin_apply_queue.py` | Maintain ticket-only boundary; no router login. |
| M05 | Merlin Approval Gate record-only | done_clean | 100% | high | a914329 Add Merlin approval gate record-only governance | `docs/governance/MERLIN_APPROVAL_GATE_GOVERNANCE.md`<br>`runtime/router/merlin_approval_gate.py` | Use exact approval phrase; still no automatic execution. |
| M06 | Merlin Human Execution Checklist | done_clean | 100% | high | f9f4e51 Add Merlin human execution checklist generator | `docs/governance/MERLIN_HUMAN_EXECUTION_CHECKLIST_GOVERNANCE.md`<br>`runtime/router/merlin_human_execution_checklist.py` | Generate manual UI checklist for approved records only. |
| M07 | Merlin Execution Result Recorder | done_clean | 100% | medium | 47fe151 Add Merlin execution result recorder | `docs/governance/MERLIN_EXECUTION_RESULT_RECORDER.md`<br>`runtime/router/merlin_execution_result_recorder.py` | Record completed / abandoned / failed / observation_only results. |
| M08 | Merlin redacted full config inventory | done_clean | 100% | high | 491b8ab Add Merlin router redacted config inventory spec | `docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md`<br>`configs/merlin/router_inventory_redacted.template.json`<br>`configs/merlin/README.md` | Keep local inventory untracked; validate before W7TP use. |
| M09 | Merlin redacted inventory validator + EAMTP adapter | done_clean | 100% | high | fa54950 Add Merlin redacted inventory validator | `docs/governance/MERLIN_REDACTED_INVENTORY_VALIDATOR.md`<br>`tools/merlin_inventory_validator.py`<br>`docs/governance/MERLIN_INVENTORY_EAMTP_ADAPTER.md`<br>`tools/merlin_inventory_to_eamtp.py` | Convert only redacted local inventory into pending_review EAMTP. |
| M10 | W7TP HA Mesh plan-only governance | done_clean | 100% | high | b899952 Add W7TP HA mesh plan-only governance | `docs/governance/W7TP_HA_MESH_PLAN_ONLY.md`<br>`docs/governance/HA_MESH_LEGACY_SCRIPT_ANALYZER.md`<br>`configs/w7tp/ha_mesh_inventory.template.json`<br>`schemas/w7tp_ha_mesh_inventory.schema.json`<br>`tools/ha_mesh_script_analyzer.py` | Analyze legacy HA scripts; never execute sudo/SSH/rsync/crontab/iptables. |
| M11 | W7TP Causal Ledger plan-only layer | done_clean | 100% | high | 2338ad1 Add W7TP causal ledger plan-only layer | `docs/governance/W7TP_CAUSAL_LEDGER_PLAN_ONLY.md`<br>`schemas/w7tp_causal_event_packet.schema.json`<br>`runtime/router/w7tp_causal_event_builder.py`<br>`tools/causal_ledger_text_analyzer.py` | Use causal packets for audit links; no production finance or Odoo ledger writes. |
| M12 | Merlin redacted inventory fill helper | done_clean | 100% | medium | 9830277 Add Merlin redacted inventory fill helper | `tools/merlin_inventory_fill_helper.py` | Use allowlisted --set updates for local redacted inventory; never commit local.json. |
| M13 | Readonly service health checker | done_clean | 100% | low | 60e656c Add readonly service health checker | `tools/service_health_readonly.py` | Use GET-only health summaries before deciding whether a service needs action. |
| M14 | Runtime shadow inventory | done_clean | 100% | low | 5e6ff90 Add runtime shadow inventory tool | `tools/runtime_shadow_inventory.py`<br>`docs/project/RUNTIME_SHADOW_INVENTORY.md` | Use inventory-only reports before any cleanup or archive decision. |
| M15 | EAMTP packet summarizer | done_clean | 100% | low | 7bb86c3 Add EAMTP packet summarizer | `tools/eamtp_packet_summarizer.py` | Use read-only packet summaries before router/gateway integration reviews. |
| M16 | W7TP smoke all checker | done_clean | 100% | low | 657a8a6 Add W7TP smoke all checker | `tools/w7tp_smoke_all.sh` | Run before integration commits to verify mainline tools are still usable. |
| M17 | Safe git stage allowlist tool | done_clean | 100% | low | c14a9da Add safe git stage allowlist tool | `tools/safe_git_stage.py`<br>`docs/project/git_stage_allowlist.txt`<br>`tests/test_safe_git_stage.py` | Use before multi-agent commits to preview/stage only allowlisted canonical files. |

## Integration Rules

- Do not use `git add .` or `git add -A`.
- Only stage explicit canonical files for the active task.
- Do not commit `runtime/reports`, `runtime/proofs`, `runtime/merlin_*`, or local inventories.
- Router, SSH, Odoo/Postgres, service restart, and credential operations require explicit review.

## Recommended Next Work

1. Build `WORKLINKS.md` from this board.
2. Add isolated task cards for A06/A07/A08 if needed.
3. Keep mainline and side tasks separated.
