# XiaoJ Total Product Operator Bundle Guide

STATE=P1_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY

## Purpose

This command builds one local operator bundle for the XiaoJ total product:

- total product refs template
- ref collection draft
- standalone ref worksheet
- total product handoff pack
- manifest with file hashes
- operator README

It is safe for P1 handoff. It does not send LINE or LINE WORKS messages, write
Odoo/POS, capture payment, read secrets, read member/resident plaintext, deploy,
or restart services.

## Command

```bash
python3 tools/xiaoj_total_product_operator_bundle.py --pretty
```

After filling refs and after human owner/admin review:

```bash
python3 tools/xiaoj_total_product_operator_bundle.py \
  --input-refs runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle>/ref_template.json \
  --allow-verified \
  --out-dir runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle> \
  --pretty
```

Output root:

```text
runtime/product_av_ordering_ai/total_product_operator_bundle/
```

## Odoo API

```text
POST /wuchang/xiaoj/api/total-product-operator-bundle
auth=user
```

The API returns an in-memory `W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_PAYLOAD_V1`
payload with:

```text
README.md
ref_template.json
ref_collection.json
ref_worksheet.md
handoff.json
```

The API does not accept server file paths and does not write bundle files. Use
the CLI when a local filesystem bundle is needed.

## Bundle Files

```text
README.md
MANIFEST.json
ref_template.json
ref_collection.json
ref_worksheet.md
handoff.json
```

## Operator Flow

```text
open README.md
open ref_worksheet.md
fill refs only
rerun bundle with --input-refs and --allow-verified only after human owner/admin review
review refreshed ref_collection, worksheet, handoff, and manifest
```

Odoo/API operator flow:

```text
call /wuchang/xiaoj/api/total-product-operator-bundle
review bundle_files.ref_worksheet.md
fill refs only
call the same API with refs and allow_verified only after human owner/admin review
review refreshed ref_collection and handoff payload
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
