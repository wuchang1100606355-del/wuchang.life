# Deferred Git push responsibility contract

## Founder rule

When an AI refuses, blocks, delays, or cannot verify a requested Git push, the push becomes a durable delivery obligation. Safety may delay execution; it must not erase the task, transfer the burden back to the Founder, or permit `HOLD` to masquerade as completion.

This skill owns the E2 obligation record and accountability lineage. Route all E4 execution, exact remote-OID readback closure, and terminal authoritative rechecks to the existing `$complete-deferred-git-push`. A route, validator PASS, ticket, or queue ACK is not activation and grants no execution authority.

## Version boundary

Write schema `w7tp-deferred-git-push-obligation/1.2`. Requiring a root-issued queue trust config, exact repository/authority/test hashes, and an independently loaded E2 obligation ACK breaks `/1.1`; both `/1.0` and `/1.1` remain read-only evidence only. Their validation always returns `HOLD_LEGACY_PUSH_OBLIGATION_MIGRATION_REQUIRED`. Never add defaults, invent a trust root, or execute a legacy record; create a reviewed `/1.2` successor with real external evidence.

## Required closed record

The `/1.2` validator rejects unknown or missing keys at every object boundary. Bind:

- `obligation_id`, Founder intent reference and SHA-256, responsible agent, workloop, identity root, member, fixed Seat, and exact `TOTAL_FIELD_8D_ADI_GIT_INDEX_RECEIVER` reference;
- state, Total Field route, canonical repository root and fingerprint SHA-256, remote name, endpoint SHA-256, one exact `refs/heads/*` target, source commit/tree, reachable-object closure hash, expected remote old OID, exact refspec, and object format;
- `change_scope_state`; when resolved, every exact path, status, and SHA-256 plus one deterministic change-set hash;
- blocker code/evidence, ordered repair plan, automation boundary, and the one human action when irreducible;
- durable queue store outside both target repository and Git common directory, request idempotency key, independent E2 ACK path and SHA-256, scheduler state, created time, next attempt, deadline, resume trigger, attempt count, bounded automatic retry limit, executor lease, and lease expiry;
- source test receipt reference/SHA-256 and the exact authorization reference/expiry, Total Field decision reference/receipt SHA-256/expiry, and required scope SHA-256;
- fast-forward-only, no force, no history rewrite, no unrelated dirty-file inclusion, remote readback, rollback, push-effect, and stop-condition facts;
- one closed `executor_handoff` and terminal evidence or a live successor reference.

Unknown identity, Seat, Receiver, path scope, source commit, or remote base may be recorded as `UNKNOWN_UNVERIFIED` only while blocked. An unresolved record can never enter `READY_TO_PUSH`.

## Hash-bound executor handoff

Use exactly these immutable routing identities:

```text
executor_skill_ref=$complete-deferred-git-push
executor_skill_version=1.0.0
input_contract=w7tp-deferred-git-push-request
input_contract_version=1.0
activation_state=NOT_ACTIVATED_BY_E2_ROUTING
```

Bind `obligation_id`, `executor_ticket_id`, `executor_request_sha256`, `executor_queue_ack_ref`, and `executor_queue_ack_sha256`. In `/1.2`, the obligation coordinate and both handoff/request ticket coordinates must be the same exact `dgp-[0-9a-f]{64}` identity; this is the external request's verifiable obligation back-reference. The obligation queue ACK and executor queue ACK are distinct evidence: `queue_store.append_only_ack_ref` acknowledges the E2 responsibility record, while `executor_queue_ack_ref` must be exactly `tickets/<dgp-64hex>/events/00000000000000000001.json` in the trusted `$complete-deferred-git-push` state root. Reusing one reference for both is invalid. Require the exact ordered responsibility set:

```text
E4_SINGLE_REF_FAST_FORWARD_EXECUTION
TERMINAL_AUTHORITATIVE_RECHECK
REMOTE_EXACT_OID_READBACK_CLOSURE
```

Use hash contract `SHA256_CANONICAL_JSON_EXCLUDING_EXECUTOR_HANDOFF_SHA256_V1`: canonical JSON uses sorted keys, UTF-8, no insignificant whitespace, and hashes the complete closed obligation after removing only `executor_handoff.handoff_sha256`. A matching self-hash proves integrity, not authority. The validator must use both `--executor-state-root` and `--executor-queue-trust-config` to safely load canonical immutable `request.json`, the first `ENQUEUED` event, and the independent E2 ACK. It verifies their exact closed schemas, hashes, ticket identity, ACK semantics, obligation back-reference, repository and Git-common-dir containment, and the complete repository/identity/authority/test/effect envelope. Caller-filled references alone always return `HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE` or `HOLD_EXTERNAL_EXECUTOR_ACK_UNVERIFIED`; they never establish an executable route.

