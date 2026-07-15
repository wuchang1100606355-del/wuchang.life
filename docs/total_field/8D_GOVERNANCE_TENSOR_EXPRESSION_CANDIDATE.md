# 8D Governance Tensor Expression Candidate Specification

Short name: `8D-GTE`

Status: `CANDIDATE_SPEC_ONLY`

Run ID: `TFCT_TRUE8D_W7TP_8DGTE_SYSTEM_CONSOLIDATION_CANDIDATE_V0_1`

This document defines a candidate representation and component contract. It
does not implement a parser, command-line interface, validator, gateway, runtime,
or second engine. It is not an Active Canonical document and does not itself
create or commit a Total Field State (TFS).

## 1. Purpose and semantic boundary

An 8D-GTE is a versioned governance expression that binds an event reference,
an opaque Observation Domain reference, eight dimension references, constraint
and convergence references, a lifecycle state, verification state, and an
optional committed TFS result.

The expression carries references and governance evidence; it does not embed an
ADI algorithm, deployment configuration, legacy dimension shape, or executable
model prompt. The adopted dimension boundary includes:

- D6: Privacy.
- D7: Generative Transmission & Resource Routing.
- D8: Red-Team Detour Alert & Quarantine.

Generative transmission is a protocol-native 8D intent-field packet. A receiver
reconstructs only what the packet requires, at the verification level the packet
requires. It is not file moving, synchronization, backup, download, or
decryption, and it does not make arbitrary existing files available through a
small packet.

## 2. Version and lifecycle

The candidate representation uses:

- `schema_version`: `8d-gte-candidate/0.1`
- `lifecycle`: exactly `CANDIDATE` or `COMMITTED`

An implementation must reject an unsupported `schema_version`. A later version
must not silently reinterpret an earlier document. Version conversion, if ever
authorized, requires an explicit converter with provenance and must be validated
again under the target schema.

## 3. Syntax elements

The JSON representation is a single closed object with these required members:

| Member | Type | Meaning |
|---|---|---|
| `schema_version` | string | Candidate representation version. |
| `lifecycle` | string | `CANDIDATE` or `COMMITTED`. |
| `event_ref` | non-empty string | Stable reference to the event; not an embedded event payload. |
| `observation_domain_ref` | non-empty string | Opaque reference to an Observation Domain. |
| `dimensions` | object | Exactly `D1_ref` through `D8_ref`, each a non-empty string. |
| `constraint_hypergraph_ref` | non-empty string | Versioned reference to the applicable Constraint Hypergraph. |
| `convergence_operator_ref` | non-empty string | Versioned reference to the convergence operator. |
| `priority_policy_ref` | non-empty string | Versioned reference to the Priority Policy. |
| `fixed_point_status` | string | `PENDING`, `REACHED`, `NOT_REACHED`, or `UNKNOWN`. |
| `verification` | object | Final governance decision and commit flag. |
| `tfs_result` | null or object | No result for candidates; committed TFS references for a valid commit. |

`verification` is a closed object with:

| Member | Type | Meaning |
|---|---|---|
| `final_decision` | string | `PENDING`, `ALLOW`, `HOLD`, `BLOCK`, or `QUARANTINE`. |
| `commit_applied` | boolean | Whether the proposed state was committed. |

When present as an object, `tfs_result` is closed and contains exactly these
non-empty string references:

- `state_ref`
- `tfid`
- `total_field_hash`

All reference strings are opaque to this schema. Their identifier algorithms,
resolution protocols, and trust roots remain outside this candidate.

## 4. Dimension semantics

The `dimensions` object carries references, not mutable dimension bodies.
Resolvers and consumers must preserve the adopted meanings of D1-D8. In
particular:

- `D6_ref` resolves only to Privacy policy/evidence appropriate to the sovereign
  privacy gate.
- `D7_ref` resolves only to generative-transmission or resource-routing
  references.
- `D8_ref` resolves only to Red-Team Detour Alert & Quarantine governance
  policy/evidence.

The D8 decision remains in `verification.final_decision`; it must not be copied
into a D3 coordinate body. `D6_gt`, `D7_risk`, `D8_envelope`, and
`D1_identity` through `D8_commit` are legacy names and are not valid 8D-GTE
dimension members.

## 5. Lifecycle invariants

### 5.1 `CANDIDATE`

A candidate expression must satisfy all of the following:

- `verification.final_decision` is one of `PENDING`, `HOLD`, `BLOCK`, or
  `QUARANTINE`.
- `verification.commit_applied` is `false`.
- `tfs_result` is `null`; a candidate cannot produce a new TFS.
- `fixed_point_status` may report the current evaluation state, but does not
  assert a convergence theorem.

### 5.2 `COMMITTED`

A committed expression must satisfy all of the following:

- `verification.final_decision` is `ALLOW`.
- `verification.commit_applied` is `true`.
- `fixed_point_status` is `REACHED`.
- `tfs_result` is an object containing `state_ref`, `tfid`, and
  `total_field_hash`.

Only `ALLOW` may commit. `HOLD`, `BLOCK`, and `QUARANTINE` preserve the prior
committed state and cannot be represented with lifecycle `COMMITTED`.

## 6. Required and prohibited content

Every member listed in Section 3 is required, including all eight dimension
references. Unknown top-level or nested members are prohibited.

The expression must not contain:

- ADI metric, topology, quantization, or tie-break algorithms;
- deployment names, hostnames, process commands, or environment configuration;
- runtime-private fields or executable instructions;
- legacy dimensions such as `D6_gt`, `D7_risk`, `D8_envelope`, or the
  `D1_identity` through `D8_commit` family;
