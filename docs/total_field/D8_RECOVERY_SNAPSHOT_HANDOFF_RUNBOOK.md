# D8 Recovery Snapshot Handoff Runbook

Current state: D8 Phase 1 through Phase 8 local databaseized agent workflow is available.

Start console:

```bash
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh doctor
```

Preflight:

```bash
tools/d8_total_field_console.sh preflight --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true}'
```

Mandatory workflow:

```bash
tools/d8_codex_mandatory_workflow.sh doctor
tools/d8_codex_mandatory_workflow.sh start --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true}' --allowed-paths-json '["runtime/d8_db/reports/**"]' --forbidden-paths-json '["AGENTS.md","addons/**",".env*"]' --expected-output "status report"
```

Writeback:

```bash
tools/d8_redteam_writeback.py --run-id HANDOFF --event-type HANDOFF_NOTE --alert-level INFO --title "Handoff" --summary "Non-executable handoff evidence"
```

Queries:

```bash
tools/d8_total_field_console.sh alerts
tools/d8_total_field_console.sh redteam
tools/d8_total_field_console.sh evals
```

Backup verification:

```bash
tools/d8_total_field_recovery_snapshot.sh verify-backup
```

Create a fresh non-production backup and handoff package:

```bash
tools/d8_total_field_recovery_snapshot.sh snapshot
```

Run recovery doctor:

```bash
tools/d8_total_field_recovery_snapshot.sh doctor
```

Never restore over `taiji_d8` during handoff verification. Use `pg_restore --list` first and restore only into a separate explicitly approved test database.

Safety flags: no secret read, no production DB write, no service restart, no deploy, no external API, no embedding.

Forbidden: do not modify `AGENTS.md`, Odoo addons, LINE login, compose files, or `.env*`.
