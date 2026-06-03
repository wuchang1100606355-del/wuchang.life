# Member Vault Sealed Mode

版本：2026-05-11

## Mode

The member information database is physically sealed after creation.

It may only be unsealed for:

1. Member personal device lost/changed: five-metric code check and note.
2. ROC government agency official document order under lawful authority.
3. Data subject erasure or correction claim.

## Not Allowed

- daily query
- AI memory
- cloud sync
- external AI plaintext processing
- POS/Odoo live source
- development test fixture

## Required Event

Every unseal operation must generate:

- reason type
- minimum scope
- pre-unseal SHA256
- post-unseal SHA256
- audit record
- resealed=true