- system-generated current time, random values, or implicit nondeterministic
  state;
- raw model prompts, unvalidated LLM extraction, credentials, secrets, or
  private payloads;
- an embedded D8 decision inside a D3 coordinate body.

`additionalProperties=false` at every represented object boundary is the schema
mechanism that enforces the closed shape.

## 7. Candidate component contracts

No component in this section is implemented by this specification.

### 7.1 Parser contract

A future parser may accept only the documented 8D-GTE representation. It must:

1. decode without executing content;
2. reject duplicate or unknown members;
3. preserve Unicode string values;
4. return either one structured expression or one stable parser error;
5. avoid current time, randomness, LLM interpretation, and external state in
   structural parsing.

There is no parser or CLI in this candidate deliverable.

### 7.2 Schema contract

The candidate JSON Schema is the structural and lifecycle gate. It must use JSON
Schema Draft 2020-12, require every Section 3 member, close every object with
`additionalProperties=false`, and encode the `CANDIDATE` and `COMMITTED`
invariants from Section 5.

Schema validity does not prove reference authenticity, mathematical convergence,
or authorization to commit.

### 7.3 Validator contract

A future semantic validator acts only after schema success. It must:

1. resolve each reference through an authorized resolver without mutating the
   submitted expression;
2. verify provenance and version compatibility;
3. verify dimension semantics, including the D6/D7/D8 boundary;
4. evaluate referenced constraints and priority policy;
5. verify fixed-point evidence without presenting an unproved theorem as fact;
6. verify that only `ALLOW` can produce a committed result;
7. return stable validation evidence or one stable failure code.

This specification supplies no resolver, policy evaluator, convergence proof, or
semantic validator implementation.

### 7.4 Submit Gateway contract

A future Submit Gateway must require parser, schema, and semantic-validation
success before admission. It must not promote a `CANDIDATE`, synthesize missing
references, or convert a non-`ALLOW` decision into a commit. Authentication,
authorization, replay protection, idempotency, audit evidence, and consensus are
required design topics but remain open. No route, service, or gateway is created
by this specification.

## 8. Total Field receiving flow

The candidate receiving sequence is:

1. Receive an expression as untrusted input.
2. Parse deterministically; stop on a parser error.
3. Validate against the matching versioned schema; stop on a structural or
   lifecycle error.
4. Resolve references under an authorized, provenance-preserving resolver; stop
   on an unresolved or unauthorized reference.
5. Evaluate the referenced Constraint Hypergraph and Priority Policy.
6. Verify fixed-point evidence and cross-node requirements when applicable.
7. Apply D6 Privacy, D7 reference, and D8 governance boundaries.
8. Admit a TFS result only when lifecycle is `COMMITTED`, decision is `ALLOW`,
   fixed point is `REACHED`, and all validation evidence succeeds.
9. Otherwise preserve the prior committed state and return evidence without a
   new TFS.

The flow is a contract, not an implementation or claim that every stage exists.

## 9. Error taxonomy

A conforming future component returns a stable code and no partial commit:

| Error code | Owner | Condition |
|---|---|---|
| `ERR_PARSE_INVALID` | Parser | Input cannot be decoded into one expression. |
| `ERR_DUPLICATE_MEMBER` | Parser | A member is repeated. |
| `ERR_SCHEMA_VERSION_UNSUPPORTED` | Parser/Schema | `schema_version` is unsupported. |
| `ERR_REQUIRED_MEMBER_MISSING` | Schema | A required member is absent. |
| `ERR_UNKNOWN_MEMBER` | Schema | A closed object contains an extra member. |
| `ERR_INVALID_REFERENCE_SHAPE` | Schema | A reference is empty or has the wrong type. |
| `ERR_LIFECYCLE_INVARIANT` | Schema | Lifecycle and verification/TFS fields disagree. |
| `ERR_CANDIDATE_COMMIT_FORBIDDEN` | Schema/Validator | A candidate requests or reports a commit. |
| `ERR_COMMITTED_REQUIRES_ALLOW` | Schema/Validator | A committed expression has a non-`ALLOW` decision. |
| `ERR_FIXED_POINT_REQUIRED` | Schema/Validator | A committed expression does not report `REACHED`. |
| `ERR_REFERENCE_UNRESOLVED` | Validator | An authorized resolver cannot resolve a reference. |
| `ERR_REFERENCE_UNAUTHORIZED` | Validator | Resolution or use is not authorized. |
| `ERR_DIMENSION_SEMANTIC_CONFLICT` | Validator | A dimension reference violates the adopted meaning. |
| `ERR_CONVERGENCE_UNVERIFIED` | Validator | Required fixed-point evidence cannot be verified. |
| `ERR_GATEWAY_ADMISSION_DENIED` | Gateway | Admission conditions are not satisfied. |

Failure at any stage must preserve the prior committed state. Error codes do not
grant commit authority.

## 10. Non-goals and open problems

This candidate does not define or implement:

- a parser, CLI, runtime, second transition engine, validator, resolver, or
  Submit Gateway;
- the complete Observation Domain;
- fixed-point existence, uniqueness, finite global convergence, or cross-node
  consistency proofs;
- a consensus protocol, TFID algorithm, or Total Field Hash contract;
- an ADI algorithm;
- canonical promotion, deployment, database writes, router writes, or process
  restarts.

`PARSER_IMPLEMENTED=NO`

`CLI_IMPLEMENTED=NO`

`CANONICAL_WRITE=NO`
