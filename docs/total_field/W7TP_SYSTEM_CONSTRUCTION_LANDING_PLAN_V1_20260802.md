# W7TP System Construction Landing Plan V1

## Plan Identity and Boundary

- Plan date: 2026-08-02
- Current node: MSI
- Current phase: PLAN
- Landing execution: not performed
- Founder authority resolution action: `MODIFY_EXISTING`
- Maximum landing effect: `E5_IDENTITY_AUTHORITY_CHANGE`
- Candidate proposal classification: `ARTIFACT_CLASS=CANDIDATE_PROPOSAL_EVIDENCE_ONLY`
- Candidate proposal production Owner: false
- Candidate proposal operational landing target: false
- Exact files to create during landing: `[]`
- Formal submission, deployment, database write, service restart, commit, and push: prohibited by this plan phase

The plan resolves an existing authority-validation defect. It does not create a Founder identity, Seat, access profile, D8 receipt, canonical pointer, or final Total Field decision. The operational change only resolves already existing opaque references and returns one of four outcomes: `RESOLVED`, `HOLD_MISSING_BINDING`, `HOLD_AMBIGUOUS_BINDING`, or `BLOCK_FORGED_BINDING`.

## Evidence and Owner Decision

The MSI read-only inspection used Git-tracked files in `tools/total_field/`, `core/`, `schemas/`, `manifests/`, `scripts/verify/`, `tests/`, and `runtime/total_field/`, plus the already identified active receiver at `/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py`.

The active receiver owns the `authority_ref` acceptance branch. Its current worktree SHA-256 is `10364480097fc0394427176d4eebf8260a7043fae853a3ae895a859dfb192d43`. The function `receive_candidate` currently checks only whether `authority_ref` is nonempty at lines 420 through 426, and `_decision_result` hashes the supplied value. This is the earliest and correct operational point for authority resolution.

`/home/taiji_admin/Taiji_Hub/tools/total_field/google_external_candidate_dual_channel.py#resolve_existing_receive_candidate` discovers the existing receiver but does not own identity or authority validation. `manifests/ollama_xiaoj_total_field_v0_1/capability_registry.json` requires a verified authority reference but remains `LOCAL_CANDIDATE_ONLY`; it is not an authority root. `/home/taiji_admin/Taiji_Hub/candidates/total_field/founder_authority_resolver_v1/RECEIVER_INTEGRATION_PROPOSAL.json` is candidate evidence and is excluded from the Owner set.

Because the existing `receive_candidate` Owner already contains the authority gate and can carry an embedded exact schema plus resolver without introducing a parallel ingress, the selected action is `MODIFY_EXISTING`. No operational file is created.

# Exact Owner Map

| OWNER_FILE | OWNER_SYMBOL | OWNER_ROLE | SCHEMA_PATH | VERIFIER_PATH | TEST_PATH | CURRENT_BEHAVIOR | MISSING_CAPABILITY |
|---|---|---|---|---|---|---|---|
| `/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py` | `receive_candidate` | Active local Total Field candidate receiver and `authority_ref` gate | `/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py` with symbol `FOUNDER_AUTHORITY_BINDING_SCHEMA_V1` | `/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py` with symbol `resolve_founder_authority_binding` | `/home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py` | Accepts any nonempty `authority_ref`, then hashes it | Exact opaque Founder, unique ACTIVE_MEMBER_XIAOJ Seat, access-profile, binding digest, expiry, D8 receipt, and ambiguity verification |
| `/home/taiji_admin/Taiji_Hub/tools/total_field/google_external_candidate_dual_channel.py` | `resolve_existing_receive_candidate` | Existing ingress discovery only | `/home/taiji_admin/Taiji_Hub/schemas/field/w7tp_google_external_candidate_dual_channel_v1.schema.json` | `/home/taiji_admin/Taiji_Hub/tools/total_field/google_external_candidate_dual_channel.py` with symbol `validate_authorization` | `/home/taiji_admin/Taiji_Hub/tests/test_google_external_candidate_dual_channel.py` | Reuses an existing receiver | Does not own Founder identity, Seat, profile, or authority binding resolution |
| `/home/taiji_admin/Taiji_Hub/manifests/ollama_xiaoj_total_field_v0_1/capability_registry.json` | `identity_profiles.founder` | Candidate-only capability policy evidence | `/home/taiji_admin/Taiji_Hub/manifests/ollama_xiaoj_total_field_v0_1/capability_registry.json` | `/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py` with symbol `_load_capability_pack` | `/home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py` | Declares that a verified authority reference is required | Cannot establish authority and must not be promoted into an identity registry |

# Exact Change Manifest

## Change 1: active receiver Owner

