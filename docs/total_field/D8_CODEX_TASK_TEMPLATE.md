# D8 Codex Task Template

Every Codex task in the Total Field flow should be expressed with this fixed structure before work begins.

## TASK_NAME

Stable task identifier.

## MODE

One of `sandbox`, `land`, `production`, or `review`.

## TASK_SCOPE_JSON

JSON object passed to the D8 preflight gate.

## ALLOWED_PATHS

Explicit path list or glob list for the task.

## FORBIDDEN_PATHS

Files and directories that must not be touched.

## SAFETY_FLAGS

Required flags include `SECRET_READ=false`, `PRODUCTION_DB_WRITE=false`, `SERVICE_RESTART=false`, `DEPLOY=false`, `EXTERNAL_API_CALL=false`, and `EMBEDDING_GENERATED=false`.

## PREFLIGHT_REQUIRED

Run `tools/d8_codex_task_bootstrap.sh` before task execution.

## EXPECTED_OUTPUT

The exact reports, exports, seals, or terminal fields expected at completion.

## VALIDATION_PLAN

Concrete checks that prove the task passed.

## REDTEAM_WRITEBACK_RULE

Any `FAIL`, `HOLD`, `WARN`, `BLOCK`, unexpected diff, forbidden path, or policy ambiguity must be written back to the redteam quarantine field with:

- `executable=false`
- `quarantine=true`
- `retrieval_scope=redteam_only`
- `pollution_guard=true`
- `reverse_index_only=true`
- `promotion_status=candidate`

## FINAL_REPORT

Path to the task final report.

## SEAL

Path to the task seal.

## Decision Rules

- PASS: may enter sandbox and may land if the task permits.
- INFO: may enter sandbox and may land, with the advisory recorded.
- WARN: sandbox only; landing requires `explicit_human_release=true`.
- HOLD: stop and wait for human review.
- BLOCK: stop and do not continue.
