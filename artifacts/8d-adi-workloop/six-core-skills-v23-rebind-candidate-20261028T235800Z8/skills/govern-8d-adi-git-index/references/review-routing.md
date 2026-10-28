# Immediate Total Field review routing

## Routes

### SAFE_PUSH_CANDIDATE

All conditions must hold:

- the change set is a JSON object, operations are a string array, and `candidate_root` names a non-empty path narrower than the repository root;
- every change is `A` and resolves under one declared isolated candidate root;
- each declared `A` path is absent from a checksum-valid, supported Git index; an unavailable, split, sparse-prefix, or unsupported index cannot receive the safe route;
- every entry is a regular non-symlink file with a matching SHA-256 and bounded size;
- safe-route file types are limited to declarative Markdown, JSON, YAML, or YML;
- operations are limited to new skill instructions, schemas, manifests in candidate state, tests, evidence, or read-only validation;
- no credential marker, protected-data payload, self-asserted Total Field receipt, active lifecycle, live Git path, deletion, overwrite, rename, executable mode, network action, or state-changing Git command appears.

The gate checks every path component for symlinks before resolution. It reads only Git index v2/v3 bytes and verifies the index checksum; it never invokes Git, reads object contents, or mutates repository state.

Malformed top-level values, operation entries, manifest objects, or lifecycle objects fail closed instead of raising an exception.

Every Python file is `REVIEW_REQUIRED`, even when AST inspection finds no dangerous capability. Process, network, dynamic execution, protected deletion, and similar imports/calls are `HOLD_PROTECTED_GIT_EFFECT`. CI/autoload locations such as `.github/workflows`, `.gitlab-ci.yml`, and other protected runner roots are also HOLD.

Behavioral control files (`SKILL.md`, `AGENTS.md`, `CLAUDE.md`, Copilot/Cursor/Windsurf rules, `agents/openai.yaml`, and `total-field-skill-manifest.json`) and control directories (`.codex`, `.cursor`, `.claude`, `.continue`, `.vscode`, `.devcontainer`, and related agent roots) always require review because materialization or a local tool can load them and alter invocation/governance behavior. Ordinary evidence, reference documents, and non-autoload schemas may still receive the safe route.

To avoid an endless and incomplete list of autoload filenames, the safe route also uses a positive placement allowlist: a file must be below `evidence/`, `references/`, `reports/`, or `schemas/` inside the candidate root. Root files and every other directory require review even when their suffix is declarative.

This route authorizes no credentials or remote mutation. If the requested delivery includes a remote update, create one externally acknowledged, hash-bound `$complete-deferred-git-push` handoff under `w7tp-deferred-git-push-obligation/1.2`; that route is not activation. A valid acknowledgement requires root-issued trust config `/1.1`, its pinned root-owned parent, exact non-root queue owner, exact different non-root validator UID, and dedicated reader GID; every evidence fd must match that owner/GID/mode contract. Only the configured capability-free validator loads the real immutable request, initial executor `ENQUEUED` event, and independent E2 ACK through the descriptor tree. Caller-filled queue strings, another reader-group member, a producer-owned queue, mutable pathname containment, or a declared `outside_target_repo` boolean cannot establish delivery.

### REVIEW_REQUIRED

Use for bounded changes that are not immediately harmless: any Python source, behavioral control file, modification of an existing file, isolated materialization, temporary pack creation, candidate ref creation, relocation commit, executable integration, dependency changes, or a file the deterministic scanner cannot classify.

### HOLD_PROTECTED_GIT_EFFECT

Use immediately for:

- `.git/objects`, pack/index hand edits, live refs/tags/HEAD, canonical pointer, production branch, or active authority changes;
- rebase/filter-history/parent rewrite, force push, reset-hard, GC/prune/expire, deletion, or replacement of originals;
- manual promisor marking, unverified alternates, identity/Seat mutation, credential/member plaintext, or self-issued Total Field receipt;
- equivalent-state output presented under an existing Git OID.

## Effect boundary

Safe candidate files are E2. Actual remote push is a persistent external effect and remains governed by the exact current authorization. Live Git, identity, canonical, formal, or authority-changing effects require the stronger applicable gate and cannot be bundled into a safe push. E4 execution, remote-ref OID readback closure, and terminal authoritative recheck route only to `$complete-deferred-git-push`; neither the outer orchestrator nor this E2 skill directly pushes.