- absolute_path: `/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py`
- operation: `MODIFY_EXISTING`
- Owner symbol: `receive_candidate`
- pre-landing worktree SHA-256: `10364480097fc0394427176d4eebf8260a7043fae853a3ae895a859dfb192d43`
- pre-landing index SHA-256: `174af91a79c0faca47cade6767db35790b4600a14c7ea3283ba5a6d54c39b01a`
- unrelated worktree bytes: preserve exactly
- embedded schema symbol to add: `FOUNDER_AUTHORITY_BINDING_SCHEMA_V1`
- resolver symbol to add: `resolve_founder_authority_binding`
- receiver branch to change: `receive_candidate` authority validation at the current nonempty check

The embedded schema requires exactly these authority fields:

1. `founder_subject_ref`: opaque string without name, email, account identifier, or member plaintext.
2. `active_member_xiaoj_seat_ref`: opaque string.
3. `seat_state`: exact value `ACTIVE_MEMBER_XIAOJ`.
4. `access_profile_ref`: opaque string.
5. `authority_binding_ref`: opaque string.
6. `binding_version`: positive integer.
7. `binding_digest`: lowercase 64-character SHA-256.
8. `seat_assignment_hash`: lowercase 64-character SHA-256.
9. `profile_hash`: lowercase 64-character SHA-256.
10. `d8_authority_receipt_ref`: opaque string.
11. `d8_authority_receipt_sha256`: lowercase 64-character SHA-256.
12. `expires_at`: timezone-qualified ISO-8601 timestamp later than resolver time.
13. `nonce`: opaque single-use string of at least 16 characters.

The resolver must validate exact keys, primitive types, opaque-reference syntax, fixed Seat state, expiry, nonce replay, binding digest recomputation, unique matching evidence, and a hash-bound D8 authority receipt reference in the governed dynamic-context evidence. It must not read or derive a name, email address, account identifier, or member plaintext. It must not create identity data.

The resolver output is a single status string. The allowed values are `RESOLVED`, `HOLD_MISSING_BINDING`, `HOLD_AMBIGUOUS_BINDING`, and `BLOCK_FORGED_BINDING`. No output carries ALLOW, ACTIVE, canonical authority, or Total Field decision semantics.

`receive_candidate` must call `resolve_founder_authority_binding(authority_ref, dynamic_context_packet)` after dynamic-context packet integrity validation and before the existing nonempty check and before `_decision_result` can hash the value. On `RESOLVED`, only the validated opaque binding projection reaches the existing hash calculation. On either HOLD result, the receiver stops with a corresponding HOLD state and passes `None` as the authority value to `_decision_result`. On `BLOCK_FORGED_BINDING`, it stops with `BLOCK_FORGED_AUTHORITY_BINDING` and passes `None` as the authority value. Candidate-only execution restrictions remain unchanged.

Replay detection occurs before receiver acceptance. A replay maps to `BLOCK_FORGED_BINDING`; the caller-facing result includes a dead-letter disposition reference without writing data in the resolver. The router dead-letter owner must remain external to this change. If its existing route cannot be resolved at landing preflight, landing stops with `HOLD_REPLAY_DEAD_LETTER_BINDING_MISSING` before modifying either file.

Rollback for Change 1 is an exact reverse patch scoped only to the added schema symbol, resolver symbol, imports used solely by those symbols, and the new authority-resolution branch. The reverse patch restores this exact original branch:

```python
    if authority_ref in (None, "", {}):
        return _decision_result(
            "HOLD_AUTHORITY_INCOMPLETE",
            reason="authority_ref is required",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )
```

Rollback is allowed only when the landing receipt proves that the current bytes equal the post-change hash and the unrelated pre-landing worktree bytes remain identical. It must not restore the staged index version because the worktree and index already differ before landing.

## Change 2: focused receiver tests

- absolute_path: `/home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py`
- operation: `MODIFY_EXISTING`
- pre-landing SHA-256: `7667144f0e874cb0814acd78edd8b1dc3cd68452081210527e140ad85aea96ae`
- test class: `TotalFieldDynamicContextTests`
- required Owner import: `receive_candidate` and `resolve_founder_authority_binding`
- rollback: remove only the listed new test methods and their newly required imports after verifying the post-change hash from the landing receipt

The exact test methods to add are:

1. `test_authority_none_empty_and_arbitrary_ref_hold`
2. `test_authority_hash_only_holds_missing_binding`
3. `test_authority_cross_binding_blocks_forgery`
4. `test_authority_pending_and_test_records_rejected`
5. `test_authority_non_active_seat_states_rejected`
6. `test_authority_expired_profile_and_receipt_hold`
7. `test_authority_ambiguous_binding_holds`
8. `test_authority_nonce_replay_blocks_before_receiver_acceptance`
9. `test_authority_complete_opaque_binding_resolves`
10. `test_receive_candidate_resolves_authority_before_decision_hash`
11. `test_existing_candidate_only_receive_contract_regression`

