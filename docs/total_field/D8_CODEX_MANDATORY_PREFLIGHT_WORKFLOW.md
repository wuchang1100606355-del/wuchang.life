# D8 Codex Mandatory Preflight Workflow

Every Codex task must run mandatory preflight before formal work because D8 work is a databaseized, evidence-first workflow. A task may only proceed after the local guard compares the requested scope against quarantined possible alerts and creates a task capsule.

task input -> preflight -> task capsule -> sandbox, stop, human review, or block -> result seal -> redteam writeback when needed.

## Commands

```bash
tools/d8_codex_mandatory_workflow.sh doctor
tools/d8_codex_mandatory_workflow.sh start --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true}' --allowed-paths-json '["runtime/d8_db/reports/**"]' --forbidden-paths-json '["AGENTS.md","addons/**",".env*"]' --expected-output "status report"
tools/d8_codex_mandatory_workflow.sh finalize --task-name SAFE_TOTAL_FIELD_STATUS_READ --task-state PASS --result-summary "Completed"
tools/d8_codex_mandatory_workflow.sh validate
```

`start` runs preflight and bootstrap, then writes a mandatory task capsule. It does not perform the task body.

`finalize` reads the capsule, writes a result seal, and writes WARN, HOLD, BLOCK, or FAIL outcomes back to redteam quarantine.

`validate` checks recent capsules, permissions, writeback guard flags, and redteam isolation.

`doctor` checks tool availability, local D8 DB reachability, possible alerts, guard evaluations, redteam events, policy presence, and pollution guard validity.

PASS and INFO may continue. WARN is sandbox only and cannot land without explicit human release. HOLD and BLOCK must stop immediately. FAIL, WARN, HOLD, and BLOCK must be written back.

Redteam data is never executable and must remain `redteam_only`; it must not enter the main line or `d8_safe_memory`.

All writeback artifacts must stay `executable=false`, `quarantine=true`, `retrieval_scope=redteam_only`, `pollution_guard=true`, `reverse_index_only=true`, and `promotion_status=candidate`.

No secret read, no production DB write, no deploy, no restart, and no modification of `AGENTS.md`, Odoo, or LINE login files.
