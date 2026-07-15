# ADI Index Strategy Candidate

STATUS=CANDIDATE

## Definition

ADI is a candidate **Representation / Index Strategy** for producing a deterministic, evidence-bound ordering or reference set over an explicitly declared representation space.

ADI_IS_D3=NO

ADI is not D3, not a coordinate proposal, not a state-transition engine, not an adjudicator, and not a substitute for any TRUE8D field. A consumer may reference an ADI result only through an explicit, versioned interface. The consumer remains responsible for its own field semantics and authority checks.

## Candidate contract

The following opaque references define an ADI invocation without selecting their algorithms:

| Field | Required meaning |
|---|---|
| `strategy_ref` | Immutable identity of the ADI strategy contract. |
| `strategy_version` | Exact contract version. |
| `representation_ref` | Versioned representation and normalization contract. |
| `observation_set_ref` | Exact bounded input-set reference. |
| `metric_ref` | Versioned distance or similarity contract. |
| `topology_ref` | Versioned neighborhood or connectivity contract. |
| `quantization_ref` | Versioned precision, boundary, and rounding contract. |
| `tie_break_ref` | Versioned total-order rule for equal scores. |
| `determinism_profile_ref` | Canonicalization and replay requirements. |
| `verifier_ref` | Verifier identity and version. |
| `evidence_ref` | Evidence binding for inputs, selected contracts, and output. |

No implicit default is allowed for metric, topology, quantization, tie-break, version, or verifier. If any required reference is absent, ambiguous, mutable, or unsupported, evaluation returns `HOLD` and no index result is authoritative.

## Candidate output

An ADI result contains only:

- the exact input and contract references;
- an ordered set of candidate references or index entries;
- declared score representations when permitted by the metric contract;
- tie-break evidence;
- verifier result and evidence reference;
- candidate status.

It must not contain a D3 coordinate body, D8 authority decision, committed state, or an instruction to mutate another field. Downstream use requires a separate explicit mapping contract.

## Determinism requirements

A conforming future implementation must satisfy all of the following under its declared determinism profile:

- identical normalized inputs and identical versioned references produce an identical ordered output;
- input map order and other semantically unordered presentation details do not affect the result;
- quantization boundaries and rounding behavior are explicit;
- tied values are resolved only by `tie_break_ref`;
- unsupported numeric values and non-canonical representations are rejected;
- all external data is addressed by immutable evidence references;
- no current time, random value, hidden model state, or unversioned external state affects evaluation.

Determinism applies only after every referenced contract has been formally specified. This document does not claim that such specifications or an implementation presently exist.

## Verifier contract

A future verifier must be able to:

- validate the presence and immutability of all required references;
- resolve the exact contract versions under an authorized evidence policy;
- recompute normalization, metric representation, quantization, ordering, and tie-break behavior;
- replay an invocation and compare the complete ordered output;
- reject missing references, unsupported versions, illegal numeric values, and unexplained ties;
- confirm that the output contains no D3 coordinate body, D8 decision, or committed-state mutation.

The verifier result is evidence, not a sovereign commit decision.

## Relationship to TRUE8D and W7TP

ADI may supply a bounded candidate reference set to an explicitly declared consumer. It cannot silently populate or replace D3. When an ADI result is carried by W7TP, the packet carries the necessary references, verification requirement, and reconstruction intent; D7 remains limited to generative-transport or routing references, while D8 remains the adjudication authority.

Only D8 `ALLOW` may permit the existing authority path to commit a downstream proposal. `HOLD`, `BLOCK`, and `QUARANTINE` preserve the previous committed state.

## Excluded mechanisms

This candidate introduces no external symbolic-placement, calendrical-position, directional-divination, or star-cycle rule. No such rule may be inferred from the word “index.” Adding any unrelated rule family would require a separate explicit proposal and is outside this candidate.

## Open problems

- The representation and normalization contract is unspecified.
- The metric and its domain-validity conditions are unspecified.
- The topology and neighborhood semantics are unspecified.
- Quantization precision, boundary behavior, and error bounds are unspecified.
- A total deterministic tie-break rule is unspecified.
- Version compatibility and migration rules are unspecified.
- Collision handling, incomplete observations, and stability criteria require formal definitions.
- The verifier, proof obligations, and conformance vectors are not implemented here.
- The relation between an ADI result and any future consumer requires an explicit mapping contract.

CANONICAL_WRITE=NO
DB_WRITE=NO
DEPLOY=NO
RESTART=NO
