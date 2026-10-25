# Total Field skill definition contract

## Definition

A Total Field skill is a versioned, identity-bound product capability whose inputs, outputs, information scope, effect boundary, D1-D8 projections, red-team obligations, verification, and lifecycle are declared in a machine-readable manifest. A skill is not merely a prompt, model, script, extension, API, endpoint, container, job, or human procedure.

## Mandatory invariants

1. **Product first:** define intended user, need, product outcome, deliverables, interface behavior, quality thresholds, acceptance criteria, failure behavior, prohibited outputs, and allowed side effects.
2. **Identity before context:** require a valid member-bound XiaoJ identity, fixed role Seat, and canonical access profile before opening dynamic context.
3. **Information is not authority:** broad identity-authorized D1-D8 read access does not grant write, execution, seal, or decision authority.
4. **Candidate boundary:** LLMs and skill components produce candidates or evidence. They never emit authoritative ALLOW, committed state, TFS, TFID, canonical pointer, or final seal.
5. **Eight state fields:** map D1 intent, D2 state, D3 coordinate, D4 evidence, D5 execution/policy, D6 generative transmission, D7 red-team confinement, and D8 envelope/authority. Identity is a full-envelope precondition, not D1.
6. **Red-team procedure:** definition, activation, and state-changing operation each have an applicable non-skippable red-team stage.
7. **Natural-language HOLD:** every pause has a safe direct resolution and, when appropriate, a bounded authorization request.
8. **Evidence before claim:** source, manifest, dependency, execution, output, and receipt claims must be hash- or evidence-bound.
9. **No inferred promotion:** install, test, canary, provider success, or human intent does not replace a D8 decision.
10. **Retirement safety:** suspension and retirement preserve evidence, revoke sessions, and never delete pre-existing business or member data.
11. **Technology identity before comparison:** effect equivalence is not technical equivalence. Compare mechanism, causal path, dependencies, eliminated operations, cost topology, and carrier/reconstruction/verification semantics before returning a technology-identity candidate.

## Canonical V2.1 locks

Bind W7TP-governed skills to `docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md`; the previous V2 locator and its hash are historical evidence only.

1. Define W7TP as Intent Communication / State-Field Packet Communication（意圖通訊／狀態場封包通訊）, not semantic communication（語意通信）.
2. Define ADI’s packet-level irreversible local decision index separately from its system-level lineage/logical-time/state-transition/namespace/evidence spatial-temporal index network. Preserve `5D_INTEGER_METRIC` where the active canonical declares it.
3. When continuous computation is declared, define a third coordinated floating-point data index separately from both authority-bearing domains. Treat it as data and candidate evidence only, never packet identity, lineage, or decision authority.
4. Bind every floating-point data index to representation, precision, scale or unit, coordinate basis, rounding, canonical serialization, absolute and relative tolerances, NaN/infinity/subnormal/signed-zero policies, declared operations, data references, and deterministic replay evidence.
5. Keep H64-TD, its codebook, mappings, and recovery material reference-only; never reconstruct, derive, copy, embed, or disclose them.
6. For patent-package skills, treat the current 10 claims as active and V04’s 21-claim draft as superseded history. Bind TIPO application 115127138 legal status only to the official receipt.
7. Record historical state append-only or as a new packet. Never silently overwrite manifests, packets, receipts, lineage, decision indexes, claim states, or canonical state.

## Technology identity lock

Require `technology_identity_contract` whenever a skill compares technologies, claims sameness or superiority, distinguishes W7TP from another mechanism, asserts that an operation or cost has been structurally eliminated, or prepares intellectual-property evidence.

The six axes are `MECHANISM`, `CAUSAL_PATH`, `DEPENDENCIES`, `ELIMINATED_OPERATIONS`, `COST_TOPOLOGY`, and `CARRIER_RECONSTRUCTION_VERIFICATION`. Use only `SAME_MECHANISM`, `PARTIAL_MECHANISM_OVERLAP`, `EFFECT_ONLY_EQUIVALENT`, `DIFFERENT_TECHNOLOGY`, or `INSUFFICIENT_EVIDENCE` as the candidate decision. Use `EV0_UNSUPPORTED` through `EV5_REPRODUCIBLE_CAUSAL_EVIDENCE` for evidence maturity; never reuse E0-E5 effect classes as evidence levels.

Forbid weighted identity scores. A deterministic decision may aggregate declared axis relations and evidence classes, but it may not manufacture a continuous similarity value or promote float-derived data into identity or authority. Preserve the distinction between structural elimination and ordinary optimization. Preserve carrier/protocol semantics separately from reconstruction and verification semantics.

A technology-identity decision never proves novelty, patentability, infringement, validity, legal status, or global superiority. Those conclusions require separately scoped, source-grounded research and the applicable formal authority.

## Protected information

Never place credential material, raw member plaintext, raw audio, ADI content, H64-TD codebooks, mappings, or recovery material, payment secrets, or cross-member plaintext in LLM context or a skill manifest. Use references, handles, typed claims, hashes, counts, schema, structural metadata, or de-identified evidence.

A provider-backed operation uses a brokered capability. The provider sees only the sanitized request allowed by the active profile and returns candidate material through the Total Field receiver.

## Skill identity

Use a stable `skill_id` independent of display name, model, provider, and installation path. Bind each version to:

```text
skill_id
version
manifest_sha256
implementation_refs[]
implementation_sha256{}
canonical_refs[]
schema_refs[]
supersedes[]
```

A changed authority boundary, effect class, protected-data rule, product output, canonical binding, or D1-D8 contract requires a new version and Total Field review. Preserve every replaced version and receipt append-only. Cosmetic wording may use the active minor-version policy only when it cannot change behavior.

## Skill content domains

Every manifest contains these domains:

- `identity_and_seat`
- `product_output_contract`
- `classification`
- `information_context`
- `d1_d8_projection`
- `authority_boundary`
- `execution_contract`
- `w7tp_contract`
- `red_team_contract`
- `hold_contract`
- `authorization_contract`
- `verification_contract`
- `lifecycle`
- `evidence_and_hashes`

The JSON Schema defines their required machine shape. The manifest explanation and member-facing dialogue remain Traditional Chinese unless the user explicitly requests another language.
