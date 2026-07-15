# TFCT Living Lab Demo Candidate

STATUS=CANDIDATE

## Purpose

This document defines four bounded Living Lab demonstration scenarios. It is a candidate demonstration design, not production evidence, deployment authority, Canonical promotion, or a performance guarantee.

Evidence labels used by this document are restricted to:

- `Measured`: observed under a cited protocol and linked to an evidence reference.
- `Assumed`: an explicit design assumption that still requires validation.
- `Illustrative`: a value or outcome used only to explain the demonstration.
- `Unverified`: a claim or value for which acceptable evidence is not available.

The symbols 8D, D3, D6, D7, and D8 are field identifiers, not measurement claims.

## Shared demonstration controls

Every scenario uses synthetic or explicitly consented data, immutable scenario inputs, a declared verification profile, and a resettable local demonstration state. Each observed value must carry an evidence label and, when `Measured`, an `evidence_ref` identifying method, environment, and raw result. Missing evidence is represented as `Unverified`, never silently promoted.

No scenario writes an Active Canonical or Pointer, modifies a database or router, deploys, restarts, or creates a production authority path. D3 remains a coordinate proposal; D6 is the privacy gate; D7 contains generative-transport or routing references only; D8 returns `ALLOW`, `HOLD`, `BLOCK`, or `QUARANTINE`. Only `ALLOW` may permit the existing authority path to commit.

## Scenario Alpha — W7TP Generative Transport

**Goal:** Demonstrate a manifest-governed small agent resolving exact references and reconstructing only the result required by a protocol-native 8D intent-field packet.

**Flow:**

- Validate the candidate agent manifest, capabilities, version tuple, size evidence, and eligibility evidence.
- Resolve only authorized references named by the packet.
- Select the declared L1, L2, or L3 reconstruction level and bind its verifier evidence.
- If a required exact asset reference cannot be reconstructed, apply only its controlled asset-fallback policy.
- Keep generative-transport and routing references in D7 and submit the result through the governed gateway and D8 path.
- Preserve the previous committed state unless D8 returns `ALLOW`.

**Displayed evidence:** manifest identity, negotiated versions, referenced capabilities, reconstruction level, fallback status, verifier result, D8 decision, and previous-state preservation.

**Performance-claim register:** `Unverified — 2435x`. No acceptable cited protocol, baseline, environment, or result is supplied here; the value must not be displayed as measured performance or used for product qualification.

## Scenario Beta — TRUE8D Convergence & Adjudication

**Goal:** Demonstrate candidate projection, bounded convergence checks, and adjudication while preserving the distinct semantics of D3, D6, D7, and D8.

**Flow:**

- Provide identical immutable event, observation, rule, and policy references to each isolated demonstration run.
- Produce a pure D3 coordinate proposal without embedding the D8 decision.
- Apply the D6 privacy gate and keep only generative-transport or routing references in D7.
- Record the fixed-point status as a candidate observation without claiming existence, uniqueness, finite convergence, or cross-node consensus.
- Submit to D8 and demonstrate `ALLOW`, `HOLD`, `BLOCK`, and `QUARANTINE` behavior.
- Confirm that only `ALLOW` permits the existing authority path to commit; every other decision preserves the prior committed state.

**Displayed evidence:** input identity, version tuple, proposal replay, fixed-point status, privacy result reference, D7 references, D8 decision, commit flag, and unresolved divergence. Any uncited outcome is `Illustrative` or `Unverified`.

## Scenario Gamma — Optical Edge Sovereignty

**Goal:** Demonstrate sovereign handling of synthetic optical observations at a bounded edge context without treating model output as authority or exposing undeclared source observations.

**Flow:**

- Use synthetic optical observation references and an explicit consent and retention policy reference.
- Keep raw observations inside the declared edge boundary; expose only the minimum authorized evidence references.
- Treat any model or XiaoJ interpretation as candidate material with model, prompt, and contract versions.
- Apply D6 before emitting D7 references and submit the proposal to D8 through the governed Total Field path.
- Preserve raw-observation confidentiality and the previous committed state for every non-`ALLOW` result.

**Displayed evidence:** source authorization, edge-boundary policy, model and prompt references, privacy result, minimal evidence disclosure, adjudication result, and retention outcome.

**Performance-claim register:** `Unverified — Deepfake detection rate`. No evidence-backed percentage, test corpus, baseline, environment, or independent verification is supplied here. Optical-defense effectiveness therefore remains an open claim and cannot be presented as production performance.

## Scenario Delta — TFS Consistency

**Goal:** Demonstrate comparison of candidate Total Field State references across replayed and isolated runs without claiming a proven consensus protocol or creating a new TFS authority.

**Flow:**

- Bind each run to the same immutable event, Observation Domain, dimension, constraint, convergence, priority-policy, and verifier references.
- Compare candidate fixed-point status and verification evidence before adjudication.
- For an `ALLOW` outcome, compare only the state reference, TFID, and Total Field integrity reference exposed by the existing authority path.
- For `HOLD`, `BLOCK`, or `QUARANTINE`, confirm that no new TFS is produced and the previous committed state is preserved.
- Report any replay or cross-node mismatch as unresolved evidence; do not infer consistency from partial agreement.

**Displayed evidence:** complete input-reference tuple, fixed-point status, verifier result, D8 decision, commit flag, state reference, TFID reference, Total Field integrity reference, and mismatch details. No node count, latency, convergence bound, or success rate is claimed.

## Measurement and claim policy

A demo record may use `Measured` only when it provides:

- an immutable scenario and environment reference;
- a measurement method and baseline reference;
- the observed value, unit, sample definition, and uncertainty treatment;
- a verifier or reviewer reference;
- a timestamp in evidence metadata, never as deterministic-core input.

`Assumed`, `Illustrative`, and `Unverified` values must remain visibly labeled in every table, chart, export, and presentation. A label may not be removed through aggregation. Optical-defense, throughput, compression, latency, scale, accuracy, energy, or multiplier claims without acceptable evidence remain `Unverified`.

## Acceptance gates for a future demo

- Scenario inputs contain no raw private production data.
- Replay uses identical immutable references and reports mismatch without concealment.
- D8 decision fields remain outside the D3 coordinate body.
- D7 contains references only.
- Only `ALLOW` can reach the existing commit authority.
- All numerical performance claims carry one allowed evidence label.
- No demo outcome is represented as production proof or Canonical authority.

## Open problems

- Observation Domain completeness and projection criteria are unresolved.
- Fixed-point existence, uniqueness, finite convergence, and cross-node equivalence are not proven.
- Formal consensus, identity generation, and Total Field integrity contracts are absent.
- Small-agent packaging, gateway, asset fallback, and installation eligibility are not implemented here.
- XiaoJ model governance and reproducibility profiles remain candidates.
- Performance and optical-defense claims require independent, citable protocols and evidence.

CANONICAL_WRITE=NO
DB_WRITE=NO
DEPLOY=NO
RESTART=NO
ROUTER_WRITE=NO
