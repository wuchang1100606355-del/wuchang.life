# Technology identity manifest contract

## Applicability

Declare `technology_identity_contract` when a skill compares technologies, claims technical sameness or superiority, distinguishes W7TP from another mechanism, asserts structural elimination, or prepares intellectual-property evidence. The contract remains candidate-only and read-only unless a separately governed effect applies.

## Fixed contract

Bind the installed gate as `w7tp.technology-identity-audit@1.0.0`. Require exactly these axes:

1. `MECHANISM`
2. `CAUSAL_PATH`
3. `DEPENDENCIES`
4. `ELIMINATED_OPERATIONS`
5. `COST_TOPOLOGY`
6. `CARRIER_RECONSTRUCTION_VERIFICATION`

Allow exactly these candidate decisions:

- `SAME_MECHANISM`
- `PARTIAL_MECHANISM_OVERLAP`
- `EFFECT_ONLY_EQUIVALENT`
- `DIFFERENT_TECHNOLOGY`
- `INSUFFICIENT_EVIDENCE`

Use exactly `EV0_UNSUPPORTED`, `EV1_ASSERTION`, `EV2_SECONDARY_SOURCE`, `EV3_PRIMARY_DOCUMENT`, `EV4_IMPLEMENTATION_EVIDENCE`, and `EV5_REPRODUCIBLE_CAUSAL_EVIDENCE` as the evidence scale.

Require `effect_equivalence_not_technical_equivalence=true`, `weighted_score_forbidden=true`, `carrier_protocol_separation_required=true`, and `patentability_inference_forbidden=true`.

## Failure behavior

Return HOLD when any required axis is absent, an undeclared decision or evidence level appears, a weighted identity score is requested, carrier and reconstruction semantics are collapsed, or a patent/legal conclusion is inferred from the gate. Preserve all existing skills and evidence unchanged.
