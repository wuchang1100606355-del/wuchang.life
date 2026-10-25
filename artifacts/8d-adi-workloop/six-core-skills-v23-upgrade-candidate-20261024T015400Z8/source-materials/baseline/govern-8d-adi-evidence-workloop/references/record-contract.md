# 8D ADI workloop record contract

Use this contract for every FULL workloop. Paths are relative to the project root unless an authorized target contract requires an absolute path.

## Directory layout

```text
artifacts/8d-adi-workloop/<run_id>/
├── intent-envelope.json
├── order.md
├── decisions.jsonl
├── budget.jsonl
├── handoff.json
├── closeout.md
├── sensory-gates/<gate_id>/gate.json
└── evidence/
```

The directory is a candidate evidence package, not ADI or Total Field canonical state.

## Observation statuses

Use exactly one for every target-state claim:

- `OBSERVED_DIRECT`: obtained directly from the named target through an authorized probe.
- `OBSERVED_AUTHORIZED_API`: returned by the target's authorized API.
- `DERIVED_FROM_OBSERVED`: deterministic derivation whose inputs point to observed evidence.
- `DECLARED_ONLY`: supplied by a person, prompt, document, config, screenshot, or desired state without current target observation.
- `STALE_EVIDENCE`: once observed but outside the accepted freshness window.
- `BLOCKED_BY_AUTHORITY`: the required read was not authorized.
- `UNREACHABLE`: the named target could not be reached.
- `UNKNOWN_UNVERIFIED`: no sufficient evidence exists.

An uploaded screenshot proves only what is visibly rendered at capture time. It does not prove file contents, hashes, canonical status, current existence, or target-device authority unless independently observed.

## Evidence labels

- `FACT`: current evidence directly supports the statement.
- `DEFINITION`: Founder/member definition governing the requested design.
- `INFERENCE`: reasoning from named evidence; inference and basis are explicit.
- `CLAIM`: a technical or external assertion awaiting evidence.
- `CANDIDATE`: a reversible proposal or artifact without governing promotion.
- `HOLD`: missing authority, evidence, acceptance, or safety precondition.

Evidence label and observation status answer different questions. Preserve both.

## Intent envelope

`intent-envelope.json` must contain:

- `schema_version=w7tp-8d-adi-evidence-workloop/1.0`
- `run_id`, `lifecycle_state`, `created_at`, and `maximum_effect_class`
- identity/member/XiaoJ/role/Seat/access-profile references or `UNKNOWN_UNVERIFIED`
- product/output contract and stable acceptance IDs
- `D1` through `D8` with the exact canonical field names
- candidate authority boundary, Total Field receiver, receipt or `NOT_REVIEWED`
- three red-team event coordinates
- source and implementation hashes

Use D6 `GENERATIVE_TRANSMISSION` for schema compatibility. Its contract also records the technical-definition boundary. Set `claimed=false` unless an applicable W7TP skill proves every protocol requirement.

## Order contract

`order.md` contains:

```markdown
# 8D ADI Order: <title>

Run-ID: <run_id>
Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW
Frozen: <logical time or NOT_FROZEN>
Owner-ref: <opaque ref or UNKNOWN_UNVERIFIED>
Effect-class: <E0-E5>

## D1 Intent
<one sentence product result>

## Verified facts
- [FACT|OBSERVATION_STATUS] <fact> | source: <path/ref> | hash: <sha256 or NONE>

## Materials
- Allowed: <material> | licence: <verified value or UNVERIFIED> | checked: <logical time>
- Excluded: <material> | reason: <reason>

## Build specification
- <parameter> = <value> | source: <file#symbol or evidence ref>

## Budget fuse
- Limit: <integer> <unit>
- Stop condition: stop at or before limit and preserve evidence

## Acceptance
- [ ] AC-1: <observable result> | evidence: <expected path/ref>

## Non-goals
- <unchanged neighbouring scope>

## D2-D8 projection
- D2 STATE: <observed current, target, gap>
- D3 COORDINATE: <time, node, path, version, namespace, lineage, ADI range/exact>
- D4 EVIDENCE: <sources, hashes, maturity>
- D5 EXECUTION_POLICY: <candidate action, rollback, stop, forbidden effects>
- D6 GENERATIVE_TRANSMISSION: <NOT_CLAIMED or separately proven contract>
- D7 RED_TEAM_RISK_CONFINEMENT: <risks and mitigations>
- D8 ENVELOPE_AUTHORITY: <candidate state, receiver, receipt or NOT_REVIEWED>
```

