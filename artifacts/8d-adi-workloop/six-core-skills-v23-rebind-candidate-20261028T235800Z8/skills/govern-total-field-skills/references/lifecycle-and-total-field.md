# Skill lifecycle and Total Field integration

## States

Use exactly one lifecycle state:

1. `DRAFT_LOCAL`
2. `CANDIDATE_FOR_TOTAL_FIELD_REVIEW`
3. `ALLOW_ISOLATED_CANARY_ONLY`
4. `ACTIVE`
5. `SUSPENDED`
6. `DEPRECATED`
7. `RETIRED`
8. `BLOCKED`

Only a Total Field decision receipt may set states 3 through 8. A file edit, installation, test PASS, manifest validation, extension activation, model reload, or Founder instruction without a matching D8 receipt does not set `ACTIVE`.

## Registration

Submit a manifest candidate containing its self-hash, implementation hashes, schema hash, product/output contract, effect class, Seat/profile requirements, D1-D8 projections, red-team record, verifier, rollback, and evidence destination. Version transitions create append-only records or new packets; they never silently overwrite a prior manifest, receipt, lineage edge, or lifecycle state.

Total Field checks:

- unique `skill_id` and version ordering;
- duplicate or conflicting product capabilities;
- effect class against actual tool and side-effect surface;
- identity, Seat, member, provider, node, and protected-data boundaries;
- D1-D8 completeness and D8 non-self-authority;
- W7TP technical-definition claims;
- verification, rollback, evidence, HOLD, and retirement behavior;
- open red-team findings and closure evidence.

## Invocation

At invocation, bind the active manifest hash, implementation hash, identity profile, Seat assignment, requested effect, input/context hashes, nonce, logical time, TTL, and Total Field receiver. Reject replay, stale manifest, changed implementation, expired profile, or an effect above the manifest class.

Every run returns a receipt with product/output status, evidence, effects, D1-D8 projection, red-team status, human response, and one next action.

## Suspension and retirement

Suspend on:

- manifest or implementation hash drift;
- missing or invalid Seat/profile;
- open high/critical red-team finding;
- verifier or product/output acceptance failure;
- protected-data or cross-member boundary violation;
- missing rollback for E3-E5;
- canonical replacement or expired dependency.

Suspension revokes new sessions and stops state-changing execution while preserving read-only evidence needed to diagnose and repair. It must not delete or silently overwrite business data, member records, source, manifests, prior packets, lineage, decision indexes, or receipts.

Retirement requires replacement or end-of-life evidence, session revocation, dependency release, archived manifests/receipts, and proof that no active workflow still depends on the skill. Deletion of evidence is not retirement.