## Files excluded from landing writes

- `/home/taiji_admin/Taiji_Hub/candidates/total_field/founder_authority_resolver_v1/RECEIVER_INTEGRATION_PROPOSAL.json`
- `/home/taiji_admin/Taiji_Hub/candidates/total_field/founder_authority_resolver_v1/FOUNDER_GENESIS_BOOTSTRAP_PACKET_CANDIDATE.json`
- `/home/taiji_admin/Taiji_Hub/manifests/ollama_xiaoj_total_field_v0_1/capability_registry.json`
- `/home/taiji_admin/Taiji_Hub/manifests/ollama_xiaoj_total_field_v0_1/founder_all_skills_8d_index.json`

These files remain evidence or candidate-only capability descriptions. They must not be used as an authority root, Seat registry, active access profile, or D8 receipt.

# Ordered State Transitions

1. `PLAN_HASH_BOUND`: verify the Founder-approved plan SHA-256 and exact scope.
2. `PRECONDITIONS_VERIFIED`: verify both modify-target SHA-256 values, preserve the receiver's pre-existing worktree/index divergence, confirm no target bytes changed after approval, and resolve the existing router dead-letter disposition interface without writing it.
3. `RED_TEAM_PRE_ACTIVATION`: verify that no input includes member plaintext, name, email, account identifier, key, token, password, candidate authority claim, or unverified active state.
4. `OWNER_PATCHED`: apply only Change 1 to the existing Owner; do not create files.
5. `TEST_PATCHED`: apply only Change 2 to the existing test file; do not create files.
6. `STATIC_VALIDATION`: parse the module, inspect the exact schema constant, verify the four-value resolver output domain, and confirm receiver call ordering before authority hashing.
7. `FOCUSED_TESTS`: run only the 11 named test methods plus the current dynamic-context candidate-only regression tests affected by imports and call ordering.
8. `POST_CHANGE_HASH_BOUND`: calculate post-change SHA-256 for both modified files and record them in the landing receipt held in memory until separately authorized evidence persistence exists.
9. `LANDING_COMPLETE_NOT_ACTIVATED`: report code landing only. No Founder identity, Seat, profile, D8 authority, canonical pointer, deployment, database write, restart, commit, or push occurs.

Any failed transition stops before the next transition. No partial change is promoted as authority.

# Validation Matrix

| Validation | Exact evidence or method | Required result | Failure state |
|---|---|---|---|
| Plan binding | Founder approval contains this plan's exact SHA-256 | Match | `HOLD_PLAN_HASH_MISMATCH` |
| Owner baseline | SHA-256 of `/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py` | `10364480097fc0394427176d4eebf8260a7043fae853a3ae895a859dfb192d43` before patch | `HOLD_OWNER_BASELINE_DRIFT` |
| Test baseline | SHA-256 of `/home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py` | `7667144f0e874cb0814acd78edd8b1dc3cd68452081210527e140ad85aea96ae` before patch | `HOLD_TEST_BASELINE_DRIFT` |
| Opaque fields | Resolver schema and focused tests | All identity values are opaque references | `BLOCK_FORGED_BINDING` |
| Missing binding | Missing field, empty value, absent evidence, or absent D8 receipt | `HOLD_MISSING_BINDING` | `HOLD_MISSING_BINDING` |
| Ambiguity | More than one evidence record matches one authority binding | `HOLD_AMBIGUOUS_BINDING` | `HOLD_AMBIGUOUS_BINDING` |
| Forgery | Hash mismatch, cross-binding, inactive Seat, expired profile, invalid receipt, or nonce replay | `BLOCK_FORGED_BINDING` | `BLOCK_FORGED_BINDING` |
| Pending and test data | Candidate, pending seal, pending receipt, reservation, suspended, expired, or test record | Rejected | `HOLD_MISSING_BINDING` or `BLOCK_FORGED_BINDING` according to integrity |
| Positive isolated vector | Complete opaque synthetic chain passed only through test isolation | `RESOLVED` in isolated test path and never in runtime path | `HOLD_TEST_VECTOR_BOUNDARY_FAILURE` |
| Receiver ordering | Static inspection and `test_receive_candidate_resolves_authority_before_decision_hash` | Resolver precedes authority hashing | `HOLD_RECEIVER_ORDER_INVALID` |
| Candidate contract regression | Existing candidate-only receiver tests | No execution, database, deploy, restart, router, or canonical write authority | `HOLD_CANDIDATE_CONTRACT_REGRESSION` |
| Replay dead-letter interface | Existing router route resolution, read-only | Exact existing route resolved before patch | `HOLD_REPLAY_DEAD_LETTER_BINDING_MISSING` |
| Write scope | Changed-path comparison against pre-landing snapshot | Exactly two operational files modified | `HOLD_WRITE_SCOPE_BREACH` |

