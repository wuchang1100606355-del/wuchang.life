---
name: w7tp-capability-assimilator
description: Rapidly and accurately analyze external software, repositories, releases, frameworks, plugins, skills, protocols, or public system designs and convert only their observable capabilities into W7TP/8D ADI implementation-independent capability contracts. Use when asked to assimilate, absorb, learn from, adapt, reimplement, compare, clean-room reconstruct, or extract capabilities from third-party systems; map capabilities to D1-D8, classify REUSE/ADAPT/REIMPLEMENT/REJECT, preserve provenance, detect authority inversion, and derive a target-aware minimum delta without importing an external authority model. Default to read-only static analysis and no installation or system mutation.
---

# W7TP Capability Assimilator

## Purpose

Convert external implementations into evidence-bound capability contracts that W7TP/8D ADI can understand and reconstruct natively. Preserve useful effects, not vendor architecture or authority. Prefer the smallest sufficient evidence path and the smallest target-native delta.

## Core invariants

1. Treat `CAPABILITY != IMPLEMENTATION`. Extract observable input, state transition, output, evidence, failure behavior, constraints, and acceptance before considering code reuse.
2. Treat every external project as a capability source, never as W7TP Canonical, Founder identity, D8 authority, Total Field authority, or effect authorization.
3. Preserve provenance: repository, release/tag, commit/tree, license, source paths, test evidence, and whether a claim is documented, implemented, upstream-tested, current-run-verified, or unknown.
4. Default to `READ_ONLY_STATIC`. Do not install, execute project code, deploy, restart, mutate a target repository, or write authority/canonical state unless the user separately authorizes that exact action and scope.
5. Prefer target reuse. Never assume source/target sync is the goal. Preserve target-only valid state and derive only the minimum required delta.
6. Separate `OBSERVED`, `RECONSTRUCTED`, `INFERRED`, `CONFLICT`, and `UNKNOWN`. Never promote README claims, upstream CI, model confidence, or a source project's `PASS/DONE` vocabulary into W7TP acceptance.
7. Prefer clean-room effect reconstruction when the user wants assimilation rather than dependency. Do not copy source code or documentation by default. If direct reuse is considered, verify the actual license and keep attribution/notice obligations explicit.
8. Keep D6 exact: it means target-aware reconstruction from an admitted verified target base plus irreducible novel delta, references, ADI coordinates, reconstruction rules, and verification rules. Cloud/local model failover, prompt or context transfer, compression, file copy, synchronization, SSH, Git, SMB, Tailscale, and VPN are not D6; they are at most capability supply or carriers.
9. Treat license clearance as distinct from patent or trademark clearance. Mark unverified IP questions as `UNKNOWN`; do not invent legal permission.

## Account, conversation, and skill-to-skill assimilation

- An external AI account, organization-mode memory, chat export, model response, or custom GPT is a D4 capability source only. It cannot establish Founder identity, current system state, Canonical, D8, deployment, or live effect.
- Preserve each account, workspace, project, thread, timestamp, and export limitation as a distinct provenance coordinate. Assimilate claims and effects without merging account identities or memory authority.
- Accept an external skill as observable only when an exact artifact or current behavior provides its trigger, inputs, outputs, tool binding, side effects, failure modes, acceptance conditions, example cases, and context references. "The model says it can" is `DOCUMENTED_ONLY` or `UNKNOWN`.
- Merge non-overlapping strengths into the existing target skill that already owns the capability. Create a new skill only when no existing owner can express the capability without violating its scope; never create a parallel Total Field, ADI, Receiver, context database, or authority layer.
- Exact duplicate claims may share a normalized claim digest while retaining every source coordinate. Conflicting claims remain explicit; do not use majority vote, semantic averaging, recency alone, or model confidence as truth resolution.
- The output contract for an assimilated skill must include `TRIGGER`, `INPUT`, `OUTPUT`, `TOOL_BINDING`, `SIDE_EFFECT`, `FAILURE_MODE`, `ACCEPTANCE`, `EXAMPLE_CASES`, `CONTEXT_REFERENCES`, `PROVENANCE`, and `AUTHORITY_BOUNDARY`.

## Select one operation

- `DISCOVER`: Find external projects likely to close a named W7TP capability gap.
- `ACQUIRE`: Pin a source version and build a read-only evidence coordinate.
- `EXTRACT`: Turn one source into capability units with implementation evidence.
- `COMPARE`: Compare multiple sources or one source against target-native capabilities.
- `ASSIMILATE`: Perform ACQUIRE + EXTRACT + target comparison + clean-room contract generation. Default when a specific external source is supplied.
- `VALIDATE`: Validate a previously produced assimilation packet or candidate implementation against its declared capability contract.