## Root-issued queue trust and independent E2 ACK

The CLI accepts one absolute canonical trust-config path. Schema `w7tp-e2-executor-queue-trust-config/1.1` is a closed canonical JSON object with self-hash contract `SHA256_CANONICAL_JSON_EXCLUDING_CONFIG_SHA256_V1`. The `/1.1` parent-anchor fields are a breaking trust-boundary change; `/1.0` does not activate this validator. The file must be a root-owned regular file, link count one, exact mode `0444`, and must remain the same inode and metadata throughout a same-descriptor read. It binds:

- one exact root-owned, non-group/world-writable, non-symlink parent directory by canonical realpath, device, inode and mode;
- one bounded child basename and the exact state-root realpath, device, inode, mode, expected non-root queue-owner UID/username;
- one exact non-root validator UID/username and one dedicated reader-group GID/name, all resolved against the operating-system account and group databases;
- the exact `.w7tp-deferred-push-queue-v1` marker path, bytes and SHA-256;
- `$complete-deferred-git-push@1.0.0`, request schema `w7tp-deferred-git-push-request/1.0`, event schema `w7tp-deferred-git-push-event/1.0`, and initial event kind `ENQUEUED`;
- one opaque activation reference, canonical `valid_from`/`expires_at` window, and activation-receipt reference/SHA-256.

The live validator/producer process effective UID must exactly equal the configured validator UID, be non-root, and differ from the configured queue owner. Its effective or supplementary group set must include the exact configured reader GID. It reads both `/proc/self/status` and `/proc/thread-self/status`, rejects unreadable, duplicate, malformed, or disagreeing capability fields, and requires `CapEff=0` and `CapPrm=0`. The state root and every queue subdirectory must be exact owner/reader-group mode `0750`; marker, request, event, independent ACK, and readback-receipt files must be exact owner/reader-group mode `0440`. Every opened fd must carry the configured queue-owner UID and reader GID. The state root must also equal the configured device/inode and remain outside both the measured target repository and its measured Git common directory. An arbitrary member of the reader group cannot validate because its UID does not equal the configured validator.

The validator opens the pinned parent directory first, opens only the exact child basename with `openat`/`O_NOFOLLOW`, and loads marker, request, event chain, independent ACK, and terminal-integrity evidence only through that descriptor tree. At the end of every load it checks the held parent/root, reopens the child through the held parent, then reopens the canonical parent path and child and requires the original device/inode/mode/owner identities. A parent rename, child rename, path replacement, root-owned or same-euid queue, stale config, unsafe link/mode, marker drift, owner/username mismatch, state-root identity drift, contract drift, or missing config returns `HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE` or the bounded external-evidence HOLD; mutable pathname assertions never establish containment.

The runtime gate proves only the current unprivileged process state. Deployment retains `TRUST_PROVISIONER_AND_OBLIGATION_PRODUCER_SEPARATION_REQUIRED`: the root trust provisioner, non-root obligation validator/producer, and distinct non-root executor queue owner must be separate principals. A trusted root provisioner must not preinstall bind/mount aliases that overlap the target repository; a root administrator could create such an alias before the capability-free validator runs, so this remains an explicit activation-host control rather than a software claim.

The independent E2 ACK is canonical schema `w7tp-e2-deferred-push-obligation-queue-ack/1.0` at `e2-obligation-acks/<dgp-64hex>.json`. It is not the executor's initial event. Its closed payload binds its own immutable ACK hash plus the obligation core, handoff payload, ticket, exact request/event paths and hashes, trust-config hash, Founder intent, repository/fingerprint, identity/member/Seat/Receiver, test receipt, authorization scope, effect scope and change set. Missing, tampered, self-authored, cross-subject, or cross-effect ACK evidence remains HOLD even if every caller-provided hash is recomputed.

The existing DGP request schema has one `origin_intent_sha256` coordinate. For this E2 handoff it must equal SHA-256 of canonical closed `w7tp-e2-to-e4-origin-envelope/1.0`, containing `founder_intent_ref`, `founder_intent_sha256`, `identity_root_ref`, `member_ref`, `seat_binding_ref`, exact Receiver, and test-receipt reference/SHA-256. This makes those coordinates part of request idempotency and the `dgp-64hex` ticket, rather than relying only on a replaceable document assertion or ACK. A subject or test change therefore requires a different exact executor ticket.

Use exactly one handoff state:

