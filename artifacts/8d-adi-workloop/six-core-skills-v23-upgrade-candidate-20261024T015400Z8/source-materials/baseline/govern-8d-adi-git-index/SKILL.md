---
name: govern-8d-adi-git-index
description: Build, validate, and review W7TP 8D ADI sidecar indexes for exact Git-object reconstruction, candidate Git placement, and durable deferred-push obligations. Use when incomplete but reconstructable state information should index Git objects, when physical pack placement must be separated from history rewriting, when Total Field must route a Git change, or whenever an AI blocks, defers, forgets, or cannot complete a requested Git push. Route acknowledged E4 execution, remote-OID closure, and terminal authoritative rechecks to $complete-deferred-git-push while retaining responsibility; never treat routing as activation or use this skill to rewrite live refs, canonical history, or Git object storage directly.
---

# Govern 8D ADI Git Index

Turn a bounded Founder intent into a reconstructable external Git index while preserving Git object identity, one Receiver, one identity root, fixed Seat, append-only lineage, and the candidate-to-canonical boundary.

## Preserve both technical identities

- Define W7TP as Intent Communication / State-Field Packet Communication. It carries state coordinates, lookup requirements, reconstruction conditions, acceptance rules, verification instructions, and governance evidence; it is not renamed Git compression, synchronization, backup, or partial clone.
- Treat Git as the canonical object-materialization boundary. Existing Git objects require exact byte reconstruction. A merely equivalent result gets a new object, tree, and commit OID.
- Permit physical placement proposals—hot/warm/cold grouping, candidate pack plans, MIDX hints, cache routes, and reconstruction order—without claiming that commit/tree/blob lineage was reordered.
- Treat any parent, tree entry, path, mode, author, timestamp, message, or object-byte change as new Git history.
- Git OID is content identity, never D8 authority.

Read [references/index-contract.md](references/index-contract.md) before creating or validating an index. Read [references/git-boundary.md](references/git-boundary.md) before proposing materialization, repacking, path relocation, partial clone, promisor, alternates, GC, or ref changes. Read [references/review-routing.md](references/review-routing.md) before routing a change for push or review. Read [references/deferred-push-obligation.md](references/deferred-push-obligation.md) whenever a requested push is not completed in the same governed run.

## Select one bounded operation

1. `INSPECT_READONLY`: inspect exact refs, OIDs, object types, sizes, pack metadata, and existing index evidence without writing.
2. `BUILD_SIDECAR_CANDIDATE`: create new candidate-only index, schema, manifest, report, test, or receipt files outside `.git` and outside canonical paths.
3. `VALIDATE_INDEX`: run `scripts/validate_git_index.py` on one packet and return its deterministic evidence.
4. `ROUTE_CHANGE`: run `scripts/git_review_gate.py` on a hash-bound change set and return exactly one route.
5. `DESIGN_PLACEMENT`: produce a candidate physical placement or reconstruction plan; do not execute pack, object, ref, GC, or history changes.
6. `REGISTER_DEFERRED_PUSH`: create or update one durable, hash-bound push obligation and its exact `$complete-deferred-git-push` handoff when the requested push is blocked, deferred, interrupted, unauthorized, or not remotely verified.

This E2 skill does not itself perform isolated materialization or a live Git mutation. Route E4 branch execution, exact remote-OID closure, and later terminal authoritative rechecks only to `$complete-deferred-git-push` using its `w7tp-deferred-git-push-request/1.0` input contract. The route and queue ACK are delivery evidence, never activation, authority, or proof that a push ran. Retain the originating AI's delivery responsibility until the executor supplies current authoritative terminal evidence.

## Build the smallest sufficient index

Require the packet contract to carry:

- full-envelope `identity_root_ref`, active Seat binding, receiver identity/version, nonce, logical time, expiry, and member boundary;
- packet-level irreversible decision reference plus system-level lineage, transition, namespace, and evidence coordinates;
- Git repository namespace, object format, object type, expected size, expected OID, source/base OIDs, path bytes, file mode, and ref scope when applicable;
- deterministic generator/rule hashes, complete lookup closure, reconstruction limits, exact-byte or equivalent-state acceptance, and packet-carried verification;
- D7 fail-closed behavior and D8 `CANDIDATE_ONLY` with canonical writes denied.

Do not embed credentials, member plaintext, raw ADI content, H64-TD codebooks or recovery material. Use opaque references and hashes.

## Route immediately and deterministically

`scripts/git_review_gate.py` returns only:

- `SAFE_PUSH_CANDIDATE`: all files are new, regular, hash-matched candidate files under one isolated root; operations are declarative/read-only; no protected Git path or authority claim appears.
- `REVIEW_REQUIRED`: the proposal is bounded but includes executable, replacement, isolated materialization, candidate-ref, or other non-trivial effects.
- `HOLD_PROTECTED_GIT_EFFECT`: the proposal touches live object storage, existing refs, history rewrite, force push, GC/prune, deletion, canonical pointer, identity/Seat, or self-asserted activation.