Combine operations only when the user's decision requires it.

## Fast accurate workflow

### 1. Freeze the assimilation intent

Record only what is needed:

- target system or component;
- desired effect or current capability gap;
- external source locator(s);
- whether source code may be read;
- whether direct reuse is allowed or clean-room reconstruction is preferred;
- allowed evidence sources;
- prohibited actions;
- acceptance condition.

If the user already supplied these, do not ask again.

### 2. Pin the source before interpreting it

For a local Git checkout, run:

```bash
python3 scripts/source_manifest.py --repo <path>
```

For a public remote source when no checkout exists, use available web/Git repository tools to obtain, in priority order:

`repository -> release/tag -> commit -> tree -> license -> SECURITY -> root manifest -> architecture docs -> entrypoints -> capability-relevant source/tests`.

Do not widen into a full-repository scan if the needed capability can be proven from a smaller set of files.

Read [references/source-acquisition.md](references/source-acquisition.md) when source identity, license, release lineage, or clean-room boundaries matter.

### 3. Run a two-pass extraction

**Fast pass — architecture triage**

Determine whether the source actually contains or only documents:

- entrypoints and runtime;
- protocol adapters and registries;
- tool/agent execution or dispatch;
- context/state handling;
- hooks, middleware, and policy gates;
- identity, auth, scopes, delegation, revocation;
- sandbox/isolation and filesystem/network boundaries;
- process supervision, timeout, cancellation, retry, compensation;
- event history, receipts, audit, provenance, attestations;
- plugin/model/MCP/A2A/external-tool adapters;
- federation/distributed coordination;
- observability/telemetry;
- security boundary and known fail-open paths.

**Deep pass — evidence only for high-value candidates**

Inspect only the source files and tests needed to prove shortlisted capabilities. Prefer implementation and tests over marketing prose. Distinguish:

- `DOCUMENTED_ONLY`
- `IMPLEMENTED`
- `UPSTREAM_TESTED`
- `VERIFIED_CURRENT_RUN`
- `UNKNOWN`

Never say `VERIFIED_CURRENT_RUN` unless this session actually executed an appropriate verifier/test.

### 4. Extract capability units

For each meaningful capability emit:

```text
CAPABILITY_ID
SOURCE_COMPONENT
SOURCE_VERSION_OR_COMMIT
STATUS
SOURCE_FILES
ENTRYPOINT
INPUT
OUTPUT
STATE_DEPENDENCY
SIDE_EFFECT
RUNTIME_DEPENDENCY
EVIDENCE_OUTPUT
FAILURE_MODE
SECURITY_ASSUMPTION
LICENSE_BOUNDARY
```

Describe the effect without reproducing protected implementation text. If the source lacks a capability, state `ABSENT`; do not infer it from project naming.

### 5. Map each unit to W7TP/8D ADI

Read [references/assimilation-contract.md](references/assimilation-contract.md). Map the source effect to:

- D1 Intent
- D2 State
- D3 Coordinate
- D4 Evidence
- D5 Execution/Policy
- D6 Generative Transmission support role
- D7 Risk/Quarantine
- D8 Envelope/Authority

Treat identity and Seat as full-envelope preconditions, not D1.

For D6, emit SUPPORTED only when the extracted capability supplies a verifiable part of this chain:

TARGET_BASE_STATE + MINIMUM_REQUIRED_DELTA + REFERENCES + ADI_COORDINATES + RECONSTRUCTION_RULES + VERIFICATION_RULES -> TARGET_RECONSTRUCTION_PACKET -> REOBSERVED_TARGET_STATE

Carrier or inference-provider compatibility alone must be reported as NOT_D6; it cannot satisfy D6 by naming or analogy. State-cell granularity and affected closure remain candidate refinements unless an explicit target contract promotes them.

For D8, describe external authorization behavior only as source evidence. Default W7TP authority output to `NONE` unless the W7TP target itself supplies a valid authority reference.

### 6. Classify assimilation disposition

Choose exactly one disposition per capability:

- `REUSE_DIRECTLY`: target can consume the capability unchanged and the technical/license/authority boundaries are compatible.
- `ADAPT`: preserve the capability contract but place it behind a W7TP adapter/wrapper.
- `REIMPLEMENT`: reproduce the observable effect with W7TP-native state, authority, evidence, or execution semantics.
- `REJECT`: the effect is unsafe, redundant, authority-inverting, incompatible, or unnecessary.