- `WAITING_EXACT_TARGET`: no exact source commit exists; the executor ticket is durable but non-executable.
- `READY_FOR_E4_VALIDATION`: exact source input is available for the executor's own independent gates; this is still not activation.
- `TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED`: a pushed record routes current and later remote/Receiver rechecks back to the executor.
- `NO_E4_ACTION_TERMINAL`: Founder-cancelled or validly superseded record; no push action is routed from that record.

Reject a different skill, contract, version, obligation back-reference, ticket/request/ACK binding, responsibility list, activation value, unknown key, or hash. Recomputing a hash cannot make a semantically wrong executor or activation claim valid.

## WAITING_EXACT_TARGET

When the bounded change exists but no exact source commit OID exists:

1. Keep the obligation state open and set handoff state `WAITING_EXACT_TARGET`.
2. Keep `source_oid`, `refspec`, commit, parent, tree, reachable-object hash, and reviewed-history hash as `UNKNOWN_UNVERIFIED`.
3. Set blocker code `WAITING_EXACT_TARGET` and resume trigger `EXACT_TARGET_COMMIT_AVAILABLE`.
4. Carry no executor lease and never substitute `HEAD`, the enqueue-time HEAD, or any older OID.
5. A waiting record is valid only after the trusted queue request, executor `ENQUEUED` event, and independent E2 ACK all verify; this proves durable non-executable responsibility, not authority.
6. After the original repository forms and validates an exact commit, create and fsync a new executor request and both distinct ACKs first. Only a hash-bound successor may then supersede the waiting record.

`WAITING_EXACT_TARGET` cannot be `READY_TO_PUSH` or `PUSHED_VERIFIED`, cannot carry executable source closure, and cannot become executable by editing the old handoff.

## Obligation state machine

```text
PUSH_OBLIGATION_OPEN
  -> BLOCKED_REPAIRING
  -> READY_FOR_AUTHORIZATION
  -> READY_TO_PUSH
  -> PUSHED_VERIFIED
```

Exceptional terminal transitions are only:

```text
* -> CANCELLED_BY_FOUNDER  # explicit cancellation receipt required
* -> SUPERSEDED            # live acknowledged successor required
```

Permission denial, authentication failure, remote drift, test failure, review HOLD, rate limit, offline node, timeout, context compaction, agent/session termination, or failed terminal recheck is non-terminal. Preserve the obligation identity, append evidence, and calculate one next safe attempt.

## Scheduler truth

Use exactly one scheduler state:

- `ACTIVE_DURABLE_SCHEDULER`: an observable external scheduler/job reference exists;
- `HANDOFF_RESUME_REQUIRED`: no background scheduler is available; the durable record and exact resume trigger exist;
- `TERMINAL`: the obligation has valid terminal evidence.

A timestamp without an observable scheduler is not an active schedule. A queue record whose only copy is inside the unpushed target repository is not durable. Without an external queue ACK, return `HOLD_QUEUE_UNAVAILABLE`.

## E4 executor boundary and closure

Before an E4 mutation, `$complete-deferred-git-push` must independently validate its closed request, authority and activation configuration, identity/member/Seat/Receiver lease, remote endpoint and expected old OID, exact source and causal scope, file hashes, tests, dirty-state isolation, hooks/LFS/submodule/tag/CI effects, and a single-ref fast-forward update. `READY_TO_PUSH` requires `authorization.required=true`, a canonical unexpired receipt window, and a canonical unexpired executor lease; E2 still returns `HOLD_EXTERNAL_EXECUTOR_STATE_UNVERIFIED` until the executor's current authority check. Any mismatch remains HOLD. This E2 skill must not reproduce or bypass that mutation flow.

After a push attempt, only the executor may independently read the exact remote ref, require the remote OID to equal the source OID, reconcile the authoritative Receiver consumption, and issue the receipt used by this obligation. The E2 validator may securely read an executor event chain and exact receipt bytes to check path/hash/core-coordinate integrity, but it does not reproduce the executor's reservation, final validation, consume ACK and revocation-epoch continuity, server CAS, protected-state comparison, or live Receiver/remote query. It must report `terminal_readback_verified=false` and `HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED`; if no external root is supplied it routes `HOLD_TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED`. Either HOLD preserves routing to `$complete-deferred-git-push`, including when the external root or initial ACK is damaged.

A local terminal is historical evidence, not permanent authority. Route every later terminal check to `$complete-deferred-git-push`; if its authoritative remote/Receiver recheck reopens HOLD, keep responsibility due and do not continue to claim current terminal closure.

## Ownership

The blocking AI remains `responsible_agent_ref` until current terminal evidence. A new agent or node may execute or verify the work, but the handoff preserves obligation ID, request/ACK hashes, evidence, next action, due time, and responsibility lineage. Never make the Founder rediscover paths, hashes, commands, or prior failures that automation already observed.
