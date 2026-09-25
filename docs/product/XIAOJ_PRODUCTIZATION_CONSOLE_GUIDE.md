# XiaoJ Productization Console Guide

STATE=P1_TOTAL_PRODUCT_CONSOLE_DRAFT_READY_P2_GATES_HOLD

## Purpose

This guide defines the Odoo-accessible XiaoJ total productization console:

- merchant branch XiaoJ
- association total-field member service XiaoJ
- 8D sovereign member system
- 8D sovereign resident property management system
- LINE WORKS notification handoff

The console is a candidate / dry-run / preflight surface only. It does not send
LINE WORKS messages, write Odoo/POS records, capture payment, read secrets, or
move member/resident plaintext into prompts.

## APIs

```text
POST /wuchang/xiaoj/api/total-product-console-status
POST /wuchang/xiaoj/api/member-llm-release-gate
POST /wuchang/xiaoj/api/local-personal-data-return-packet
POST /wuchang/xiaoj/api/8d-delegate-rotation-draft
POST /wuchang/xiaoj/api/sovereign-xiaoj-claim-draft
auth=user
```

## Product Lines

```text
merchant_branch_xiaoj
association_total_field_member_service_xiaoj
eightd_sovereign_member_system
eightd_sovereign_resident_property_management
```

Human-world identities must be supplied as refs:

```text
owner_admin_ref
merchant_manager_ref
association_ref
sponsor_org_ref
```

Do not put plaintext email, password, token, raw API key, member plaintext,
resident plaintext, payment data, raw audio, or raw video into refs, contracts,
prompts, or public docs.

## Low-Cost Model Boundary

```text
gpt-5.4-mini: implementation, docs, verifier repair
gemini-2.5-flash-lite: runtime candidate generation
gpt-5.4-nano: classification / formatting / field backfill / summary only
gpt-5.5 or human owner/admin: final release, red-team judgment, patent core
```

Cloud model output remains candidate-only. The local discrete verifier remains
the authority for execution.

## P2 Gates

```text
member_llm_release_gate
local_personal_data_return_packet
8d_delegate_rotation_draft
sovereign_xiaoj_claim_draft
formal POS/member/payment release
```

All P2 gates return HOLD until verified refs are supplied and reviewed by the
human owner/admin.

## P1 Boundary

```text
external_api_call=false
model_invocation=false
formal_lineworks_send=false
formal_line_message_send=false
formal_member_registration=false
formal_db_write=false
formal_pos_write=false
payment_capture=false
secret_read=false
raw_api_key_read=false
raw_api_key_saved=false
member_plaintext_read=false
resident_plaintext_read=false
runtime_model_changed=false
deploy=false
service_restart=false
```