Only non-control declarative Markdown/JSON/YAML below candidate `evidence/`, `references/`, `reports/`, or `schemas/` may receive the safe route. Root files, other directories, agent instruction/control files and directories, candidate manifests, and Python always require review; process/network/dynamic-execution capability and CI/autoload locations are HOLD.

A safe route is E2 review evidence only. It does not grant remote credentials, become a Total Field receipt, or authorize any orchestrator to push. When delivery includes a remote push, create the hash-bound acknowledged handoff described below and route E4 exclusively to `$complete-deferred-git-push`.

## Make every blocked push a delivery obligation

Treat `HOLD`, missing credentials, remote rejection, dirty-worktree collision, concurrent-writer drift, failed tests, missing review, expired authority, and session interruption as delay states, never silent cancellation.

When the requested push is not remotely verified in the same run:

1. Create or update exactly one closed `w7tp-deferred-git-push-obligation/1.2` record in a governed durable queue that is not solely stored inside the unpushed target repository. Obtain a separate immutable E2 obligation ACK whose exact path and SHA-256 are bound into the record. Never trust `store_ref`, `outside_target_repo`, or an ACK string without loading the real ACK from the activated executor queue and measuring containment against the target repository and Git common directory. If no durable queue can acknowledge it, return `HOLD_QUEUE_UNAVAILABLE`; never pretend that a local timestamp is a schedule. Never create duplicate obligations for the same Founder intent, repository, target ref, expected old OID, source OID, and change-set hash.
2. Bind a closed `executor_handoff` to exact skill `$complete-deferred-git-push` version `1.0.0`, input contract `w7tp-deferred-git-push-request` version `1.0`, one shared `dgp-[0-9a-f]{64}` obligation/ticket coordinate, executor request hash, its distinct executor `ENQUEUED` ACK reference/hash, handoff state, three fixed executor responsibilities, non-activation state, and its canonical SHA-256. Derive the DGP request `origin_intent_sha256` from closed `w7tp-e2-to-e4-origin-envelope/1.0`, which includes the raw Founder intent coordinates plus identity/member/Seat/Receiver and test-receipt coordinates; changing any of them must change request identity and ticket. Require `--executor-queue-trust-config`: one canonical self-hashed root-owned regular file under `w7tp-e2-executor-queue-trust-config/1.1`, exact mode `0444`, link count one. It pins a root-owned non-group/world-writable parent by canonical realpath/device/inode/mode, one exact child basename, the distinct nonroot queue owner UID/username, one exact nonroot validator UID/username, and one dedicated reader GID/name. The state root and every queue directory must be owner/reader-group `0750`; marker, request, event, ACK, and receipt files must be owner/reader-group `0440`. The live validator/producer UID must exactly equal the configured validator, differ from root and the queue owner, belong through effective or supplementary groups to the configured reader GID, and have zero effective and permitted Linux capabilities (`CapEff=0`, `CapPrm=0`) in both process and current-thread status. Open the parent, state root, and all request/event/ACK evidence by descriptor plus bounded `openat`/`O_NOFOLLOW`; check exact owner and reader GID on every fd, then reopen the named parent and child and require the pinned identities. Never trust caller-filled references, mutable pathname containment, or an arbitrary reader-group member whose UID is not the configured validator.
3. If no exact source commit OID exists, enqueue an acknowledged executor ticket as handoff state `WAITING_EXACT_TARGET`. Keep refspec and source execution closure unresolved, carry no executor lease, and never substitute `HEAD` or another current commit. It may become executable only through a newly hash-bound exact successor acknowledged by the executor.
4. Record one opaque `responsible_agent_ref`. The AI that blocks the push remains accountable for diagnosis, safe repair, resumption, handoff, and closure; delegation does not erase ownership.
5. Bind the repository, remote-name and endpoint hash, one exact `refs/heads/*` target, source commit/tree and reachable-object closure when known, expected remote old OID, exact refspec, exact file paths and SHA-256 values when resolved, route decision, blocker evidence, repair plan, authorization state, queue ACK, execution lease, next-attempt time, resume trigger, attempt count, deadline, and workloop reference.
6. Perform every authorized, reversible E2 repair automatically. Ask the Founder only for the one irreducible decision or credential action that automation cannot perform.
7. Use an available durable scheduler. If no scheduler is callable, persist the obligation and handoff as `PUSH_OBLIGATION_OPEN`, set an exact `next_attempt_at` and `resume_trigger`, and state plainly that background execution is not active. Never claim a schedule exists merely because a timestamp was written.
8. Let `$complete-deferred-git-push`, not this skill, re-resolve endpoint/ref state, validate the exact source and causal scope, isolate dirty state, enforce its E4 authority gate, perform the single-ref fast-forward update, independently read back the remote OID, and run current and later authoritative terminal rechecks.
9. For a claimed historical `PUSHED_VERIFIED` record, load the executor event chain and exact receipt bytes only as integrity coordinates. This E2 validator does not reproduce the executor's reservation, final validation, consume-ACK continuity, exact server CAS, protected-state, or live Receiver/remote state machine, so it returns `HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED` with `terminal_readback_verified=false`. Only `$complete-deferred-git-push` may validate that terminal and perform the current authoritative recheck.

