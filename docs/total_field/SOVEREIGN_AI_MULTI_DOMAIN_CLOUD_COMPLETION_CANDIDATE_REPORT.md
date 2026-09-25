# Sovereign AI Multi-Domain Cloud Completion Candidate Report

## Document identity

- `RUN_ID=SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANDIDATE_V0_1`
- `DOCUMENT_STATUS=CANDIDATE_ONLY`
- `CLOUD_COMPLETION=SUPPORTED_AS_CANDIDATE_ONLY`
- `FULL_AUTHORITY=NEVER`
- `CANONICAL_PROMOTION=NOT_PERFORMED`

This document defines a candidate-only integration boundary for cloud-assisted attribute completion. A cloud model may propose values and evidence references, but it cannot adjudicate, commit, create a TFS, or acquire Total Field authority. The existing Total Field Gateway and TRUE8D runtime remain the sole processing path; this candidate does not introduce a parallel engine.

## Fixed domain scope

Only the following three domain labels are in scope:

| Domain | Chinese label | Candidate scope |
|---|---|---|
| `COMMUNITY` | 社區場域 | Community-context attribute completion candidates |
| `COMMERCE` | 商業場域 | Commercial-context attribute completion candidates |
| `PROPERTY` | 物業場域 | Property-context attribute completion candidates |

The labels are a closed candidate allowlist. A model-generated label is not proof of domain membership. Unknown, empty, conflicting, or ambiguous classification must remain uncommitted and proceed through a non-`ALLOW` outcome. Adding a fourth domain requires a separate candidate revision and must not occur through free-form model output.

## Candidate-only processing flow

The only permitted logical flow is:

```text
Cloud LLM Candidate
  -> XiaoJ candidate envelope
  -> existing Total Field Gateway
  -> TRUE8D
  -> constraints
  -> convergence
  -> D8
  -> ALLOW-only TFS
```

Responsibilities are separated as follows:

1. **Cloud LLM Candidate** proposes domain classification and attribute values. It supplies no final decision, commit state, TFID, Total Field hash, or committed state.
2. **XiaoJ candidate envelope** performs provider-neutral semantic wrapping. Persona material remains separate from the governance payload and cannot become decision evidence merely because XiaoJ produced it.
3. **Existing Total Field Gateway** remains the common candidate ingress. The completion adapter supplies a closed Observation Domain mapping and delegates to the existing receiver; it does not bypass schema validation or create an alternate gateway authority.
4. **TRUE8D and constraints** evaluate required fields, external authority claims, D6 sovereign privacy, D7 reference-only semantics, configured Observation Domain status, and other registered candidate constraints.
5. **Convergence** operates on captured deterministic inputs. Provider generation is outside the deterministic core.
6. **D8** alone produces `ALLOW`, `HOLD`, `BLOCK`, or `QUARANTINE`.
7. **ALLOW-only TFS** means a TFS may represent the proposed completion only when the existing runtime reaches its required fixed point and D8 returns `ALLOW`. Every other decision preserves the previous committed state.

`CLOUD_COMPLETION=SUPPORTED_AS_CANDIDATE_ONLY` therefore means the cloud may contribute a proposal to this flow. It never means cloud output is complete, trusted, canonical, committed, or `FULL_AUTHORITY`.

## Classification gates

Classification is a candidate assertion subject to all of these gates:

| Gate | Required behavior |
|---|---|
| Domain allowlist | Accept only `COMMUNITY`, `COMMERCE`, or `PROPERTY` as candidate labels. |
| Evidence reference | Associate classification with detached evidence references; prose confidence alone is insufficient. |
| Ambiguity isolation | Conflicting or multi-domain classification remains non-committing until an explicit candidate rule resolves it. |
| External authority guard | Reject an envelope that claims `ALLOW`, committed state, `commit_applied=true`, TFID, or Total Field hash. |
| Observation Domain | Use an opaque configured reference supplied by the trusted caller. An unconfigured domain remains a deterministic hold condition. |
| D6 sovereign privacy | Sensitive material and declared hard risks remain governed by the existing privacy gate. Raw secrets are never completion inputs or outputs. |
| D7 reference-only | Store references or reconstruction conditions only; do not reinterpret completion as file movement, synchronization, backup, download, or decryption. |
| D8 adjudication | Only the existing adjudicator can authorize commit. Cloud and XiaoJ outputs remain candidates. |

No classification score is treated as authority. Thresholds, tie-break rules, and conflict resolution are versioned policy concerns and are not invented by this document.

## Per-attribute batch isolation

A batch is an ordered collection of independent attribute-completion candidates, not one shared commit transaction.

- Each attribute has its own attribute reference, domain label, event identity, logical ordering input, rule reference, source value reference, proposed value, and evidence references.
- Each attribute is enveloped, validated, hashed, replayed, converged, and adjudicated independently.
- One malformed, sensitive, blocked, quarantined, ambiguous, or unavailable attribute does not alter another attribute's candidate body or decision.
- A failure in one unit must not promote, suppress, overwrite, or roll back an unrelated unit.
- Batch ordering is explicit input. Runtime clock time, random UUIDs, process identifiers, and provider-local ordering are excluded from deterministic identity.
- Batch summaries may aggregate results for display, but cannot turn several non-`ALLOW` results into an `ALLOW` or perform a batch-wide commit.
- Retries reuse the same immutable candidate inputs and identifiers. A changed proposal or evidence set is a new candidate input and must produce a new deterministic hash.

