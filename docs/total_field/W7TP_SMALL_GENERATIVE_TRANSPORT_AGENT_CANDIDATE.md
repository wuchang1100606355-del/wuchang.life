# W7TP Small Generative Transport Agent Candidate

STATUS=CANDIDATE

## Purpose

This document defines an architecture candidate for a small W7TP generative-transport agent. It is not an implementation, an installed agent, an Active Canonical definition, or authority to change persistent state.

生成式傳輸是 protocol-native 8D intent-field packet：agent 只依 packet 所要求的 verification level，解析引用並重構必要的結果。L1、L2、L3 分別表示完整重構、等價重構與候選重構；L3 的結果必須交由本地狀態機裁決。

The agent must remain small by carrying capability declarations, references, verification instructions, and bounded adapters. A fixed package-size claim is intentionally not made. Any future size limit must be versioned, measured, and attached to evidence.

## Architecture boundary

The candidate consists of the following logical components:

- **Manifest reader**: validates agent identity, protocol compatibility, declared capabilities, size envelope, and evidence references.
- **Reference resolver**: resolves only exact, authorized references named by the packet and records resolution evidence.
- **Reconstruction coordinator**: invokes the declared L1, L2, or L3 behavior without redefining the packet protocol.
- **LLM adapter**: optionally proposes semantic interpretations through a declared input/output contract; its output is always candidate material.
- **Sovereign-privacy interface**: sends the minimal required evidence to the D6 privacy gate without exposing undeclared private material.
- **Generative-transport/router interface**: places generative-transport and routing references in D7 only.
- **Adjudication interface**: submits the candidate and evidence to D8 and accepts only `ALLOW`, `HOLD`, `BLOCK`, or `QUARANTINE`.
- **Gateway adapter**: uses one governed ingress/egress contract; it is not an alternate engine or a parallel authority path.
- **Verifier adapter**: validates reconstruction level, reference integrity, evidence binding, and the final decision before any eligible commit.

`D6 = Privacy`, `D7 = Generative Transport / Router References`, and `D8 = Adjudication`. D8 state must not be inserted into a D3 coordinate body.

## Candidate manifest contract

The manifest is declarative. Field names below are candidate interface names and do not create a schema or service:

| Field | Candidate meaning |
|---|---|
| `agent_ref` | Opaque identity reference for the agent package. |
| `agent_version` | Immutable version used for negotiation and evidence binding. |
| `protocol_versions` | Supported W7TP protocol versions. |
| `capability_refs` | Versioned capability references; absence means unsupported. |
| `reconstruction_modes` | Declared subset of L1, L2, and L3. |
| `input_contract_ref` | Contract for accepted intent-field packets. |
| `output_contract_ref` | Contract for candidate results and evidence. |
| `llm_adapter_ref` | Optional, versioned adapter contract; no implicit model is allowed. |
| `gateway_contract_ref` | Governed gateway contract used for pull and submit. |
| `verification_profile_ref` | Required verification level and verifier reference. |
| `artifact_size_bytes` | Package size accompanied by an evidence status. |
| `unpacked_size_bytes` | Expanded size accompanied by an evidence status. |
| `working_set_limit_bytes` | Declared resource ceiling accompanied by an evidence status. |
| `asset_fallback_policy_ref` | Versioned policy for exact, authorized asset references. |
| `eligibility_policy_ref` | Versioned installation-eligibility policy. |

All size values require one of `Measured`, `Assumed`, `Illustrative`, or `Unverified`, plus an `evidence_ref` when the status is `Measured`. This document supplies no size value.

## LLM adapter contract

The LLM adapter is optional and non-sovereign. It must declare `model_ref`, `model_version`, `prompt_ref`, `input_contract_ref`, `output_contract_ref`, and `evidence_ref`. It may translate an intent or propose candidate references, but it may not:

- alter a packet silently;
- create an authority decision;
- bypass D6 or D8;
- commit state;
- make the deterministic verifier depend on unrecorded model state.

An unavailable, incompatible, or unverifiable adapter results in `HOLD`; it does not activate an undeclared fallback model.

## Version negotiation

Negotiation compares the packet protocol version, manifest version, capability versions, gateway contract version, and verification profile version. The selected tuple must be recorded in evidence before reconstruction starts.

- An exact compatible tuple may continue.
- A declared backward-compatible tuple may continue only under its named compatibility profile.
- An unknown, ambiguous, or unsupported tuple returns `HOLD`.
- Negotiation must not rewrite either peer's declared version.

## Asset fallback

Asset fallback is a controlled exception for a packet that names an exact `asset_ref` and a permitted fallback policy. The gateway must verify authorization, scope, integrity evidence, provenance, and expiry before exposing the referenced material to reconstruction.

Fallback is denied when the reference is absent, broad, expired, unauthorized, or cannot meet the required verification level. A fallback result remains candidate material until D8 adjudication. The presence of an asset reference does not broaden agent capability or packet scope.

## Decision and commit flow

1. Validate the manifest and negotiate a compatible version tuple.
2. Validate the packet contract and resolve only its authorized references.
3. Produce a bounded L1, L2, or L3 reconstruction result and bind evidence.
4. Apply the D6 sovereign-privacy gate interface.
5. Record only generative-transport or routing references in D7.
6. Submit proposal and evidence to D8.
7. If and only if D8 returns `ALLOW`, expose the adjudicated committed result to the existing authority path.
8. For `HOLD`, `BLOCK`, or `QUARANTINE`, preserve the previous committed state.

ALLOW_ONLY_COMMIT=YES

The agent itself never becomes the committing authority. It must not write a database, change a router, deploy, restart, or modify Active Canonical or Pointer state.

## Installation eligibility

An agent is eligible for human-reviewed installation only when all of the following are evidenced:

- manifest authenticity and immutable version identity;
- compatible protocol and gateway contracts;
- explicit capability allowlist;
- declared package and working-set measurements;
- D6, D7, and D8 interface conformance;
- verifier availability and deterministic replay for deterministic portions;
- controlled asset-fallback policy;
- revocation and expiry handling;
- no undeclared network, storage, model, or authority dependency.

Eligibility is not installation approval. Missing or stale evidence yields `HOLD`.

## Evidence requirements

Each run must bind the manifest version, negotiated version tuple, packet reference, resolved references, reconstruction mode, verification profile, fallback use, D6 result reference, D7 reference set, D8 decision, and verifier result. Claims without cited evidence remain `Unverified` and cannot establish installation eligibility.

## Open problems

- Package-size and working-set thresholds have not been selected.
- Capability negotiation and revocation profiles require formal contracts.
- The controlled asset channel and provenance verifier are not implemented here.
- Cross-version equivalence criteria require proof and test vectors.
- Agent packaging, sandboxing, and installation approval remain separate work.

CANONICAL_WRITE=NO
DB_WRITE=NO
DEPLOY=NO
RESTART=NO
