# Technology identity comparison contract

## Input shape

Provide one JSON object:

```json
{
  "schema_version": "technology-identity-gate/1.0",
  "comparison_id": "opaque-comparison-ref",
  "technology_a": "Technology A",
  "technology_b": "Technology B",
  "observable_effect_relation": "SAME",
  "axes": {
    "MECHANISM": {
      "relation": "DIFFERENT",
      "evidence_level": "EV4_IMPLEMENTATION_EVIDENCE",
      "evidence_refs": ["source://implementation/a", "source://implementation/b"],
      "finding": "The causal mechanism differs despite the same visible output."
    }
  }
}
```

Require exactly six axis objects: `MECHANISM`, `CAUSAL_PATH`, `DEPENDENCIES`, `ELIMINATED_OPERATIONS`, `COST_TOPOLOGY`, and `CARRIER_RECONSTRUCTION_VERIFICATION`.

Each axis uses one relation: `SAME`, `PARTIAL`, `DIFFERENT`, or `UNKNOWN`. Each axis uses one evidence label from `EV0_UNSUPPORTED` through `EV5_REPRODUCIBLE_CAUSAL_EVIDENCE`. `EV1` or higher requires at least one non-empty evidence reference. A finding is required and must describe the bounded relation without a legal conclusion.

## Evidence semantics

| Label | Meaning |
|---|---|
| `EV0_UNSUPPORTED` | No usable evidence; assertion remains unknown |
| `EV1_ASSERTION` | A party or model stated the claim without independent support |
| `EV2_SECONDARY_SOURCE` | A secondary technical description supports the claim |
| `EV3_PRIMARY_DOCUMENT` | A primary specification, official document, or canonical source supports the claim |
| `EV4_IMPLEMENTATION_EVIDENCE` | Source, runtime structure, test, or implementation evidence supports the causal claim |
| `EV5_REPRODUCIBLE_CAUSAL_EVIDENCE` | A reproducible test demonstrates the mechanism and causal path |

Evidence maturity is discrete. Do not convert labels into weights, averages, percentages, distances, or model confidence.

## Decision rules

1. Return `SAME_MECHANISM` only when all six axes are `SAME` and every axis is at least `EV3_PRIMARY_DOCUMENT`.
2. Return `EFFECT_ONLY_EQUIVALENT` when the observable effect is `SAME` and at least one axis is `DIFFERENT` with EV3-or-stronger evidence.
3. Return `DIFFERENT_TECHNOLOGY` when the observable effect is not `SAME` and at least one axis is `DIFFERENT` with EV3-or-stronger evidence.
4. Return `PARTIAL_MECHANISM_OVERLAP` when no strongly evidenced difference exists, at least one axis is `PARTIAL`, and every axis is known with EV2-or-stronger evidence.
5. Otherwise return `INSUFFICIENT_EVIDENCE`.

A strongly evidenced difference on one causal axis prevents `SAME_MECHANISM`. The aggregator is conservative and deterministic; it does not decide which source is legally controlling.

## Structural elimination rule

Treat an operation as structurally eliminated only when evidence shows that the operation is absent from the required causal path and no equivalent dependency performs it elsewhere. Speeding it up, moving it, caching it, batching it, reducing its frequency, or making it probabilistic is optimization, not elimination.

## Carrier and verification rule

Compare carrier/protocol separately from reconstruction and verification semantics. A shared carrier cannot prove shared technical identity. Separate post-hoc result comparison, integrity verification, identity verification, authority verification, envelope verification, and packet-carried verification. Eliminating one category never implies eliminating all categories.

## Intellectual-property boundary

Return no patentability, novelty, inventive-step, infringement, validity, ownership, authorship, or legal-status conclusion. A gate decision may become evidence for a separate audit, but it cannot replace prior-art searching, claim construction, jurisdiction-specific law, or an official receipt.
