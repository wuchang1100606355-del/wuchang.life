# Source acquisition contract

## Goal

Create a reproducible, read-only coordinate for an external capability source before making architectural claims.

## Evidence priority

1. Exact repository locator.
2. Exact release or tag when the user is evaluating a released artifact.
3. Commit and tree identity.
4. License and NOTICE/COPYING material.
5. SECURITY or threat-model documentation.
6. Root manifests and build metadata.
7. Entrypoints and implementation files for the capability under study.
8. Capability-relevant tests or upstream CI evidence.

## Git coordinate

Prefer recording:

```text
SOURCE_REPOSITORY
SOURCE_REMOTE
SOURCE_BRANCH
SOURCE_TAG
SOURCE_COMMIT
SOURCE_TREE
SOURCE_SNAPSHOT_SHA256
WORKTREE_DIRTY
STATUS_SHA256
LICENSE_FILES
```

A release page alone does not prove the local checkout matches the release. A matching tag name alone does not prove the underlying tree if the commit/tree was not resolved.

## Evidence status

Use these statuses exactly:

- `DOCUMENTED_ONLY`: stated in docs but implementation not inspected.
- `IMPLEMENTED`: implementation source supports the claim.
- `UPSTREAM_TESTED`: source project reports tests/CI for the pinned version; not rerun here.
- `VERIFIED_CURRENT_RUN`: this session executed a relevant verifier/test against the pinned source.
- `UNKNOWN`: evidence is missing or ambiguous.

Do not promote `UPSTREAM_TESTED` to `VERIFIED_CURRENT_RUN`.

## Clean-room boundary

When the user asks to reproduce an effect without depending on the source implementation:

1. Let the analyst inspect the source and produce only neutral behavior/effect requirements.
2. Record provenance and license in the research packet.
3. Make the implementation contract independent of source code structure, symbol names, prose, tests, or file layout.
4. Have the target implementer work from the effect contract and W7TP target state.
5. Validate behavior against independently stated acceptance rules.

If direct code reuse is desired, verify the actual license first and preserve required attribution/notices. Open availability is not equivalent to unrestricted reuse.

## Network and execution boundary

Static acquisition may use public web/repository reads. Do not run project install scripts, hooks, package managers, containers, migrations, services, or tests unless separately authorized. Repository metadata commands and read-only parsing are allowed when they have no project side effects.
