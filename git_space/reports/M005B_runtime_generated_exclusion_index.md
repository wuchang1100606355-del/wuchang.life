# M005B Runtime Generated / State Exclusion Index

Purpose:
Record runtime/generated/state directories excluded from Git baseline.

Excluded:
- runtime/archive/
- runtime/build/
- runtime/checkpoints/
- runtime/consensus/
- runtime/memory/conversations/
- runtime/memory/*.json
- runtime/memory_bus/
- runtime/metrics/
- runtime/mock/
- runtime/outbox/
- runtime/state/
- runtime/cache/
- runtime/ledger/
- runtime/memos/

Reason:
- These are generated state, queues, logs, mock payloads, copied build artifacts, or runtime outputs.
- They may contain timestamps, session-like identifiers, operational traces, or duplicate code.
- They should be preserved by bundle/evidence process only after redaction, not tracked as source baseline.

Git rule:
- Source code and governance files go into Git.
- Runtime outputs go into evidence packs or D: removable cold backup after redaction.
- Do not use git add . .
