# Execution receipt contract

Required receipt fields:

- `execution_id`
- `request_ref`
- `target`
- `exact_effect`
- `started_at`
- `ended_at`
- `outcome`
- `evidence_refs`
- `artifact_hashes`
- `authority_ref`
- `previous_receipt_hash`

Generated fields:

- `receipt_state=W7TP_EXECUTION_EVIDENCE`
- `receipt_sha256`
- `authority_created=false`
- `canonical_changed=false` unless the supplied execution evidence explicitly says the separately authorized canonical operation actually occurred

An appended JSONL ledger is append-oriented evidence only. The script does not make the filesystem tamper-proof.
