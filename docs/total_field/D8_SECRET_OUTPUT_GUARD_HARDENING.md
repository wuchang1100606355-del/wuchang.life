# D8 Secret Output Guard Hardening

This guard applies to reports, seals, logs, terminal output summaries, and runtime artifacts created by Codex workflows.

## Rules

1. Do not output env, config, password, token, private key, API key, or database URI values into reports or seals.
2. Reports may record only secret type, hash prefix, file path, count, and containment status.
3. Any `SECRET_VALUE_EXPOSED=TRUE` result is a BLOCK governance event.
4. A technical PASS must not override a governance FAIL.
5. Odoo runtime reload workflows that need config must use non-printing container commands and must not print config.
6. `docker inspect`, environment dumps, process-argument dumps, and config-reading commands require redteam review before use.
7. Sanitized PASS/HOLD reporting is allowed only after containment scan, quarantine when applicable, sanitized copies, and redteam writeback.

## Safe Output Shape

- `secret_type`
- `sha256_prefix`
- `file_path`
- `count`
- `sanitized_path`
- `quarantined_path`
- `rotation_review_required`

## Forbidden Output Shape

- Raw password values.
- Raw token values.
- Raw private key blocks.
- Raw database URIs containing credentials.
- Full config or environment dumps.
