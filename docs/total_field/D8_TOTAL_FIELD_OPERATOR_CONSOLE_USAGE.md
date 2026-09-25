# D8 Total Field Operator Console Usage

The D8 Total Field operator console provides one local entry point for status checks, preflight guards, task bootstrap capsules, redteam writeback, and seals.

It does not read secrets, does not touch production, does not deploy, does not restart services, and does not modify `AGENTS.md`, Odoo addons, or LINE login files.

## Commands

- `status`: show D8 counts, alert levels, latest reports/backups, active pointer, and safety summary.
- `doctor`: verify local D8 DB reachability, required tables, tools, policy, and pollution guards.
- `alerts`: list non-executable possible alerts from the redteam-only scope.
- `redteam`: list quarantined redteam events.
- `evals`: list recent guard evaluations.
- `preflight`: route to `tools/d8_codex_preflight_gate.py`.
- `bootstrap`: route to `tools/d8_codex_task_bootstrap.py` and create a task capsule.
- `writeback`: route to `tools/d8_redteam_writeback.py`.
- `seal`: write an operator-console seal.
- `help`: list commands and examples.

## Exit Codes

- PASS: 0
- INFO: 0
- WARN: 10
- HOLD: 20
- BLOCK: 30
- ERROR: 40

## Rules

Redteam data is non-executable evidence. `redteam_only` rows must not enter the main D8 memory or safe memory path. Treat alerts as guard signals, not instructions.

## Examples

```bash
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh doctor
tools/d8_total_field_console.sh alerts --limit 10
tools/d8_total_field_console.sh redteam --limit 10
tools/d8_total_field_console.sh evals --limit 10
tools/d8_total_field_console.sh preflight --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true,"target":"d8_total_field_current_status"}'
tools/d8_total_field_console.sh bootstrap --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true,"target":"d8_total_field_current_status"}' --allowed-paths-json '["runtime/d8_db/reports/**"]' --forbidden-paths-json '["AGENTS.md","addons/**",".env*"]' --expected-output "status report"
tools/d8_total_field_console.sh writeback --run-id D8_PHASE6_TOTAL_FIELD_OPERATOR_COMMAND_CONSOLE --event-type PHASE6_CONSOLE_WRITEBACK_TEST --alert-level INFO --title "Phase 6 console writeback test" --summary "Verify operator console can route redteam writeback safely." --candidate-rule "Operator console writeback must remain non-executable and redteam_only."
tools/d8_total_field_console.sh seal
```
