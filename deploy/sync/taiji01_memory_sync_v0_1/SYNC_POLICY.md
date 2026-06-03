# Taiji01 Memory Sync Policy v0.1

## Authority

`taiji01` is the canonical node for Taiji memory and knowledge storage.

Canonical memory databases:

1. `data/f5_core_memory.db`
2. `data/wuchang_5d_knowledge_vault.db`

Auxiliary audit / metric ledger:

- `data/ledger/metric_memory.sqlite3`

The local Linux workspace may keep cache copies for speed, but those copies are not authoritative.

## Sync Rules

- Default action is status check only.
- Pull from `taiji01` to local cache is allowed for efficiency.
- Push from local to `taiji01` is disabled unless `TAIJI_ALLOW_MEMORY_PUSH_TO_01=true` is set explicitly.
- No `data/secrets`, service account JSON, tokens, private keys, or member plaintext files are included.
- SQLite integrity check must pass before and after sync.
- Existing local files are backed up before replacement.
