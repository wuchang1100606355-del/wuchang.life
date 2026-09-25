# XiaoJ Sovereign Agent Candidate

STATUS=CANDIDATE

## Purpose and authority

小J is defined here as a candidate sovereign-agent architecture with two logical LLM layers and governed pull/submit entrypoints. This document does not create an agent, service, model endpoint, database authority, deployment, or commit path.

XIAOJ_AUTHORITY=CANDIDATE_ONLY

小J may interpret, translate, and package a proposal. It may not make a sovereign commit decision. Every proposal and every adjudication outcome returns through the governed Total Field path.

## Two-layer LLM architecture

### Semantic Translation Layer

The Semantic Translation Layer converts authorized user intent and referenced context into a structured candidate expression. It must:

- operate only on the minimum authorized context;
- preserve the original intent reference and provenance;
- declare model, prompt, contract, and version references;
- mark uncertainty and unresolved references explicitly;
- produce no authority state and no direct side effect.

### Sovereign Review Layer

The Sovereign Review Layer evaluates whether the candidate is sufficiently bounded for submission. It checks intent fidelity, privacy boundaries, missing evidence, contract compatibility, and prohibited authority requests. Its result is a review proposal, not a D8 decision.

The two layers must have separate input/output evidence. The second layer must not erase, rewrite, or conceal uncertainty produced by the first. A disagreement, unverifiable model state, or contract mismatch yields `HOLD` for submission.

## Pull candidate entrypoint

`pull` is a candidate gateway operation for acquiring only authorized references required by a named task. Its request contract must include:

- `request_ref` and `intent_ref`;
- requesting sovereign identity reference;
- exact context and capability references;
- purpose and scope constraints;
- privacy-policy and expiry references;
- expected response contract and version.

The gateway validates scope before returning minimal referenced context. Missing authority, ambiguous scope, incompatible version, or unavailable evidence returns a bounded error and no expanded context.

## Submit candidate entrypoint

`submit` is a candidate gateway operation for sending a structured proposal and its evidence to the Total Field process. Its request contract must include:

- source `request_ref` and `intent_ref`;
- candidate expression reference;
- both LLM-layer evidence references;
- schema and validator references;
- D6 privacy evidence reference;
- D7 generative-transport or routing references, when applicable;
- requested verification profile and version tuple.

Submission does not imply acceptance or commit. The gateway validates the envelope, forwards it to the existing adjudication path, and returns the resulting `ALLOW`, `HOLD`, `BLOCK`, or `QUARANTINE` outcome with its evidence reference.

## Unified return to Total Field

All paths converge on the same governed Total Field ingress:

1. Pull only authorized references.
2. Produce a Semantic Translation Layer proposal.
3. Produce a Sovereign Review Layer proposal.
4. Validate contracts and bind evidence.
5. Apply the D6 privacy gate interface.
6. Keep generative-transport and routing references in D7 only.
7. Submit to D8 adjudication through the governed gateway.
8. Return the decision and evidence to the Total Field path.

There is no alternate XiaoJ commit channel. Only D8 `ALLOW` may permit the existing authority path to commit. `HOLD`, `BLOCK`, and `QUARANTINE` preserve the previous committed state.

ALLOW_ONLY_COMMIT=YES

## Candidate-only boundaries

小J must not:

- write a D8 decision into a D3 coordinate body;
- treat LLM output as verified truth;
- commit or mutate persistent state;
- write a database or router configuration;
- deploy, restart, promote, or modify Active Canonical or Pointer state;
- create a parallel adjudication engine or bypass an existing gateway;
- expose raw private context beyond the authorized reference scope.

The LLM layers are replaceable candidate adapters. Deterministic checks must use recorded inputs, versioned contracts, and explicit evidence rather than hidden model state.

## Error model

| Error class | Required candidate outcome |
|---|---|
| Missing or expired authorization | `BLOCK` submission and disclose no additional context. |
| Ambiguous intent or unresolved reference | `HOLD` pending explicit resolution. |
| Sensitive material outside declared scope | `QUARANTINE` with minimal evidence reference. |
| Contract or version mismatch | `HOLD` with the incompatible references. |
| LLM-layer disagreement | `HOLD` and preserve both layer outputs as evidence. |
| Verifier failure | `BLOCK` candidate progression. |

These mappings are candidate interface guidance and do not replace D8 adjudication policy.

## Verification criteria

A future verifier should confirm:

- pull never returns context beyond explicit authorized references;
- submit always includes both layer evidence references;
- identical recorded deterministic inputs produce identical deterministic envelope fields;
- LLM uncertainty survives translation and review;
- all outcomes return through the same governed Total Field path;
- only `ALLOW` can reach the existing commit authority;
- no direct database, router, deployment, restart, Canonical, or Pointer action exists.

## Open problems

- Formal pull and submit schemas are not defined here.
- Model and prompt governance, revocation, and reproducibility profiles remain open.
- Human escalation and consent-renewal policy require a separate decision.
- Total Field ingress implementation and authentication are outside this candidate.
- Cross-model semantic equivalence requires evidence and evaluation criteria.

CANONICAL_WRITE=NO
DB_WRITE=NO
DEPLOY=NO
RESTART=NO
