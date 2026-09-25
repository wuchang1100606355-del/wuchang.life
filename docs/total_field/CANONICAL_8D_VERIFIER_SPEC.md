# Canonical 8D Verifier Spec

STATE=CANONICAL_8D_VERIFIER_SPEC
MODE=REVIEW_ONLY_BUNDLE
SCOPE=LOCAL_VERIFIER_ONLY

## Purpose
Canonical 8D Verifier is a local verifier for W7TP / Taiji / XiaoJ.
It performs local reconstruction, D7 signature verification, persistent nonce replay guard, deterministic tensor lookup, and tamper-evident audit logging.

## D7 Signature
D7 is not a fixed string. It must be an HMAC/signature bound to D1, D2, D4, D8.nonce, and D8.timestamp.
Invalid signature returns DENY_D7_SIGNATURE_INVALID.

## Nonce Ledger
Nonce replay guard must survive restart. Minimum implementation is SQLite with nonce, packet_hash, used_at, expires_at.

## 8D to Five-Element Mapping
Metal = D6 Governance + D5 Resource
Wood = D2 Task Reference
Water = D4 Topology
Fire = D3 State + D8 Envelope
Earth = D1 Identity + D7 Verification
Unknown tuple returns QUARANTINE_DENY_BY_DEFAULT.

## Audit Log
Required fields: run_id, packet_hash, trajectory_hmac, collapse_result, verifier_version, prev_log_hash, log_hash, log_hmac, key_version, gate_stage, seal_version, external_anchor_ref, created_at.
Hash-chain is tamper-evident. Do not claim absolute immutability without external anchoring.

## Secret Policy
Production module must not hardcode production secrets. Secrets must be dependency injected or loaded by an approved local secret provider.
Missing secret returns DENY_SECRET_NOT_CONFIGURED or HOLD before execution.

## Required Tests
VALID_PACKET=EXEC_POS_ORDER
REPLAY_AFTER_RESTART=DENY_REPLAY_ATTACK
EXPIRED_PACKET=DENY_TTL_EXPIRED
BAD_SIGNATURE=DENY_D7_SIGNATURE_INVALID
MISSING_D8=DENY_SCHEMA_INVALID_D8_ENVELOPE
UNKNOWN_TASK=QUARANTINE_DENY_BY_DEFAULT
AUDIT_CHAIN_VERIFY=PASS
TAMPERED_LOG=HASH_CHAIN_BREAK
PLAINTEXT_STORAGE=FALSE
SECRET_PRINT=FALSE

## Safety Boundary
No production DB write. No Odoo production write. No member plaintext read. No secret print. No service restart. No deploy. No production release. No external API call.

## Claim Boundary
Allowed claims: local reconstruction, deny-by-default, D7 signature verification, persistent nonce guard, HMAC trajectory summary, tamper-evident audit chain, reduced plaintext audit exposure.
Disallowed claims: absolute security, physical-limit guarantee, unqualified zero-knowledge, unqualified breach immunity, unqualified immutable chain.
