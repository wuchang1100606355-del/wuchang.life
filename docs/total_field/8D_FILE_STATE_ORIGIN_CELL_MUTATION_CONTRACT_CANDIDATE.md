# 8D File-State / Origin-Cell Mutation Contract — Candidate

**Founder correction:** 2026-09-18 (Asia/Taipei)  
**State:** `CANDIDATE_FOR_TOTAL_FIELD_REVIEW`  
**Canonical write:** `NONE`  
**Runtime activation:** `NONE`

This candidate refines the 2026-09-17/18 results freeze. It records that a file must not be treated as the primary semantic mutation unit. A file is a serialized projection/container of state. Before modification, the system must understand the file through the complete D1–D8 state, its dependency/storage relations, its exact coordinates, and the Origin-Cell state instructions that authorize and describe the minimum state transition.

## 1. Governing rule

```text
FILE != PRIMARY_MUTATION_UNIT
ORIGIN_CELL = MINIMUM_COMPLETE_D1_D8_STATE_UNIT
```

Modification flow:

```text
FOUNDER_INTENT
+ TARGET_FILE / OBJECT OBSERVATION
+ D1-D8 FILE-STATE INTERPRETATION
+ DEPENDENCY / STORAGE RELATION GRAPH
+ EXACT COORDINATES
+ ORIGIN-CELL STATE INSTRUCTIONS
        |
        v
SOURCE / TARGET STATE COMPARISON
        |
        v
REUSE | PRESERVE | COMPLETE | COVER_OR_MIGRATE | EXTEND | CONVERGE
        |
        v
MINIMUM_AUTHORIZED_STATE_DELTA
        |
        v
TARGET-NATIVE RECONSTRUCTION
        |
        v
VERIFY AFFECTED CELLS + DEPENDENCIES + FINAL FILE/OBJECT STATE
```

A file must not be modified merely because text, bytes, filename, or path appears different. The relevant state transition must first be resolved at the Origin-Cell level.

## 2. D1–D8 interpretation of file state

Every governed file/object mutation candidate must bind the following state before mutation.

### D1 — Intent

What product/system intent the file participates in; why this file/object exists; which intended effect the requested modification is supposed to produce.

A textual edit without a bound D1 intent is not sufficient authority to change a governed file.

### D2 — State

Current semantic and operational state, including as applicable:

- current version / object identity;
- content hash / state hash;
- schema state;
- lifecycle state;
- predecessor/successor relation;
- current logical value represented by the relevant section/object/cell.

D2 is not reduced to file bytes. Two byte-different projections may represent equivalent state, and byte-equal projections may be invalid when coordinates, authority, dependencies, or freshness differ.

### D3 — Coordinate / Location / Relation

Bind the exact location and relation of the state being changed, including as applicable:

```text
node
repository / storage namespace
branch / revision / tree
file path / object key
schema / table / record / field
section / symbol / block / range
origin-cell coordinate
logical time / scene / target workspace
incoming / outgoing dependency references
```

Moving or renaming an object is therefore a D3 state transition even when content is unchanged. References that depend on the old coordinate must be evaluated before accepting the new coordinate.

### D4 — Evidence

Bind the evidence that establishes the observed current state and the result of the proposed transition:

- hashes;
- receipts;
- tests;
- provenance;
- target observation;
- reconstruction evidence;
- dependency verification;
- end-product acceptance when required.

Historical evidence remains append-only.

### D5 — Execution / Policy

State exactly what may change and what must not change:

- allowed mutation scope;
- target boundary;
- preservation requirements;
- rollback rule;
- forbidden side effects;
- whether the change is candidate-only, isolated reconstruction, or separately authorized live effect.

Permission to read or understand a file is not permission to modify it.

### D6 — Generative Transmission / Reconstruction

Construct the target-aware state transition from:

```text
TARGET_BASE_STATE
+ MINIMUM_REQUIRED_DELTA
+ REFERENCES
+ COORDINATES
+ RECONSTRUCTION_RULES
+ VERIFICATION_RULES
```

Reuse the verified target-native state. Do not replace a complete file/object when the intended effect can be produced by a smaller verified state transition, except when physical serialization requires an atomic whole-file write. In that case, the logical mutation and evidence must still record only the affected Origin-Cell state delta and its dependency closure.

### D7 — Risk / Quarantine

Classify unresolved or unsafe conditions before mutation, including:

- stale base state;
- broken or unknown dependency;
- conflicting predecessor;
- protected or cross-member data;
- unexpected target-only state;
- schema incompatibility;
- replay / stale instruction;
- widened mutation scope;
- unverified reconstruction.

`UNKNOWN` and `CONFLICT` are not silently converted into modification instructions.

### D8 — Envelope / Authority

Bind who/what may authorize the transition and the exact authority envelope:

- natural-person / member / role / Seat reference as applicable;
- Total Field decision reference;
- nonce / TTL / logical time;
- allowed effect class;
- target identity;
- instruction identity/hash;
- final acceptance boundary.

A model, editor, account, transport, file path, or device is not authority by itself.

## 3. Dependency and storage-relation graph