This isolation keeps partial results reviewable while preserving the existing ALLOW-only commit invariant.

## Deterministic hashing and replay

Determinism begins after provider output has been captured as a closed candidate envelope. The provider call itself is not part of the deterministic core.

- Caller inputs are detached before normalization or evaluation.
- Canonical JSON uses sorted keys, UTF-8-preserving serialization, compact separators, and rejection of NaN and Infinity.
- SHA-256 binds the normalized candidate envelope, fixed domain label, event identity, logical time, rule and policy references, evidence references, and other declared transition inputs.
- Current time, random values, random UUIDs, mutable external state, credentials, persona text, and transport session data are excluded.
- Replaying identical captured inputs through the same versioned rules must reproduce the same candidate hash, proposed state, D8 decision, commit result, and Total Field result identifiers.
- A difference in any bound attribute input, event identity, logical time, domain reference, rule reference, policy reference, or evidence reference must be visible in replay comparison.

Replay equivalence is local deterministic equivalence. Distributed consensus remains outside this candidate's claims.

## Provider boundary

The candidate implementation and validation boundary permits only provider-neutral `Fake` or `InMemory` providers.

- `REAL_LLM_CALL=NO`
- `PROVIDER_MODE=Fake/InMemory_ONLY`
- `PROVIDER_CREDENTIAL_READ=NO`
- `EXTERNAL_NETWORK_CALL=NO`
- `MODEL_SPECIFIC_AUTHORITY=NO`

Fixtures must contain no secret, token, password, member plaintext, raw private data, or live credential. Fake provider responses are captured candidate examples only. A future real cloud provider requires a separate security, privacy, data-residency, credential, availability, and failure-mode review; it still must enter through the same candidate-only gateway.

## Persona and governance separation

Persona text may influence presentation or provider-neutral prompting, but it is not governance state.

- Persona is stored outside the 8D governance candidate body.
- Persona is excluded from deterministic candidate, transition, TFS, and Total Field hashes.
- Persona cannot populate D6 authority, D7 routing/reference authority, or D8 decision state.
- Persona cannot claim domain classification evidence, override a constraint, or authorize commit.
- The XiaoJ envelope carries governance fields and references explicitly; it does not copy persona prose into committed TFS state.

## Existing integration seams

The nearest existing integration seam is the common receiver in `tools/total_field_candidate_gateway.py`:

- `receive_candidate(...)` accepts the candidate payload, previous state, caller-supplied Observation Domain registry, and candidate policy.
- `TotalFieldCandidateGateway` binds a detached Observation Domain registry while preserving the same common receiver.
- `total_field_pull(...)` and `llm_push(...)` set source mode only and then use the common receiver.

The existing TRUE8D candidate runtime supplies `ObservationDomain`, `Event`, `EightFieldState`, `run_convergence(...)`, and the ALLOW-only finalization invariant. A domain-completion adapter should construct the closed Observation Domain registry and delegate exactly once to the gateway. It must not call an alternate adjudicator, write D8 state into a proposed field body, or introduce a second convergence engine.

## Side-effect and authority boundary

This candidate report authorizes no operational mutation:

- `DB_WRITE=NO`
- `DEPLOY=NO`
- `RESTART=NO`
- `REBOOT=NO`
- `ROUTER_WRITE=NO`
- `FIREWALL_WRITE=NO`
- `ACTIVE_CANONICAL_WRITE=NO`
- `POINTER_WRITE=NO`
- `ACTIVE_RUNTIME_POLICY_WRITE=NO`

No Active Canonical, Pointer, database, router configuration, service, runtime process, or network route is changed by this candidate design.

## Limitations and open problems

1. A production domain ontology and versioned attribute registry for `COMMUNITY`, `COMMERCE`, and `PROPERTY` are not defined here.
2. Formal classification thresholds, multi-label conflict policy, missing-evidence handling, and deterministic tie-break rules remain open policy work.
3. Production Observation Domain registration, authorization, expiry, provenance, and revocation contracts remain to be specified.
4. Domain-specific constraint sets and convergence rules require independent evidence and candidate review.
5. A real cloud provider is not integrated or tested. Credential handling, privacy impact, residency, retention, provider outage behavior, and prompt-injection controls remain open.
6. Batch retry, idempotency retention, partial-result presentation, and operational rate limiting require a versioned implementation contract.
7. Cross-node distributed consensus, global uniqueness, and multi-node failure recovery remain open problems; this report claims local deterministic replay only.
8. Performance, accuracy, completion quality, and cost have no measured production evidence in this candidate.
9. Human review criteria and any later canonical-promotion process require separate authorization and verification.
10. XiaoJ's production provider channel, if later added, must preserve persona/governance separation and cannot receive direct commit authority.

## Candidate conclusion

The three-domain completion path is structurally supportable only as a proposal source feeding the existing candidate gateway and TRUE8D adjudication chain. Its formal status is:

```text
CLOUD_COMPLETION=SUPPORTED_AS_CANDIDATE_ONLY
FULL_AUTHORITY=NEVER
ALLOW_ONLY_TFS=REQUIRED
REAL_LLM_CALL=NO
CANONICAL_PROMOTION=NOT_PERFORMED
```
