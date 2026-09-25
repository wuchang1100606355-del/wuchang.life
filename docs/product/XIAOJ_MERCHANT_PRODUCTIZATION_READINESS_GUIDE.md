# XiaoJ Merchant Productization Readiness Guide

STATE=MERCHANT_PRODUCTIZATION_READINESS_GATE_READY

## Purpose

This guide gives the operator one command to check whether XiaoJ is ready for
merchant activation across:

- LINE WORKS notification send
- LINE Official Account configuration
- formal member registration
- formal POS order creation
- formal payment

The readiness command is a local verifier. It does not send LINE or LINE WORKS
messages, create Odoo records, write POS orders, capture payments, read
secrets, deploy, or restart services.

## Readiness Command

```bash
python3 tools/xiaoj_merchant_productization_readiness.py \
  --config packets/product_av_ordering_ai/xiaoj_merchant_productization_readiness_template.json \
  --pretty
```

Odoo JSON API:

```text
POST /wuchang/xiaoj/api/merchant-productization-readiness
auth=user
```

API payload refs are in-memory refs only:

```json
{
  "formal_release_refs": {},
  "lineworks_refs": {},
  "line_official_account_refs": {},
  "line_official_account_intent": "candidate intent only",
  "lineworks_probe": {}
}
```

The API uses the same service as the CLI:

```text
wuchang_cafe_ai_gateway.services.merchant_productization_readiness.build_merchant_productization_readiness
```

The untouched template must return:

```text
STATE=HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS
```

This is correct. It means the system has a productization gate, but human-filled
verified refs are still missing.

## Required Human Inputs

Fill refs only. Do not paste token values, channel secrets, LINE passwords,
LINE WORKS user IDs, Google API keys, Odoo passwords, payment data, member
plaintext, router passwords, raw audio, or raw video.

The operator must provide:

- `packets/product_av_ordering_ai/lineworks_release_refs_template.json`
- `packets/product_av_ordering_ai/line_official_account_refs_template.json`
- formal member registration release refs
- formal POS order release refs
- formal payment release refs

Each formal release ref must include:

```json
{
  "ref": "OPAQUE_READY_REF",
  "packet_hash": "64hex",
  "verifier": "total_field_release_registry",
  "verified": true
}
```

## PASS Meaning

`PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS` means:

- LINE WORKS preflight is ready for human activation.
- LINE Official Account config candidate is ready for human approval.
- formal member registration gate has verified refs.
- formal POS order gate has verified refs.
- formal payment gate has verified refs.
- the total field subfield query is available and safe.

PASS still does not execute production actions. It means the human owner/admin
may review the report and then create a separate runtime activation packet.

## HOLD Meaning

`HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS` means at least one gate is not
ready. The report includes `operator_next_actions`, such as:

```text
fill_line_official_account_safe_refs_and_rerun_config_candidate
fill_verified_lineworks_release_refs_and_runtime_connector_refs
fill_verified_member_registration_release_refs
fill_verified_pos_order_release_refs
fill_verified_payment_release_refs
```

## Boundary

```text
total field may prepare candidates
human owner/admin remains root of trust
LLM direct execution=false
cloud model authority=false
runtime activation required=true
```

P1 side effects remain false:

```text
external_api_call=false
formal_lineworks_send=false
formal_line_message_send=false
official_account_setting_changed=false
formal_member_registration=false
formal_db_write=false
formal_pos_write=false
payment_capture=false
secret_read=false
member_plaintext_read=false
deploy=false
service_restart=false
```