Direct reuse is never the default just because code is open source.

### 7. Compare source to target state

Classify each target relationship:

- `MATCH -> REUSE`
- `MISSING_REQUIRED -> COMPLETE`
- `STALE_OR_INCOMPATIBLE -> VERSIONED_COVER_OR_MIGRATE`
- `TARGET_ONLY -> PRESERVE`
- `EXTENDABLE -> EXTEND_INTENT_FIELD`
- `CONFLICT -> CONVERGENCE_CANDIDATE`
- `UNKNOWN -> TARGET_EVIDENCE_RESOLUTION`

Never delete or overwrite target-only state merely to resemble the source.

### 8. Derive an implementation-independent clean-room contract

When assimilation is preferred over dependency, transform:

```text
SOURCE_OBSERVED_BEHAVIOR
-> EFFECT_CONTRACT
-> TARGET_BASE_STATE
-> MINIMUM_REQUIRED_DELTA
-> TARGET_NATIVE_IMPLEMENTATION_CANDIDATE
-> VERIFICATION_RULES
-> ACCEPTANCE_RULES
```

The effect contract should be sufficient for a separate implementer to work without source implementation details. Preserve source attribution in the research/evidence record, not in the target's authority chain.

### 9. Run the authority-inversion wall

Read [references/authority-wall.md](references/authority-wall.md). Reject any transformation in which an external model, admin, reviewer, identity provider, policy engine, plugin hook, repository status, CI result, or source token becomes:

- Founder identity;
- W7TP Canonical maker;
- D8 authority source;
- effect authorization by itself;
- W7TP PASS/ACTIVE/CANONICAL by vocabulary mapping.

An external system may provide identity evidence, policy evaluation, delegation mechanics, or execution controls. It does not acquire W7TP authority merely by providing those mechanisms.

### 10. Validate structured output

When an assimilation packet is saved as JSON, run:

```bash
python3 scripts/validate_assimilation_packet.py packet.json
```

The validator checks required fields, evidence/disposition enums, D1-D8 presence, and common authority-inversion violations. A validator `PASS` proves packet form and hard-wall compliance only; it does not prove semantic truth or implementation correctness.

## Output contract

Lead with the direct assimilation decision. Then return the smallest useful result:

```text
STATE=<PASS_READ_ONLY_ASSIMILATION | PRECONDITION_MISSING | HOLD_TRUE_HARD_RISK | BLOCK_AUTHORITY_INVERSION>
OPERATION=<...>
SOURCE_COORDINATE=<repo/tag/commit/tree/license or exact missing coordinate>
TARGET=<...>

HIGH_VALUE_CAPABILITIES=[...]
REUSE_DIRECTLY=[...]
ADAPT=[...]
REIMPLEMENT=[...]
REJECT=[...]

TARGET_BASE_STATE=<...>
MINIMUM_REQUIRED_DELTA=<...>
AUTHORITY_CONFLICTS=[...]
EVIDENCE_GAPS=[...]

D1_INTENT=<...>
D2_STATE=<...>
D3_COORDINATE=<...>
D4_EVIDENCE=<...>
D5_EXECUTION=<...>
D6_TECHNICAL_DEFINITION=<...>
D7_RISK=<...>
D8_ENVELOPE=<...>

FILES_CHANGED=<NONE unless separately authorized>
PROJECT_CODE_EXECUTED=<false unless actually executed>
NEXT=<one shortest next action>
```

If the user asks for a machine-readable packet, use [references/assimilation-packet.schema.json](references/assimilation-packet.schema.json) as the structural contract.

## Efficiency rules

- Reuse supplied hashes, manifests, release pins, tests, and prior static-analysis evidence instead of rerunning them.
- Search source by capability question, not by arbitrary file count.
- Stop deep reading once the capability contract, failure boundary, and target disposition are supported.
- Prefer exact source paths and code/test evidence over broad documentation summaries.
- Preserve `UNKNOWN` rather than filling gaps with architectural intuition.
- Return one next action, not a sprawling research backlog.

## Example triggers

- "分析這個 GitHub repo，有哪些能力可以同化進 8D ADI。"
- "把 ContextForge/CPEX 的 gateway 與 policy enforcement 效果抽成 W7TP 能力契約。"
- "不要安裝，先做唯讀能力抽取，判定 REUSE/ADAPT/REIMPLEMENT/REJECT。"
- "我只要它的效果，不要它的 authority model，幫我做 clean-room 重構規格。"
- "比較 Temporal、gVisor、OPA、Biscuit，找出補 W7TP Executor 的最小能力組合。"