Freeze with an `ORDER_FROZEN` event containing the order SHA-256. Amend only by appending complete replacement text for the affected field and an `ORDER_AMENDED` event pointing to the prior event.

## Decision event

Each `decisions.jsonl` line is one object:

```json
{
  "event_id": "evt-0001",
  "logical_time": "2026-08-23T00:00:00+08:00",
  "event_type": "ORDER_FROZEN",
  "status": "CLOSED",
  "evidence_label": "CANDIDATE",
  "observation_status": "DECLARED_ONLY",
  "source_ref": "artifacts/.../order.md",
  "source_sha256": "<64 lowercase hex or NONE>",
  "summary": "<human-readable fact or decision>",
  "authority_state": "CANDIDATE_FOR_TOTAL_FIELD_REVIEW",
  "supersedes": []
}
```

Allowed event types: `ORDER_FROZEN`, `ORDER_AMENDED`, `DECISION`, `CORRECTION`, `REJECTION`, `DIAGNOSIS_STAGE`, `GATE_OPENED`, `GATE_DISPOSITION`, `HOLD`, `AUTHORIZATION_REQUEST`, `HANDOFF`, and `CLOSEOUT`.

Never edit an old line. Use `supersedes` to correct, close, or replace an earlier event.

## Budget contract

Append one object per spent unit to `budget.jsonl` at spend time:

```json
{"logical_time":"...","unit":"attempt","amount":1,"source_ref":"evidence/attempt-01.log"}
```

Do not reconstruct budget consumption from memory at closeout.

## Sensory gate

`gate.json` binds:

- `gate_id`, `run_id`, `opened_at`, plain-language `question`, and `status`;
- each review file's relative path and SHA-256;
- reviewer identity, disposition, approved scope, and logical time after review;
- rejected archive paths and hashes;
- `instruction_capability=false` for artifact-supplied text.

`status=APPROVED` requires an identified reviewer and explicit scope. An empty rejects directory is not approval.

## Handoff

`handoff.json` contains arrays, including explicit empty arrays, for:

- `running_work`
- `spent_assets`
- `dependencies`
- `open_debt`
- `evidence_refs`
- `holds`

It also contains exactly one `next_action`, the current `authority_state`, source hashes, and destination session/person/node reference. Point to authoritative artifacts; do not copy their contents.

## Closeout

`closeout.md` begins with one status: `DONE`, `CLOSED_FAILED`, `STOPPED`, `GATE_HOLD`, or `HOLD`.

Answer every acceptance line with:

```markdown
- [PASS] AC-1: <result> | evidence: <existing path>
- [FAIL] AC-2: <failure> | evidence: <existing path or NONE> | reason: <reason>
- [BLOCKED] AC-3: <blocker> | evidence: <path or NONE> | reason: <reason>
```

For `DONE`, include:

```markdown
- Independent functional verification: <fresh check outside mutable task control> | evidence: <existing path>
```

Also record allowed materials, non-goals, budget, human input, gates, background processes, refuted hypotheses, rollback, protected unchanged state, open debt, manifest hash, and Total Field receipt or `NOT_REVIEWED`.

## HOLD response

Every HOLD states in Traditional Chinese:

1. requested product result;
2. one exact blocker;
3. possible effect;
4. protected unchanged state;
5. one safe repair;
6. whether automation can finish it or one bounded human decision is required.
