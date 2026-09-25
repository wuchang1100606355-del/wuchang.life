# Delegation contract

Each grant should carry:

- `grant_id`
- `parent_grant_id` (null only for root)
- `grantor`
- `grantee`
- `capabilities`
- `targets`
- `purposes`
- `effect_classes`
- `valid_from`
- `expires_at`
- `delegation_allowed`
- `revocable`
- `authority_ref`

Root grants additionally require `founder_grant_ref`.

Validation proves structural attenuation only. Authenticity, signature validity, revocation state, and current D8 authority must be established by the active W7TP authority mechanism.
