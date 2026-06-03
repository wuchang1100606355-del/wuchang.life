# W7TP Eastern State Router v1.3 Specification

Status: Specification only  
Location class: Algorithm specification  
Runtime report boundary: `runtime/reports/` is reserved for execution reports and evidence outputs only.

## Summary

W7TP Eastern State Router v1.3 defines a deterministic routing specification for converting observed eastern-state signals into reviewable W7TP task states, routing bands, and governance outcomes.

This document is not executable code. It does not define service startup behavior, database mutation, container control, or product implementation. Its purpose is to preserve the algorithm contract before any future implementation work.

## Document Boundary

- This file belongs under `docs/w7tp_algorithms/` because it describes algorithm rules.
- Execution reports, smoke results, runtime evidence, and generated outputs belong under `runtime/reports/`.
- Runtime dead-letter artifacts belong under `runtime/dead_letter/`.
- Evidence bundles and proof material belong under `runtime/evidence/` or the existing proof/evidence lane selected by the operator.

## Router Purpose

The Eastern State Router classifies a task or event into a stable operational state before action is taken. It is intended to reduce ambiguity between:

- observation
- interpretation
- routing
- approval
- execution readiness
- post-action evidence

The router should make the state transition legible enough for human review and strict enough for later automation.

## Inputs

The router accepts normalized state observations. Each observation should include:

- source identity
- event timestamp
- domain label
- intent label
- risk signal
- evidence reference
- requested action class
- current approval state
- prior state reference, when available

Inputs must not require secret material. The router must not depend on reading `.env`, tokens, passwords, private keys, or raw credential stores.

## Eastern State Bands

The v1.3 router uses the following state bands:

| Band | Name | Meaning |
| --- | --- | --- |
| E0 | Observed | Signal exists but has not been interpreted. |
| E1 | Interpreted | Signal has a normalized intent and domain. |
| E2 | Routed | Signal has a proposed W7TP route and risk band. |
| E3 | Gated | Route requires approval, review, or additional evidence. |
| E4 | Ready | Route is approved for the next safe non-destructive step. |
| E5 | Executed | Approved step has run and produced evidence. |
| E6 | Closed | Evidence has been reviewed and closure is recorded. |
| EX | Rejected | Signal is invalid, unsafe, duplicate, or outside scope. |

## Routing Dimensions

Each routing decision should record four dimensions:

- State band: current eastern-state band.
- Domain: affected system area, such as docs, runtime, Odoo, gateway, governance, or evidence.
- Risk band: operational risk level for the next step.
- Action class: read-only, documentation-only, candidate-write, runtime-write, service-control, database-write, or external-publication.

## Risk Bands

The router should align with existing W7TP governance language:

| Risk | Meaning | Default Handling |
| --- | --- | --- |
| L0 | Read-only observation | Allowed when within scope. |
| L1 | Documentation or report write | Allowed when target lane is correct. |
| L2 | Candidate source write | Requires explicit scope and review lane. |
| L3 | Runtime, service, database, credential, or public action | Requires explicit operator approval and evidence plan. |

## Deterministic Routing Rules

The router should apply rules in this order:

1. Reject any request that requires secret reads unless explicitly authorized by a separate governance step.
2. Classify the target lane before classifying action.
3. If the target is `runtime/reports/`, only execution reports and generated evidence summaries are valid.
4. If the target is `docs/w7tp_algorithms/`, only algorithm specifications, contracts, diagrams, and review notes are valid.
5. If the target is live Odoo, database state, running containers, or service process control, classify as L3.
6. If the event has no evidence reference and requests execution, route to E3 Gated.
7. If the event is documentation-only and target lane is correct, route to E4 Ready.
8. If an approved action runs and produces evidence, route to E5 Executed.
9. If evidence is reviewed and no follow-up remains, route to E6 Closed.
10. If the request is duplicate, stale, or lane-invalid, route to EX Rejected or E3 Gated depending on recoverability.

## Output Record

Every routing decision should be expressible as a compact record containing:

- router version
- input event identifier
- normalized intent
- target lane
- state band
- risk band
- action class
- decision
- required approval, if any
- evidence reference
- next safe step

The output record is a specification concept only. This document does not define a storage schema or executable serialization format.

## Lane Policy

The router must preserve the distinction between documentation, reports, evidence, and runtime state:

- `docs/w7tp_specs/`: system and product specifications.
- `docs/w7tp_algorithms/`: algorithm specifications and deterministic routing contracts.
- `docs/w7tp_posters/`: presentation/poster-facing summaries.
- `runtime/reports/`: execution reports, readiness scans, smoke reports, generated observations.
- `runtime/evidence/`: evidence artifacts selected for retention.
- `runtime/dead_letter/`: failed, rejected, or deferred runtime/event artifacts.

## PortDetector Handling

If VSCode PortDetector or a language-server process fails, the router should classify it as an environment-readiness signal, not as application failure by default.

Recommended state:

- State band: E1 Interpreted
- Domain: local development environment
- Risk band: L0 for read-only diagnosis, L3 for restart or process control
- Default next safe step: read-only health mapping before any service action

## Governance Constraints

The router must not imply permission to:

- restart services
- kill processes
- modify Odoo database state
- read secrets
- publish externally
- commit changes
- promote candidate code into runtime paths

Those actions remain outside this specification unless separately approved.

## Version Notes

Version 1.3 clarifies lane separation:

- Algorithm specifications belong in `docs/w7tp_algorithms/`.
- Execution reports belong in `runtime/reports/`.
- Environment findings can be summarized in reports, but durable algorithm rules should not be stored there.

## Recommended Next Review

Before implementation, review this specification against:

- existing W7TP governance documents
- active gateway routing expectations
- runtime evidence retention policy
- Odoo and service-control approval boundaries

Implementation should remain blocked until an operator explicitly approves a separate implementation task.
