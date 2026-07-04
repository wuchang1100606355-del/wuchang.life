# UX CLOUD MINIMALITY GATE

STATE: POLICY_BOUNDARY_ATTACHED
MODE: DRY_RUN_AND_FUTURE_PRODUCTION_GATE

## Hard Rules

1. User experience must not be lower than cloud-level UX.
2. Local 0.5-2B LLM cannot be used as an excuse for poor UX.
3. Cloud dependency must be precise, minimal, and non-reconstructable.
4. Cloud receives candidate packets only.
5. Cloud never receives enough data to reconstruct:
   - user identity
   - raw browser state
   - care context
   - address
   - payment context
   - member plaintext
6. Cloud never performs final decision.
7. Final decision returns to ΩGI Total Field.

## Allowed Cloud Packet

- intent_hash
- boundary_ref
- schema_ref
- verifier_ref
- candidate_task_summary
- redacted evidence refs
- non-sensitive constraints

## Forbidden Cloud Packet

- natural person plaintext
- member plaintext
- raw browser state
- address
- payment or financial detail
- care or welfare context
- full Odoo record payload
- H64-TD codebook/mapping/table/rules
- DB password/token/private key

## Effect on Wish Tree ADI Sidecar

WISH_TREE_ADI_DRY_RUN_ALLOWED: TRUE
CLOUD_CANDIDATE_ALLOWED: TRUE_IF_PACKETIZED
PRODUCTION_WRITE_ALLOWED: FALSE
ODOO_INSTALL_ALLOWED: FALSE
SERVICE_RESTART_ALLOWED: FALSE
FINAL_AUTHORITY: OMEGA_GI_TOTAL_FIELD
