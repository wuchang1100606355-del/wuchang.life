-- W7TP state-field candidate schema v1.
-- This schema records candidate state only. It deliberately seeds no authority.

CREATE TABLE workspaces (
    workspace_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    root_ref TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE objects (
    object_id TEXT PRIMARY KEY,
    object_sha256 TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    storage_ref TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (object_id = 'sha256:' || object_sha256),
    CHECK (
        length(object_sha256) = 64
        AND object_sha256 = lower(object_sha256)
        AND object_sha256 NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE TABLE manifests (
    manifest_ref TEXT PRIMARY KEY,
    manifest_hash TEXT NOT NULL UNIQUE,
    entry_count INTEGER NOT NULL CHECK (entry_count >= 0),
    created_at TEXT NOT NULL,
    CHECK (manifest_ref = 'sha256:' || manifest_hash),
    CHECK (
        length(manifest_hash) = 64
        AND manifest_hash = lower(manifest_hash)
        AND manifest_hash NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE TABLE manifest_entry (
    manifest_ref TEXT NOT NULL,
    entry_ordinal INTEGER NOT NULL CHECK (entry_ordinal >= 0),
    logical_path TEXT NOT NULL,
    entry_kind TEXT NOT NULL CHECK (
        entry_kind IN ('FILE', 'DIRECTORY')
    ),
    mode INTEGER NOT NULL CHECK (mode BETWEEN 0 AND 65535),
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    file_sha256 TEXT,
    PRIMARY KEY (manifest_ref, entry_ordinal),
    UNIQUE (manifest_ref, logical_path),
    FOREIGN KEY (manifest_ref) REFERENCES manifests(manifest_ref),
    CHECK (
        (
            entry_kind = 'FILE'
            AND file_sha256 IS NOT NULL
            AND length(file_sha256) = 64
            AND file_sha256 = lower(file_sha256)
            AND file_sha256 NOT GLOB '*[^0-9a-f]*'
        )
        OR
        (
            entry_kind = 'DIRECTORY'
            AND size_bytes = 0
            AND file_sha256 IS NULL
        )
    )
);

CREATE TABLE manifest_entry_chunk (
    manifest_ref TEXT NOT NULL,
    entry_ordinal INTEGER NOT NULL,
    chunk_ordinal INTEGER NOT NULL CHECK (chunk_ordinal >= 0),
    object_id TEXT NOT NULL,
    byte_offset INTEGER NOT NULL CHECK (byte_offset >= 0),
    byte_length INTEGER NOT NULL CHECK (byte_length > 0),
    PRIMARY KEY (manifest_ref, entry_ordinal, chunk_ordinal),
    FOREIGN KEY (manifest_ref, entry_ordinal)
        REFERENCES manifest_entry(manifest_ref, entry_ordinal),
    FOREIGN KEY (object_id) REFERENCES objects(object_id)
);

CREATE INDEX ix_manifest_entry_chunk_object
ON manifest_entry_chunk(object_id);

CREATE TABLE resources (
    resource_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    resource_kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
);

CREATE TABLE transitions (
    transition_ref TEXT PRIMARY KEY,
    transition_hash TEXT NOT NULL UNIQUE,
    operation_id TEXT NOT NULL UNIQUE,
    resource_id TEXT NOT NULL,
    from_version_ref TEXT,
    to_version_ref TEXT NOT NULL,
    expected_generation INTEGER NOT NULL CHECK (expected_generation >= 0),
    receipt_ref TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    CHECK (transition_ref = 'sha256:' || transition_hash),
    CHECK (
        length(transition_hash) = 64
        AND transition_hash = lower(transition_hash)
        AND transition_hash NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE TABLE current_pointer (
    resource_id TEXT PRIMARY KEY,
    version_ref TEXT,
    generation INTEGER NOT NULL CHECK (generation >= 0),
    transition_ref TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    FOREIGN KEY (transition_ref) REFERENCES transitions(transition_ref)
);

CREATE TABLE artifact_bindings (
    binding_ref TEXT PRIMARY KEY,
    binding_hash TEXT NOT NULL UNIQUE,
    node_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    artifact_ref TEXT NOT NULL,
    manifest_ref TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    version TEXT NOT NULL,
    adapter_ref TEXT NOT NULL,
    binding_state TEXT NOT NULL CHECK (
        binding_state IN (
            'OBSERVED', 'CANDIDATE', 'VERIFIED', 'HOLD', 'CONFLICT'
        )
    ),
    evidence_ref TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    UNIQUE (
        node_id, workspace_id, artifact_ref, manifest_ref,
        artifact_hash, capability_id, version, adapter_ref
    ),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
    FOREIGN KEY (manifest_ref) REFERENCES manifests(manifest_ref),
    CHECK (binding_ref = 'sha256:' || binding_hash),
    CHECK (
        length(binding_hash) = 64
        AND binding_hash = lower(binding_hash)
        AND binding_hash NOT GLOB '*[^0-9a-f]*'
    ),
    CHECK (
        length(artifact_hash) = 64
        AND artifact_hash = lower(artifact_hash)
        AND artifact_hash NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE INDEX ix_artifact_binding_capability
ON artifact_bindings(capability_id, version, binding_state);

CREATE TABLE effect_operation_claims (
    idempotency_key TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL UNIQUE,
    effect_contract_ref TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    CHECK (
        length(effect_contract_ref) = 71
        AND substr(effect_contract_ref, 1, 7) = 'sha256:'
        AND substr(effect_contract_ref, 8) = lower(
            substr(effect_contract_ref, 8)
        )
        AND substr(effect_contract_ref, 8)
            NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE TABLE effect_attempt_claims (
    operation_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
    idempotency_key TEXT NOT NULL,
    effect_contract_ref TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    PRIMARY KEY (operation_id, attempt_no),
    UNIQUE (idempotency_key, attempt_no),
    FOREIGN KEY (idempotency_key)
        REFERENCES effect_operation_claims(idempotency_key),
    CHECK (
        length(effect_contract_ref) = 71
        AND substr(effect_contract_ref, 1, 7) = 'sha256:'
        AND substr(effect_contract_ref, 8) = lower(
            substr(effect_contract_ref, 8)
        )
        AND substr(effect_contract_ref, 8)
            NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE TABLE operation_journal (
    operation_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
    sequence_no INTEGER NOT NULL CHECK (sequence_no >= 0),
    effect_contract_ref TEXT NOT NULL,
    effect_contract_hash TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'RESOURCE_READY',
            'INGRESS_VERIFIED',
            'DELEGATION_VERIFIED',
            'FLOW_VERIFIED',
            'STATE_DRIFT',
            'EFFECT_PREPARED',
            'EFFECT_STARTED',
            'EFFECT_OBSERVED',
            'EFFECT_FAILED',
            'EFFECT_ACCEPTED',
            'STATE_COMMITTED'
        )
    ),
    payload_ref TEXT NOT NULL,
    previous_event_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE,
    occurred_at TEXT NOT NULL,
    PRIMARY KEY (operation_id, attempt_no, sequence_no),
    CHECK (effect_contract_ref = 'sha256:' || effect_contract_hash),
    CHECK (
        length(effect_contract_hash) = 64
        AND effect_contract_hash = lower(effect_contract_hash)
        AND effect_contract_hash NOT GLOB '*[^0-9a-f]*'
    ),
    CHECK (
        previous_event_hash IS NULL
        OR (
            length(previous_event_hash) = 64
            AND previous_event_hash = lower(previous_event_hash)
            AND previous_event_hash NOT GLOB '*[^0-9a-f]*'
        )
    ),
    CHECK (
        length(event_hash) = 64
        AND event_hash = lower(event_hash)
        AND event_hash NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE INDEX ix_journal_operation_effect
ON operation_journal(operation_id, attempt_no, sequence_no);

CREATE TABLE receipts (
    receipt_ref TEXT PRIMARY KEY,
    receipt_hash TEXT NOT NULL UNIQUE,
    operation_id TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NOT NULL UNIQUE,
    transition_ref TEXT NOT NULL UNIQUE,
    effect_contract_ref TEXT NOT NULL,
    effect_contract_hash TEXT NOT NULL,
    result_version_ref TEXT NOT NULL,
    payload_ref TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (transition_ref) REFERENCES transitions(transition_ref),
    CHECK (receipt_ref = 'sha256:' || receipt_hash),
    CHECK (effect_contract_ref = 'sha256:' || effect_contract_hash),
    CHECK (
        length(receipt_hash) = 64
        AND receipt_hash = lower(receipt_hash)
        AND receipt_hash NOT GLOB '*[^0-9a-f]*'
    ),
    CHECK (
        length(effect_contract_hash) = 64
        AND effect_contract_hash = lower(effect_contract_hash)
        AND effect_contract_hash NOT GLOB '*[^0-9a-f]*'
    )
);

CREATE TRIGGER artifact_bindings_no_update
BEFORE UPDATE ON artifact_bindings
BEGIN
    SELECT RAISE(ABORT, 'artifact_bindings append-only');
END;

CREATE TRIGGER artifact_bindings_verify_sealed_verified
BEFORE INSERT ON artifact_bindings
BEGIN
    SELECT CASE
        WHEN NEW.binding_state != 'VERIFIED'
        THEN RAISE(ABORT, 'artifact_bindings VERIFIED required')
        WHEN NEW.binding_hash != w7tp_artifact_binding_hash(
            NEW.node_id,
            NEW.workspace_id,
            NEW.artifact_ref,
            NEW.manifest_ref,
            NEW.artifact_hash,
            NEW.capability_id,
            NEW.version,
            NEW.adapter_ref,
            NEW.binding_state,
            NEW.evidence_ref,
            NEW.observed_at
        )
        OR NEW.binding_ref != 'sha256:' || w7tp_artifact_binding_hash(
            NEW.node_id,
            NEW.workspace_id,
            NEW.artifact_ref,
            NEW.manifest_ref,
            NEW.artifact_hash,
            NEW.capability_id,
            NEW.version,
            NEW.adapter_ref,
            NEW.binding_state,
            NEW.evidence_ref,
            NEW.observed_at
        )
        THEN RAISE(ABORT, 'artifact_bindings sealed hash conflict')
    END;
END;

CREATE TRIGGER artifact_bindings_no_delete
BEFORE DELETE ON artifact_bindings
BEGIN
    SELECT RAISE(ABORT, 'artifact_bindings append-only');
END;

CREATE TRIGGER effect_operation_claims_no_update
BEFORE UPDATE ON effect_operation_claims
BEGIN
    SELECT RAISE(ABORT, 'effect_operation_claims append-only');
END;

CREATE TRIGGER effect_operation_claims_no_delete
BEFORE DELETE ON effect_operation_claims
BEGIN
    SELECT RAISE(ABORT, 'effect_operation_claims append-only');
END;

CREATE TRIGGER effect_attempt_claims_no_update
BEFORE UPDATE ON effect_attempt_claims
BEGIN
    SELECT RAISE(ABORT, 'effect_attempt_claims append-only');
END;

CREATE TRIGGER effect_attempt_claims_no_delete
BEFORE DELETE ON effect_attempt_claims
BEGIN
    SELECT RAISE(ABORT, 'effect_attempt_claims append-only');
END;

CREATE TRIGGER operation_journal_no_update
BEFORE UPDATE ON operation_journal
BEGIN
    SELECT RAISE(ABORT, 'operation_journal append-only');
END;

CREATE TRIGGER operation_journal_no_delete
BEFORE DELETE ON operation_journal
BEGIN
    SELECT RAISE(ABORT, 'operation_journal append-only');
END;

CREATE TRIGGER transitions_no_update
BEFORE UPDATE ON transitions
BEGIN
    SELECT RAISE(ABORT, 'transitions append-only');
END;

CREATE TRIGGER transitions_no_delete
BEFORE DELETE ON transitions
BEGIN
    SELECT RAISE(ABORT, 'transitions append-only');
END;

CREATE TRIGGER receipts_no_update
BEFORE UPDATE ON receipts
BEGIN
    SELECT RAISE(ABORT, 'receipts append-only');
END;

CREATE TRIGGER receipts_no_delete
BEFORE DELETE ON receipts
BEGIN
    SELECT RAISE(ABORT, 'receipts append-only');
END;

CREATE TRIGGER objects_no_update
BEFORE UPDATE ON objects
BEGIN
    SELECT RAISE(ABORT, 'objects append-only');
END;

CREATE TRIGGER objects_no_delete
BEFORE DELETE ON objects
BEGIN
    SELECT RAISE(ABORT, 'objects append-only');
END;

CREATE TRIGGER manifests_no_update
BEFORE UPDATE ON manifests
BEGIN
    SELECT RAISE(ABORT, 'manifests append-only');
END;

CREATE TRIGGER manifests_no_delete
BEFORE DELETE ON manifests
BEGIN
    SELECT RAISE(ABORT, 'manifests append-only');
END;

CREATE TRIGGER manifest_entry_no_update
BEFORE UPDATE ON manifest_entry
BEGIN
    SELECT RAISE(ABORT, 'manifest_entry append-only');
END;

CREATE TRIGGER manifest_entry_no_delete
BEFORE DELETE ON manifest_entry
BEGIN
    SELECT RAISE(ABORT, 'manifest_entry append-only');
END;

CREATE TRIGGER manifest_entry_chunk_no_update
BEFORE UPDATE ON manifest_entry_chunk
BEGIN
    SELECT RAISE(ABORT, 'manifest_entry_chunk append-only');
END;

CREATE TRIGGER manifest_entry_chunk_no_delete
BEFORE DELETE ON manifest_entry_chunk
BEGIN
    SELECT RAISE(ABORT, 'manifest_entry_chunk append-only');
END;
