# Git object and history boundary

## Fixed invariants

Git has four object types: blob, tree, commit, and tag. An object name is derived from its canonical object type, size, and exact content. Existing-OID reconstruction therefore requires exact bytes, not a semantically or functionally similar result.

- Physical pack representation may change without changing object OIDs. Git may store objects loose, compressed whole, or as deltas in packfiles.
- MIDX maps immutable OIDs to packfiles and offsets. Commit-graph accelerates traversal but does not replace the object database.
- A changed tree path, name, mode, or referenced object produces a new tree OID.
- A changed commit tree, parent list/order, author, committer, timestamp, or message produces a new commit OID. Descendants referring to it normally change as well.
- Working-tree relocation can be a new candidate commit while preserving old history. Rewriting all historical paths is history rewriting.

Official primary references:

- Git objects: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
- Pack format: https://git-scm.com/docs/gitformat-pack
- Pack construction: https://git-scm.com/docs/git-pack-objects
- Repack: https://git-scm.com/docs/git-repack
- Multi-pack index: https://git-scm.com/docs/multi-pack-index
- Commit graph: https://git-scm.com/docs/commit-graph
- Partial clone and promisor: https://git-scm.com/docs/partial-clone
- Repository layout and alternates: https://git-scm.com/docs/gitrepository-layout
- Object/connectivity verification: https://git-scm.com/docs/git-fsck
- Pack verification: https://git-scm.com/docs/git-verify-pack

## Safe sidecar placement

Use the 8D ADI index as an external placement/materialization layer:

```text
immutable Git OID
  -> ADI state/lineage/intent coordinate
  -> deterministic lookup and reconstruction contract
  -> quarantine materialization
  -> Git-native OID/type/size verification
  -> candidate receipt
```

Git partial clone/promisor can request missing objects by OID, but it does not natively consume arbitrary generative recipes. A bridge Receiver must materialize a valid exact Git object or pack. An equivalent-state output belongs under a new candidate OID.

Never hand-edit `.pack`, `.idx`, `.git/objects`, or `.promisor`. Never assume an external ADI reference protects an object from Git GC; Git reachability must be governed through Git-native mechanisms in an isolated execution workflow.
