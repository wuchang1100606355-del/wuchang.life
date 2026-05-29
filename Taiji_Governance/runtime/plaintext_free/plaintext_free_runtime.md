# Plaintext-Free Context Runtime

## Rule

Raw plaintext is not executable memory. Runtime stores tensor summaries, hashes, redacted summaries, topology state, authority vectors, and audit lineage.

## Allowed Runtime Memory

- `packet_hash`
- `parent_hash`
- `nonce`
- redacted summary
- TensorPacket vectors
- audit snapshot id
- topology node id
- rollback horizon

## Blocked Runtime Memory

- service account JSON
- OAuth token
- private key
- password
- session cookie
- Odoo member plaintext
- Google private data
- ChatGPT raw export content
- raw customer speech unless classified as non-sensitive and approved

## Enforcement

Any executable packet that requires raw plaintext secret or personal data enters `deadbox`.
