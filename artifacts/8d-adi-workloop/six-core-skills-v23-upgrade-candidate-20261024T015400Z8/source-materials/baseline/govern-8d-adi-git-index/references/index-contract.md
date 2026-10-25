# W7TP 8D Git sidecar index contract

## Purpose

The index stores the smallest sufficient reconstruction contract and governed coordinate set. It is neither the Git object nor a complete backup by itself.

Use schema version `w7tp-8d-git-index/1.0` and require:

```json
{
  "schema_version": "w7tp-8d-git-index/1.0",
  "packet_id": "opaque-id",
  "packet_decision_index": "integer-decision-reference",
  "identity_root_ref": "opaque-identity-reference",
  "seat_binding_ref": "opaque-seat-reference",
  "receiver": {"id": "receiver-id", "version": "1.0.0"},
  "event": {
    "logical_time": 1,
    "prev_event_hash": null,
    "event_hash": "64 lowercase hex",
    "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_EVENT_HASH_V1",
    "nonce": "opaque-single-use-value",
    "replay_guard_ref": "opaque-replay-registry-reference",
    "expiry": "canonical UTC timestamp YYYY-MM-DDTHH:MM:SSZ"
  },
  "D1": {"intent_ref": "opaque-ref", "operation": "LOOKUP"},
  "D2": {
    "repo_namespace": "opaque-repository-id",
    "object_format": "sha1",
    "object_type": "blob",
    "expected_size": 12,
    "expected_git_oid": "40 or 64 lowercase hex",
    "acceptance": "EXACT_BYTES"
  },
  "D3": {
    "base_commit_oid": "40 or 64 lowercase hex",
    "base_tree_oid": "40 or 64 lowercase hex",
    "path_bytes_b64": "base64-path-bytes",
    "file_mode": "100644",
    "lineage_event_ref": "opaque-ref"
  },
  "D4": {
    "source_object_oids": ["40 or 64 lowercase hex"],
    "source_manifest_sha256": "64 lowercase hex",
    "reconstruction_receipt_ref": null
  },
  "D5": {
    "policy": "READ_ONLY_LOOKUP",
    "abort_conditions": ["MISSING_LOOKUP_CLOSURE"]
  },
  "D6": {
    "rule_refs": [{"ref": "opaque-rule", "sha256": "64 lowercase hex"}],
    "lookup_closure": [{"ref": "opaque-base", "sha256": "64 lowercase hex"}],
    "acceptance": "EXACT_BYTES",
    "verification_instruction": "GIT_NATIVE_OID_TYPE_SIZE_AND_CONNECTIVITY"
  },
  "D7": {
    "missing_prerequisite": "QUARANTINE",
    "max_reconstruction_depth": 16,
    "max_output_bytes": 1048576
  },
  "D8": {
    "authority": "CANDIDATE_ONLY",
    "allowed_ref_prefix": "refs/adi/candidates/",
    "canonical_write": false,
    "promotion_receipt_required": true
  }
}
```

## Exact and equivalent acceptance

- `EXACT_BYTES`: required when the result must retain an existing Git OID. The expected OID, object type, size, object-format namespace, rules, and complete lookup closure must be fixed.
- `EQUIVALENT_STATE`: allowed only for a newly materialized candidate object/tree/commit. It must not carry an existing expected OID as if identity were preserved.

The packet-level decision index and system-level lineage index remain separate. Any optional continuous numeric data is non-authoritative candidate evidence and requires its own declared numeric contract; it cannot establish object identity, lineage, or D8 authority.

Historical index events and receipts are append-only. A cursor or cache is a disposable projection, never the authority source.

`event_hash` is SHA-256 over canonical UTF-8 JSON with sorted keys, compact separators, finite JSON values, and only `event.event_hash` removed. CLI input bytes must equal that canonical representation plus one trailing newline; duplicate keys, non-JSON constants, unknown fields at any D1-D8/receiver/event boundary, and noncanonical timestamps are rejected. The local validator verifies that hash and expiry. `replay_guard_ref`, identity, Seat activity, prior-event existence, and Receiver authority are external prerequisites that the declared Receiver must resolve; a local packet PASS never proves those authority checks.

## Deferred-push routing boundary

An incomplete delivery uses the separate closed `w7tp-deferred-git-push-obligation/1.2` contract. E2 may report an acknowledged route only after root-issued `w7tp-e2-executor-queue-trust-config/1.1` pins a non-writable root-owned parent, one exact non-root queue owner, one distinct non-root/capability-free validator UID, and one reader GID; every queue directory/file fd must have the pinned owner/GID and `0750`/`0440` mode. That validator loads the immutable executor request, initial `ENQUEUED` event, and independent E2 obligation ACK through the descriptor tree, and the parent/child identities still match after the read. Caller-provided queue strings and containment claims are not evidence. Legacy obligation `/1.0` and `/1.1` remain read-only migration HOLD.

That acknowledgement records responsibility; it does not activate E4. Single-ref fast-forward execution, exact remote-OID closure, and current terminal authoritative recheck remain exclusively routed to `$complete-deferred-git-push`.
