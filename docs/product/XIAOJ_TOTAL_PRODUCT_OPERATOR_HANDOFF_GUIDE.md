# XiaoJ Total Product Operator Handoff Guide

STATE=P1_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY

## Purpose

This is the operator handoff for the current XiaoJ productization package:

- 8D intent-field packet natural-language control system assembly
- merchant management system
- association sovereign member system
- resident/property management system
- LINE WORKS and LINE Official Account integration gates

The handoff pack is safe to run locally. It does not send messages, write Odoo,
write POS, capture payment, read secrets, read member plaintext, read resident
plaintext, deploy, or restart services.

## Command

```bash
python3 tools/xiaoj_total_product_operator_bundle.py --pretty

python3 tools/xiaoj_total_product_handoff_pack.py --pretty
```

The bundle command creates `README.md`, `MANIFEST.json`, `ref_template.json`,
`ref_collection.json`, `ref_worksheet.md`, and `handoff.json` under:

```text
runtime/product_av_ordering_ai/total_product_operator_bundle/
```

After filling refs and after human owner/admin review:

```bash
python3 tools/xiaoj_total_product_operator_bundle.py \
  --input-refs runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle>/ref_template.json \
  --allow-verified \
  --out-dir runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle> \
  --pretty
```

Recommended ref collection command before handoff:

```bash
python3 tools/xiaoj_total_product_ref_collection_builder.py \
  --emit-template \
  --out runtime/product_av_ordering_ai/total_product_ref_collection/xiaoj_total_product_ref_template.json \
  --pretty

python3 tools/xiaoj_total_product_ref_collection_builder.py \
  --input packets/product_av_ordering_ai/xiaoj_total_product_ref_collection_template.json \
  --worksheet-out runtime/product_av_ordering_ai/total_product_ref_collection/xiaoj_total_product_ref_worksheet.md \
  --pretty
```

Recommended ref collection API before handoff:

```text
POST /wuchang/xiaoj/api/total-product-ref-template
auth=user

POST /wuchang/xiaoj/api/total-product-ref-collection
auth=user
```

Odoo operator page:

```text
WuChang Cafe / Total Product Handoff
Click Load Ref Template
Fill refs only
Click Build Ref Collection
Review Human Fill Checklist
Review Operator Worksheet
Click Build Handoff Pack
```

After filling refs:

```bash
python3 tools/xiaoj_total_product_handoff_pack.py \
  --ref-collection runtime/product_av_ordering_ai/total_product_ref_collection/<draft>.json \
  --pretty
```

Odoo JSON API:

```text
POST /wuchang/xiaoj/api/total-product-operator-handoff
auth=user
```

Service:

```text
wuchang_cafe_ai_gateway.services.total_product_handoff.build_total_product_operator_handoff
```

## What The Pack Aggregates

- 8D system assembly status
- merchant productization readiness
- LINE WORKS operator inputs
- LINE Official Account operator inputs
- association sovereign member operator inputs
- resident property management operator inputs
- forbidden operator inputs
- operator checklist

## What You Should Prepare

Prepare refs only:

- LINE WORKS verified refs and runtime token provider ref
- LINE Official Account refs and vault/runtime refs
- formal member registration release refs
- formal POS order release refs
- formal payment release refs
- sovereign XiaoJ claim / consent / Gemini key refs
- resident / unit / role / facility / property action refs

Each verified release ref should have:

```json
{
  "ref": "OPAQUE_READY_REF",
  "packet_hash": "64hex",
  "verifier": "total_field_release_registry",
  "verified": true
}
```

## What You Should Not Give

- LINE password
- LINE WORKS password
- channel access token value
- channel secret value
- Google Gemini raw API key
- Odoo password
- router password
- member plaintext
- resident plaintext
- payment card data
- raw audio
- raw video

## Meaning Of PASS

`PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY` means the handoff pack itself
is ready for operator review and next-step execution planning.

It does not mean production activation is ready. Production activation remains
blocked until verified refs and runtime activation packets are provided.

In short: production activation remains blocked by design until the human
owner/admin provides verified refs and separate runtime activation packets.

## P1 Boundary

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
resident_plaintext_read=false
raw_audio_saved=false
raw_video_saved=false
deploy=false
service_restart=false
```