# Embedded Landing Contract

```yaml
contract_id: W7TP_SYSTEM_CONSTRUCTION_LANDING_PLAN_V1_20260802
node: MSI
action: MODIFY_EXISTING
maximum_effect: E5_IDENTITY_AUTHORITY_CHANGE
create_actions: []
modify_actions:
  - absolute_path: /home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py
    operation: MODIFY_EXISTING
    required_owner_symbol: receive_candidate
    required_schema_path: /home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py
    required_schema_symbol: FOUNDER_AUTHORITY_BINDING_SCHEMA_V1
    required_verifier_path: /home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py
    required_verifier_symbol: resolve_founder_authority_binding
    required_test_path: /home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py
    precondition_sha256: 10364480097fc0394427176d4eebf8260a7043fae853a3ae895a859dfb192d43
    overwrite_unrelated_bytes: false
    delete: false
    move: false
    rollback: REVERSE_ONLY_THIS_PLAN_PATCH_IF_POST_HASH_MATCHES_LANDING_RECEIPT
  - absolute_path: /home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py
    operation: MODIFY_EXISTING
    required_owner_symbol: TotalFieldDynamicContextTests
    required_schema_path: /home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py
    required_schema_symbol: FOUNDER_AUTHORITY_BINDING_SCHEMA_V1
    required_verifier_path: /home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py
    required_verifier_symbol: resolve_founder_authority_binding
    required_test_path: /home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py
    precondition_sha256: 7667144f0e874cb0814acd78edd8b1dc3cd68452081210527e140ad85aea96ae
    overwrite_unrelated_bytes: false
    delete: false
    move: false
    rollback: REMOVE_ONLY_THE_ELEVEN_PLAN_NAMED_TESTS_AND_NEW_IMPORTS_IF_POST_HASH_MATCHES_LANDING_RECEIPT
candidate_proposal_used_as_owner: false
runtime_authority_created_by_code_landing: false
receiver_call_authorized: false
formal_submission_authorized: false
database_write_authorized: false
deploy_authorized: false
service_restart_authorized: false
commit_authorized: false
push_authorized: false
```

There are no CREATE actions. Therefore `absolute_path`, `CREATE_EXCLUSIVE`, `O_CREAT|O_EXCL`, parent Owner, target-exists handling, and delete-only-if-created rollback semantics do not apply to an operational landing target in this plan. `EXCLUSIVE_CREATE_TARGET=NONE`, and the unresolved-create-path set is empty.

# Founder Approval Transition

The current plan phase ends after the plan SHA-256 is calculated and reported. No landing action is authorized by creating this document.

Landing requires one Founder decision carrying all of these exact fields:

- `FOUNDER_APPROVAL=APPROVE_W7TP_SYSTEM_CONSTRUCTION_LANDING_PLAN_V1`
- `PLAN_SHA256` equal to the SHA-256 reported with this document
- `TARGET=LANDING`
- `APPROVED_SCOPE=MODIFY_EXISTING:/home/taiji_admin/Taiji_Hub/tools/total_field_dynamic_context.py#receive_candidate,/home/taiji_admin/Taiji_Hub/tests/test_total_field_dynamic_context.py#TotalFieldDynamicContextTests`

Approval is single-use. It is consumed at the first attempted patch after all preconditions pass, or at the first technical HOLD after approval validation. It expires when any precondition SHA-256 changes, the approved scope changes, the MSI node changes, or the Founder explicitly withdraws it.

Stop immediately on any plan hash mismatch, Owner/test baseline drift, unresolved router dead-letter interface, protected plaintext detection, ambiguous binding, forged binding, pending or test authority record in the runtime path, failed focused test, write-scope expansion, receiver call attempt, formal submission attempt, database write, deployment, restart, commit, or push.

## Rollback Summary

Rollback applies the exact reverse patches described in Change 1 and Change 2 only after matching the landing receipt's post-change hashes. It preserves all bytes that existed before the landing transaction, including the receiver's existing worktree/index divergence. If post-change hashes do not match the landing receipt, rollback stops with `HOLD_ROLLBACK_BASELINE_AMBIGUOUS` and performs no write.

## Plan Completion Assertions

- All operational target paths are absolute.
- There are no operational CREATE actions.
- No candidate directory is a formal Owner.
- No unresolved create path exists.
- The existing receiver Owner and existing test file are the only planned operational modifications.
- The candidate proposal remains read-only evidence.
- This document is the only file written in the PLAN phase.
- Landing, activation, formal submission, deployment, database write, service restart, commit, and push have not occurred.
