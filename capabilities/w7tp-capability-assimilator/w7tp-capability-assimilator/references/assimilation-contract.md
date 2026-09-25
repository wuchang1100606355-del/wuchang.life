# W7TP / 8D ADI assimilation contract

## 1. Capability abstraction

Represent an external capability as:

```text
Capability =
  Intent
+ Preconditions
+ Input Contract
+ State Transition
+ Output Contract
+ Evidence Contract
+ Failure Contract
+ Security Assumptions
+ Side-Effect Boundary
+ Acceptance Contract
```

The source implementation is one realization of this contract, not the contract itself.

## 2. D1-D8 mapping

### D1 Intent
State the effect sought, not the source product name. Example: "confine an untrusted tool invocation to a declared filesystem/network scope."

### D2 State
Capture source lifecycle states and the target current state needed to reason about transition compatibility.

### D3 Coordinate
Bind repository/tag/commit/tree/source path plus target node/module/namespace/logical-time coordinate when available.

### D4 Evidence
Record implementation files, tests, receipts, hashes, event history, attestations, telemetry, and their evidence status. Keep functional evidence distinct from integrity/identity evidence.

### D5 Execution/Policy
Capture allowed operations, intercept points, retry/timeout/cancel semantics, policy evaluation, filesystem/network scope, and side effects.

### D6 Generative Transmission
Use the source only to derive reconstruction requirements. W7TP D6 remains target-aware generation:

```text
TARGET_BASE_STATE
+ MINIMUM_REQUIRED_DELTA
+ REFERENCES
+ COORDINATES
+ RECONSTRUCTION_RULES
+ VERIFICATION_RULES
```

Do not redefine D6 as copying source files, dependency installation, synchronization, or source-side replay.

### D7 Risk/Quarantine
Capture fail-open paths, unsafe defaults, unresolved security assumptions, rollback gaps, state overwrite, privilege expansion, credential inheritance, and unbounded filesystem/network behavior.

### D8 Envelope/Authority
Describe source authorization mechanics as evidence only. W7TP D8 must remain external to the source unless a valid W7TP authority object explicitly binds it.

Identity and Seat are full-envelope preconditions, not D1.

## 3. Assimilation disposition

### REUSE_DIRECTLY
Use only when all are true:

- effect exactly closes the target gap;
- target runtime can consume it without authority drift;
- side effects are bounded;
- license obligations are known and acceptable;
- no W7TP Canonical/D8 meaning is imported;
- target acceptance can independently verify the effect.

### ADAPT
Use when source behavior is valuable but needs namespace, schema, policy, evidence, or protocol wrapping.

### REIMPLEMENT
Use when the observable effect is valuable but source authority/state/security/runtime semantics are incompatible or dependency is undesirable.

### REJECT
Use when the capability adds no necessary value, violates the authority wall, weakens fail-closed behavior, or cannot be bounded sufficiently.

## 4. Target convergence classes

```text
MATCH                  -> REUSE
MISSING_REQUIRED       -> COMPLETE
STALE_OR_INCOMPATIBLE  -> VERSIONED_COVER_OR_MIGRATE
TARGET_ONLY            -> PRESERVE
EXTENDABLE             -> EXTEND_INTENT_FIELD
CONFLICT                -> CONVERGENCE_CANDIDATE
UNKNOWN                 -> TARGET_EVIDENCE_RESOLUTION
```

A source architecture is never the desired target merely because it is mature.

## 5. Equivalent reconstruction acceptance

Do not call a target implementation equivalent unless the declared acceptance contract supports at least:

- same intended effect;
- compatible preconditions;
- equivalent governed state transition;
- sufficient evidence class;
- preserved policy and risk decision;
- valid authority result;
- accepted observable output/side effect.

Code, file layout, language, model, vendor, branch, or runtime identity need not match unless the contract explicitly requires exact identity.
