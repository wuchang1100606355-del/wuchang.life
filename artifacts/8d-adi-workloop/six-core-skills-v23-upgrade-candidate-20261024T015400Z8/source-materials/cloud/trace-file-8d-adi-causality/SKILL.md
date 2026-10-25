---
name: trace-file-8d-adi-causality
description: Build a candidate-only 8D/ADI system intent field from Founder intent and the bounded content contracts of every source file in a local repository or a repository reached through an exact fixed-IP SSH profile. Use when Codex must reconstruct what each file should be called, what it supplies or requires, its product effect, dependencies, relations, terminology, transitions, evidence, authority, and reconstruction coordinate without making Git, paths, hashes, or keywords the design authority. Export bounded six-axis evidence inputs for audit-technology-identity when a technical-identity claim is in scope, but never adjudicate technical sameness, patentability, or superiority here.
---

# Trace File 8D ADI Causality

## Preserve the authority boundary

Treat Founder intent and the human-visible product effect as the field root. Treat bounded source content as the capability evidence used to resolve that field. Emit only candidate evidence. Never emit `PASS`, canonical promotion, activation, commit, push, deployment, database writes, service changes, or pointer changes.

Treat 8D as one atomic projection for each file state, not eight workflow stages. Treat ADI as coordinated state, capability, decision, transition, spatial-temporal, evidence, and reconstruction coordinates. Never reduce it to semantic search, embeddings, a dependency table, or ordinary file metadata.

Ordinary SSH is only a carrier. Never call SSH, copying, Git, backup, compression, or synchronization W7TP generative transmission. Read [references/causal-contract.md](references/causal-contract.md) before changing comparison behavior.

## Select the execution coordinate

- For a local repository, run `scripts/causal_index.py` directly.
- For a fixed private node, run `scripts/remote_runner.py` with a private profile conforming to [references/connection-profile.md](references/connection-profile.md).
- Keep the raw private IP and account coordinate in that local profile only. Do not copy them into `SKILL.md`, manifests, prompts, model context, reports, or evidence outputs.
- Require an IP literal, strict host-key checking, batch mode, a pre-existing SSH trust path, and an absolute remote repository path.
- Do not fall back to DNS, another address, cloud relay, a tunnel, or another node when the fixed IP is unavailable.

## Form the field, freeze once, and compare independently

Resolve one Founder intent and one human-visible product effect before scanning. Run one source enumeration and extract bounded content contracts: module summaries, declarations, imports, calls, inputs, outputs, schemas, routes, states, decisions, terms, effects, explicit references, and protected opaque boundaries. Do not consult Git. Paths, hashes, and modification times are evidence coordinates only.

Build one deterministic supply-demand pair plan from explicit imports, explicit file references, and uniquely resolved symbol consumers/providers. Content contracts create the relation candidates; shared path tokens, times, hashes, or keywords do not.

Run these independent comparison subroutines over only the frozen snapshot and pair plan:

`DEMAND`, `SUPPLY`, `EFFECT`, `DEPENDENCY`, `RELATION`, `TERM`, `STATE_TRANSITION`, `EVIDENCE`, `AUTHORITY`, `RECONSTRUCTION`, and `RISK`.

Each comparison runs as a separate child process. Every process must use identical snapshot and pair-plan hashes, perform no filesystem rescan, perform no network, semantic, fuzzy, Git, or undeclared-path search, and read no other subroutine output. The aggregator may validate and join edges; it may not reread sources, discover targets, invent causality, resolve authority conflicts, or promote `INFERRED` to `OBSERVED`.

Require every emitted edge to carry the complete causal contract even when fields remain `UNKNOWN`. An explicit import, explicit file reference, or uniquely resolved symbol consumer/provider may become `RECONSTRUCTED_EXPLICIT_SUPPLY_DEMAND`; it remains candidate-only until Total Field accepts it. Time, path, token, hash, keyword, or byte equality alone never creates a design relation. Record one distinct child-process and invocation receipt for every comparator, including zero-edge results.

## Export technology-identity evidence, never decide it

Always emit `92_TECHNOLOGY_IDENTITY_EVIDENCE_CANDIDATE.json` as a gate-input view over the frozen evidence. Keep the six axes fixed as `MECHANISM`, `CAUSAL_PATH`, `DEPENDENCIES`, `ELIMINATED_OPERATIONS`, `COST_TOPOLOGY`, and `CARRIER_RECONSTRUCTION_VERIFICATION`. Preserve unsupported axes as `UNKNOWN` with `EV0_UNSUPPORTED`; do not fill gaps from filenames, shared effects, analogy, or model confidence.

When the request compares technologies or claims technical sameness, structural elimination, zero-float, verification elimination, or superiority, pass this evidence view to the installed `audit-technology-identity` skill. This skill supplies evidence only. It must leave the gate decision as `NOT_RUN`, emit no weighted technology-identity score, keep effect equivalence separate from technical equivalence, and retain `PATENT_OR_LEGAL_CONCLUSION=NOT_DETERMINED`.

## Protect sensitive sources

Represent suspected credentials, keys, tokens, passwords, member plaintext, and identity plaintext as `PROTECTED_OPAQUE_NODE`. Record only path-relative structural metadata, state layer, permissions, size, and the protection reason. Do not read, hash, print, transmit, or place their contents in model context.

Treat binaries, cache, vendor, generated, and large runtime outputs as structural nodes. Common virtual-environment, cache, vendor, and dependency directories may be represented as declared structural boundaries without descent; report that bounded scope and never call it complete per-file coverage. Do not infer meaning from their names. Preserve conflicts and unknowns.