A governed file/object must be interpreted together with the relations that give its state meaning.

Represent the relevant graph as:

```text
NODE = file | object | schema | service | index | cell | capability | evidence
EDGE = depends_on | references | generated_from | consumed_by |
       stored_at | mirrors | reconstructs_from | supersedes |
       authorized_by | verified_by
```

The graph is used to determine which Origin Cells are affected by a requested state change.

The default affected set is:

```text
AFFECTED_CELLS
= AUTHORIZED_SCOPE
  ∩ CLOSURE(CHANGED_ORIGIN_CELLS, DEPENDENCY_GRAPH)
```

Unaffected coordinates are preserved. A dependency closure must not be expanded merely for convenience.

## 4. Origin-Cell state instruction

Each mutation instruction should bind at least:

```text
ORIGIN_CELL_ID
CURRENT_STATE_REF / BASE_HASH
TARGET_STATE
D1_INTENT_REF
D3_COORDINATE
DEPENDENCY_REFS
OPERATION
MINIMUM_DELTA
PRESERVE_REFS
RECONSTRUCTION_RULE
VERIFICATION_RULE
ROLLBACK_RULE
D8_AUTHORITY_REF
LOGICAL_TIME / TTL / NONCE
```

Allowed primary operation classes remain:

```text
MATCH                 -> REUSE
MISSING_REQUIRED      -> COMPLETE
STALE_OR_INCOMPATIBLE -> VERSIONED_COVER_OR_MIGRATE
TARGET_ONLY           -> PRESERVE
EXTENDABLE            -> EXTEND_INTENT_FIELD
CONFLICT              -> CONVERGENCE_CANDIDATE
UNKNOWN               -> TARGET_EVIDENCE_RESOLUTION
```

An Origin-Cell instruction modifies the bound state at its coordinate. It does not imply that neighboring cells, the whole file, the whole repository, or the whole target should also be rewritten.

## 5. File mutation is reconstruction, not blind editing

The intended semantics are:

```text
DO NOT:
read file -> search text -> replace broadly -> save

DO:
observe target -> interpret D1-D8 -> resolve coordinates + dependencies
-> identify affected Origin Cells -> derive minimum authorized delta
-> reconstruct target-native projection -> verify state equivalence/effect
```

Examples:

- **Single value change:** modify only the Origin Cell carrying that state plus the dependency closure proven to require update.
- **Rename/move:** treat as D3 coordinate transition; preserve content state and update only references whose dependency evidence requires it.
- **Schema migration:** preserve predecessor evidence; create versioned successor state; do not overwrite history.
- **Generated artifact:** modify the governing source/state instruction when appropriate, then regenerate the affected projection; do not patch an output that will immediately be overwritten by its generator.
- **Cross-language target:** preserve the same intended state contract while allowing the target-native adapter to serialize different code/text/representation.

## 6. Physical full-file writes

Some formats or APIs only support replacing an entire physical file. That implementation constraint does not change the logical mutation unit.

When a whole-file serialization is unavoidable:

```text
LOGICAL_CHANGE = AFFECTED_ORIGIN_CELL_DELTA
PHYSICAL_WRITE = FULL_SERIALIZED_FILE
```

The receipt must distinguish the two. The system must prove that unrelated Origin Cells were preserved and that the final serialized file satisfies the bound target-state contract.

## 7. Required pre-mutation acquisition

Before issuing an Origin-Cell mutation instruction against a live/actual target, acquire the current target state from the actual target. A source-side copy, old receipt, forwarded file, filename, or historical hash cannot substitute for current target observation.

If current target state cannot be observed:

```text
STATE=TARGET_NOT_OBSERVABLE
MUTATION=NOT_AUTHORIZED_BY_THIS_CANDIDATE
NEXT=ACQUIRE_CURRENT_TARGET_D1_D8_STATE_AND_DEPENDENCY_COORDINATES
```

## 8. Total Field role

Total Field does not perform a blind whole-file rewrite merely because a candidate proposes one. It evaluates the formed Origin-Cell transition against current target evidence, dependency closure, risk, and authority.

The intended authority chain is:

```text
FOUNDER / MEMBER INTENT
      -> 8D FILE-STATE INTERPRETATION
      -> ORIGIN-CELL STATE INSTRUCTION
      -> MINIMUM DELTA / TARGET-NATIVE RECONSTRUCTION
      -> TARGET EVIDENCE
      -> TOTAL FIELD ACCEPT / HOLD / REJECT
```

This keeps asynchronous distributed organs compatible with one unified authority state.

## 9. Correction to the frozen architecture

The 2026-09-17/18 freeze should therefore be interpreted with this additional Founder rule:

> **8DADI does not primarily operate by editing files. It understands each governed file/object as an eight-dimensional state projection with exact dependencies, storage relations, and coordinates. The Origin-Cell Controller issues state instructions against the minimum affected complete-state cells; the target then reconstructs the necessary projection, while Total Field preserves authority, evidence, unrelated state, and dependency consistency.**

This candidate does not activate a runtime mutator, change canonical state, or retroactively rewrite historical evidence. It freezes the intended modification semantics for Total Field review.
