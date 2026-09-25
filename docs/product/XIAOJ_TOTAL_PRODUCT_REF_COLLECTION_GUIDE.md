# XiaoJ Total Product Ref Collection Guide

STATE=P1_TOTAL_PRODUCT_REF_COLLECTION_READY_FOR_HUMAN_FILL

## Purpose

This is the single ref collection flow for the XiaoJ total product handoff:

- LINE WORKS
- LINE Official Account
- merchant formal member/POS/payment release
- association sovereign member
- resident property management

It accepts refs only. Do not paste passwords, token values, API keys, member
plaintext, resident plaintext, payment card data, raw audio, or raw video.

## Template

```text
packets/product_av_ordering_ai/xiaoj_total_product_ref_collection_template.json
```

Generate the same refs-only template from the shared service:

```bash
python3 tools/xiaoj_total_product_ref_collection_builder.py \
  --emit-template \
  --out runtime/product_av_ordering_ai/total_product_ref_collection/xiaoj_total_product_ref_template.json \
  --pretty
```

Odoo JSON API:

```text
POST /wuchang/xiaoj/api/total-product-ref-template
auth=user
```

The untouched template must stay:

```text
HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT
```

## Validate Draft

```bash
python3 tools/xiaoj_total_product_ref_collection_builder.py \
  --input packets/product_av_ordering_ai/xiaoj_total_product_ref_collection_template.json \
  --worksheet-out runtime/product_av_ordering_ai/total_product_ref_collection/xiaoj_total_product_ref_worksheet.md \
  --pretty
```

After you fill safe refs and verified packet hashes:

```bash
python3 tools/xiaoj_total_product_ref_collection_builder.py \
  --input runtime/product_av_ordering_ai/your_filled_refs.json \
  --worksheet-out runtime/product_av_ordering_ai/total_product_ref_collection/xiaoj_total_product_ref_worksheet.md \
  --allow-verified \
  --pretty
```

Odoo JSON API:

```text
POST /wuchang/xiaoj/api/total-product-ref-collection
auth=user
```

The draft output contains:

```text
handoff_inputs
human_fill_checklist
operator_fill_summary
operator_fill_worksheet_md
```

`human_fill_checklist` lists each required ref, packet hash, verifier, and
human-reviewed verified flag by group. Use it as the operator checklist before
building the handoff pack.

`operator_fill_worksheet_md` is a human-readable markdown worksheet grouped by
LINE WORKS, LINE Official Account, member registration, POS, payment,
association sovereign member, and resident property management refs.

Use `--worksheet-out <path>.md` to write that worksheet as a standalone markdown
file for operator review.

Use that draft directly with:

```bash
python3 tools/xiaoj_total_product_handoff_pack.py \
  --ref-collection runtime/product_av_ordering_ai/total_product_ref_collection/<draft>.json \
  --pretty
```

## Required Groups

```text
lineworks
line_official_account
merchant_formal_release
association_sovereign_member
resident_property_management
```

Each verified release ref should have:

```json
{
  "ref": "OPAQUE_READY_REF",
  "packet_hash": "64hex",
  "verifier": "total_field_release_registry",
  "verified": true
}
```

## Forbidden Inputs

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
