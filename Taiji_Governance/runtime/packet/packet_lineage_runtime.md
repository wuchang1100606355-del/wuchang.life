# Packet Lineage Runtime

Packet lineage uses:

- `packet_hash`
- `parent_hash`
- `nonce`
- audit event id
- rollback id
- topology vector hash
- authority vector hash

Lineage allows replay inspection without preserving raw plaintext.

Parentless packets are allowed only when `parent_hash = root` and risk is L0/L1.
