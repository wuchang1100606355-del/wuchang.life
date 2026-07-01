# XiaoJ 8D Total System Assembly Guide

STATE=P1_8D_TOTAL_SYSTEM_ASSEMBLY_READY_FOR_HUMAN_REVIEW

## Definition

本交付把三個系統收斂成一個 8 維度意圖場封包自然語言控制系統總成：

- 商家管理系統
- 協會會員 8 維度主權會員系統
- 8 維度主權住戶整合式物業管理系統

核心鏈：

```text
natural_language_input
-> total_field_subfield_query
-> 8d_intent_field_packet
-> authority_packet
-> local_reconstruction
-> local_discrete_state_verifier
-> hold_or_human_release_or_dead_letter
-> evidence_seal_and_ui_status
```

## 8D Dimensions

```text
D1_identity
D2_intent
D3_state
D4_topology
D5_resource
D6_governance
D7_verification
D8_envelope
```

Packets carry refs, hashes, state codes, route keys, TTL, nonce, and evidence
seals. They do not carry member plaintext, resident plaintext, token values,
raw audio, raw video, raw API keys, router passwords, or payment data.

## Delivered Interfaces

CLI:

```bash
python3 tools/xiaoj_8d_system_assembly_report.py --pretty
```

Odoo JSON API:

```text
POST /wuchang/xiaoj/api/8d-system-assembly-status
auth=user
```

Service:

```text
wuchang_cafe_ai_gateway.services.eightd_system_assembly.build_eightd_system_assembly_status
```

Contract:

```text
packets/product_av_ordering_ai/xiaoj_8d_total_system_assembly_contract.json
```

## Product Systems

### Merchant Management

Includes:

- POS/table-side ordering candidate gate
- member service candidate gate
- LINE WORKS notification candidate and readiness gate
- LINE Official Account config candidate gate
- formal member/POS/payment release gates

### Association Sovereign Member

Includes:

- 8D member identity/ref packet
- member-owned XiaoJ claim candidate
- no-plaintext member context
- user Gemini key-ref candidate worker
- member sovereignty non-override rule

### Resident Property Management

Includes:

- resident/unit role candidate gate
- facility/repair/parcel/visitor candidate workflow
- association/community context
- resident plaintext redaction boundary
- local role-time-facility-evidence verifier

## P1 Boundary

P1 is ready for human review and candidate governance. It is not production
activation.

Forbidden in P1:

```text
secret_read=false
member_plaintext_read=false
resident_plaintext_read=false
formal_db_write=false
formal_pos_write=false
payment_capture=false
formal_lineworks_send=false
formal_line_message_send=false
deploy=false
service_restart=false
cloud_model_authority=false
llm_direct_execution=false
```

Production requires verified release refs, human owner/admin approval, runtime
activation packets, and local verifier PASS for the target subsystem.