Treat legacy `w7tp-deferred-git-push-obligation/1.0` and `/1.1` records as read-only evidence. The validator returns `HOLD_LEGACY_PUSH_OBLIGATION_MIGRATION_REQUIRED`; do not synthesize a trust root, independent ACK, handoff, or missing fields, and do not route E4 from the legacy record. Create a reviewed `/1.2` successor instead.

`HOLD`, `REVIEW_REQUIRED`, permission failure, timeout, and session end cannot close or discard an obligation. The only terminal states are:

- `PUSHED_VERIFIED`, with remote-ref readback and exact pushed-file evidence;
- `CANCELLED_BY_FOUNDER`, with an explicit Founder cancellation receipt;
- `SUPERSEDED`, with a live successor obligation reference preserving lineage.

Validate every obligation before handoff:

```bash
python3 scripts/validate_deferred_push.py obligation.json \
  --executor-state-root /absolute/trusted/executor-state-root \
  --executor-queue-trust-config /absolute/root-issued/executor-queue-trust.json
```

A validation PASS proves only the closed E2 record plus externally loaded request, initial executor ACK, and independent E2 obligation ACK under the root-issued queue trust config. Missing, expired, unsafe, owner-mismatched, capability-bearing, root-executed, parent-replaced, or inode-drifted config/state returns `HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE`. This software cannot prove that a root-capable producer never existed before the live check: deployment must enforce `TRUST_PROVISIONER_AND_OBLIGATION_PRODUCER_SEPARATION_REQUIRED`, and the trusted provisioner must not preinstall bind/mount aliases that overlap the target repository. A claimed pushed record remains `HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED` with `terminal_readback_verified=false` until `$complete-deferred-git-push` validates its full terminal state machine and performs the current Receiver and remote-OID recheck. The executor still requires its own exact authority, activation configuration, remote preflight, and live lease before any E4 push.

## Enforce a single Receiver

Producers may append candidate index events only. The local validator verifies packet shape, canonical event hash, expiry, Git coordinates, lookup closure, reconstruction contract, and acceptance mode. One declared Receiver must separately resolve identity+Seat activity, replay-registry state, event sequence, previous-event existence, and its own authority. It may issue candidate evidence; it cannot move production refs or promote canonical state.

Use `refs/adi/candidates/*` only as a proposed isolated namespace. Do not create it under this skill. Promotion requires a separate exact Founder instruction and valid D8 receipt.

## Validate before handoff

For an index packet:

```bash
python3 scripts/validate_git_index.py packet.json
```

For a change-routing packet:

```bash
python3 scripts/git_review_gate.py change-set.json --repo-root /exact/repository/root
```

For this skill package:

```bash
python3 scripts/test_skill.py
python3 /path/to/quick_validate.py /path/to/govern-8d-adi-git-index
python3 /path/to/validate_skill_manifest.py /path/to/govern-8d-adi-git-index
```

Do not claim success from exit code alone. Preserve the JSON results, input hashes, Git refs/OID evidence when applicable, unchanged-state proof, and red-team record.

## Return the governed result

```text
STATE=<PASS_READONLY | PASS_CANDIDATE_ARTIFACT | SAFE_PUSH_CANDIDATE | REVIEW_REQUIRED | HOLD_PROTECTED_GIT_EFFECT | HOLD_QUEUE_UNAVAILABLE | HOLD_LEGACY_PUSH_OBLIGATION_MIGRATION_REQUIRED | PUSH_OBLIGATION_OPEN | WAITING_EXACT_TARGET | READY_TO_PUSH | PUSHED_VERIFIED | PRECONDITION_MISSING>
OPERATION=<selected operation>
GIT_BOUNDARY=<physical placement only | new candidate history | unchanged>
INDEX=<packet or artifact reference and SHA-256>
RECONSTRUCTION=<EXACT_BYTES | EQUIVALENT_STATE | NOT_RUN>
RECEIVER=<identity/version/Seat binding or missing prerequisite>
TOTAL_FIELD_ROUTE=<route and evidence reference>
PUSH_OBLIGATION=<record, responsible agent, next attempt, scheduler state, blocker, or NONE>
EXECUTOR_HANDOFF=<$complete-deferred-git-push ticket/request/ACK hashes, handoff state, activation NOT_GRANTED, or NONE>
REMOTE_RECEIPT=<verified remote OID and evidence or NONE>
CANONICAL=<UNCHANGED>
NEXT=<one exact action or NONE>
```

Never report `ACTIVE`, `MATERIALIZED`, `PUSHED`, `PUSHED_VERIFIED`, or `CANONICAL` without the corresponding external receipt. Never infer activation from a valid handoff or queue ACK. Never use a push prohibition as permission to forget delivery.