Never follow symbolic links. Do not descend into protected directories or read a likely private key that has a same-stem `.pub` sibling. Record directory-enumeration and file-read failures as explicit coverage gaps; do not claim full coverage when any gap remains.

## Run locally

```bash
python3 scripts/causal_index.py \
  --repo /absolute/repository/path \
  --output-dir /absolute/repository/path/evidence/total_field/file_8d_adi_causal_index/RUN_ID \
  --founder-intent "<本次要找回的系統設計意圖>" \
  --product-effect "<人類可見產品效果>"
```

The output directory must not exist inside the frozen source set. The script excludes its exact output directory during enumeration and writes only candidate artifacts there.

Use a new output directory for every run. Refuse to overwrite or append into an existing coordinate.

## Run through a fixed-IP private profile

```bash
python3 scripts/remote_runner.py \
  --profile /private/path/taiji01-fixed.json \
  --founder-intent "<本次要找回的系統設計意圖>" \
  --product-effect "<人類可見產品效果>"
```

The runner sends the deterministic analyzer over standard input to the already trusted SSH endpoint. It does not use SCP, install a service, read a password, alter SSH configuration, or label the carrier as generative transmission.

If the route, host key, non-interactive authentication, Python runtime, repository, or bounded output coordinate is unavailable, return one `PRECONDITION_MISSING` result. Do not search for alternatives.

## Verify the result

Require:

- one source enumeration;
- all file-state and term edge endpoints present;
- the intent field root is Founder intent plus the human-visible product effect;
- every analyzed source file carries bounded content-derived supply, demand, role, logical name, D1-D8, and full ADI coordinates;
- every edge physically contains actor, precondition, trigger, action, mechanism, effect, dependency, relation, term, necessity/sufficiency, failure effect, reconstruction, evidence class/reference, authority, D1-D8, and full ADI references;
- identical snapshot and pair-plan hashes across comparators;
- a distinct structured execution receipt for each of the eleven child comparators;
- parseable JSON and JSONL;
- a complete SHA-256 manifest;
- gate-input-only `92_TECHNOLOGY_IDENTITY_EVIDENCE_CANDIDATE.json` with all six axes, EV evidence levels, no weighted score, and no local identity decision;
- structured `93_RED_TEAM_EXECUTION_EVIDENCE.json` bound into the SHA-256 manifest;
- explicit partial-coverage HOLD evidence for every read or directory-enumeration failure;
- no Git consultation and no source, runtime, database, service, canonical, or pointer changes;
- `OBSERVED`, `RECONSTRUCTED`, `INFERRED`, `CONFLICT`, and `UNKNOWN` kept distinct;
- product and 8D field checks run first; true hard-risk checks run last;
- no component emits Total Field `PASS`.

Validate the governed definition against [total-field-skill-manifest.json](total-field-skill-manifest.json). Installation and static validation do not make the skill active under Total Field.

## Return one compact receipt

Return:

```text
STATE=<CANDIDATE_NOT_CANONICAL|PRECONDITION_MISSING|HOLD_TRUE_HARD_RISK>
RUN_ID=<value>
NODE_REF=<opaque node ref>
CONNECTION_MODE=<LOCAL|FIXED_IP_SSH_PRIVATE_PROFILE>
SOURCE_ENUMERATION_COUNT=<0|1>
SOURCE_FILE_COUNT=<count>
FILE_STATE_NODE_COUNT=<count>
CAUSAL_EDGE_COUNT=<count>
VERIFIED_CAUSAL_CHAIN_COUNT=<0 unless separately adjudicated>
RECONSTRUCTED_CAUSAL_CHAIN_COUNT=<content-contract chain count>
SOURCE_COVERAGE_STATUS=<complete or partial with explicit gaps>
CONFLICT_COUNT=<count>
UNKNOWN_COUNT=<count>
PROTECTED_OPAQUE_COUNT=<count>
OUTPUT_DIR=<bounded path or NONE>
MANIFEST_SHA256=<value or NONE>
ORIGINAL_FILES_MODIFIED=FALSE
GIT_CONSULTED=FALSE
CANONICAL_PROMOTION=FALSE
TOTAL_FIELD_DECISION=NOT_RUN
TECHNOLOGY_IDENTITY_EVIDENCE_STATUS=GATE_INPUT_ONLY
TECHNOLOGY_IDENTITY_GATE_DECISION=NOT_RUN
WEIGHTED_TECHNOLOGY_IDENTITY_SCORE_USED=FALSE
PATENT_OR_LEGAL_CONCLUSION=NOT_DETERMINED
NEXT=<one shortest action>
```

## Single current design

Use `govern-total-field-skills` → `references/current-design-contract.json` as the single Founder V2.3 design root. Read its `references/version-observation-causality.md` for causal-chain changes. Revalidate dependent references, validators and state indexes after changes; do not choose an older design as fallback. Historical evidence stays historical. ADI binds state, time, spatial/object location, relations, causality and reconstruction coordinates together. Preserve actual runtime schema differences as local migration gaps.


## Bounded read-only observation profile

For a user-authorized read-only file inspection, use the explicitly supplied source or named connected device and record its exact node, runtime, path, source state and observation time. This profile does not run the full indexer or its comparison subprocesses: report `COMPARATORS=NOT_RUN`, exact coverage, and candidate evidence only. Do not require index-export artifacts to read an authorized bounded source. The fixed-IP runner retains its own route and host-key requirements; this profile is not a fallback after its failure.

