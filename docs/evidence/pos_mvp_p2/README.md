# POS MVP P2 Candidate Reader Evidence

STATE=POS_P2_CANDIDATE_READER_SPEC

Scope:
- Read latest `POS_SANDBOX_ORDER_CANDIDATE.json` from sandbox run outputs.
- Project items, subtotal, discount, payable amount, voice reply, rule refs, and d8 ref.
- Produce human confirm gate output with `CONFIRM_DRY_RUN`.

Safety:
- FORMAL_DB_WRITE=false
- FORMAL_POS_WRITE=false
- PAYMENT_CAPTURE=false
- SERVICE_RESTART=false
- DEPLOY=false
- PRODUCTION_RELEASE=false
- SECRET_READ=false
- MEMBER_PLAINTEXT_READ=false

Verifier:

```bash
bash scripts/verify/verify_pos_mvp_p2_candidate_projection.sh
```

Rollback notes:
- Remove `tools/w7tp_pos_p2_candidate_projection.py`.
- Remove `scripts/verify/verify_pos_mvp_p2_candidate_projection.sh`.
- Remove `docs/evidence/pos_mvp_p2`.
- Remove `packets/pos_mvp/POS_MVP_P2_CANDIDATE_READER_PACKET.json`.
- Runtime outputs are isolated under `runtime/sandbox/pos_mvp_p2_projection_run/`.
- Current runtime outputs are isolated under `runtime/sandbox/pos_mvp_autodev_run/POS_MVP_P2_CANDIDATE_READER/`.
- Total Field evidence seal is written to `runtime/total_field/evidence/TOTAL_FIELD_SEAL_POS_MVP_P2_CANDIDATE_READER/`.
- Total Field evidence index is `runtime/total_field/evidence/POS_MVP_P2_CANDIDATE_READER_INDEX.jsonl`.
