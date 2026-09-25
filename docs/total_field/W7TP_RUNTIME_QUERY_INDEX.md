# W7TP Runtime Query Index

## Purpose

`tools/w7tp_runtime_query_indexer.py` builds a local SQLite query index for W7TP runtime artifacts. The SQLite file is a convenience index only. It is not the authoritative database, not the Odoo database, and not an execution authority.

Authoritative evidence remains in append-only runtime artifacts such as JSON, JSONL, MANIFEST, SHA256, dead-letter records, evidence seals, packets, and verifier outputs. The index stores only path, hash, type, status, references, and safe summary fields so reviewers can search quickly.

## Authority Boundary

The index is rebuildable and deletable. If the SQLite DB is removed, it can be recreated from the original artifacts. A query result must never become `execution_allowed=true`; only the verifier and discrete-state core can make authoritative decisions.

Odoo is only a UI / ERP / POS / review entry point for safe fields such as `runtime_ref`, `packet_hash`, `decision`, `status`, and `artifact_link`. Odoo is not an authority for W7TP verifier decisions, identity decisions, payment capture, production deployment, or runtime execution.

## Write Boundary

The indexer defaults to dry-run mode. It does not write SQLite records unless `--write-index` is explicitly provided. `--rebuild` only has effect together with `--write-index`.

Runtime source artifacts are not modified. The indexer may write a scan report when `--report-json` is provided, and it may write the SQLite index only under the explicit `--write-index` gate.

## Sensitive Material Boundary

The index must not index sensitive materials:

- secrets, tokens, API keys, client secrets, router passwords, or private key blocks
- member plaintext or direct identity-card style records
- raw audio or binary audio content
- `WHY_IT_RUNS`
- full lookup tables
- private model weights

When a hard risk is detected, the index may record the source path, SHA256, artifact type, and redacted scan metadata only. It must not persist the matched raw value.

## HOLD Conditions

- `HOLD_SECRET_INDEXED`: a secret-like value, token, password, router password, or private key block was detected.
- `HOLD_MEMBER_PLAINTEXT_INDEXED`: member plaintext or direct identity data was detected.
- `HOLD_RAW_AUDIO_INDEXED`: raw audio content or binary audio material was detected.
- `HOLD_DB_BECAME_AUTHORITY`: SQLite output was used or represented as an authority decision, or as an automatic path to `execution_allowed=true`.

These conditions require review. They do not grant execution.

## Query Modes

Supported queries:

- `--query run_id --value <RUN_ID>`
- `--query sha256 --value <SHA256>`
- `--query packet_hash --value <PACKET_HASH>`
- `--query claim_no --value <CLAIM_NO>`
- `--query gate --value PASS|HOLD|FAIL`

All query responses are JSON and include `execution_allowed=false`.

