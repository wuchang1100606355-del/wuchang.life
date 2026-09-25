# XiaoJ LLM Cost-Saving Model Router Guide

STATE=P1_LLM_COST_SAVING_MODEL_ROUTER_READY

## Purpose

This guide fixes the low-cost model operating method for XiaoJ without changing
runtime model configuration.

The rule is:

```text
cheap model / Gemini / local model -> candidate only
total-field packet -> local reconstruction
local discrete verifier -> EXECUTE / HOLD / QUARANTINE / DEAD_LETTER
```

## Default Model Roles

```text
gpt-5.5
  total-field planning, patent core review, red-team review, final release judgment

gpt-5.4-mini
  Codex implementation, documentation fill, focused verifier repair, Odoo/LINE module modification

gemini-2.5-flash-lite
  merchant runtime candidate generation, customer-service drafts, menu copy, social drafts, natural-language intent candidates

gpt-5.4-nano
  classification, format conversion, field backfill, verifier report summary only
```

`gpt-5.4-nano` is intentionally not used for architecture decisions.

## Price Snapshot

Snapshot date: `2026-07-01`

Sources:

```text
https://platform.openai.com/docs/pricing
https://ai.google.dev/gemini-api/docs/pricing
```

The prices must be rechecked before procurement or production budgeting.

```text
gpt-5.4-mini: input $0.75 / 1M tokens, output $4.50 / 1M tokens
gpt-5.4-nano: input $0.20 / 1M tokens, output $1.25 / 1M tokens
gemini-2.5-flash-lite: input $0.10 / 1M tokens, output $0.40 / 1M tokens
```

## API

```text
POST /wuchang/xiaoj/api/llm-cost-saving-model-router
auth=user
```

Input fields:

```text
task_intent
task_surface
refs
allow_external_candidate
```

Required refs:

```text
local_model_ref
external_candidate_model_ref
gemini_key_ref_vault_binding
member_llm_release_ref
quota_policy_ref
consent_policy_ref
```

The API returns a candidate packet only. It does not write Odoo settings, call a
model, read secrets, or change runtime configuration.

## CLI

```bash
python3 tools/xiaoj_llm_cost_saving_model_router.py \
  --intent "商家客服候選文案" \
  --surface merchant_social_management \
  --pretty
```

With verified refs:

```bash
python3 tools/xiaoj_llm_cost_saving_model_router.py \
  --intent "影音人形服務生候選互動" \
  --surface av_humanoid_service \
  --refs runtime/product_av_ordering_ai/<refs>.json \
  --allow-external-candidate \
  --pretty
```

## Release Sequence

```text
1. complete_llm_cost_saving_model_router_doc_contract_verifier
2. migrate_gemini_raw_key_to_gemini_key_ref_vault_binding
3. add_member_llm_release_gate
4. add_local_personal_data_return_packet
5. add_8d_delegate_rotation_and_revocation
6. add_sovereign_xiaoj_claim_activation
7. only_then_enable_formal_pos_member_payment_release_gates
```

## Forbidden

- raw Google Gemini API key
- raw OpenAI API key
- LINE token
- LINE WORKS token
- Odoo password
- member plaintext
- resident plaintext
- payment card data
- raw audio
- raw video
- cloud model direct execution
- nano model architecture decision

## P1 Boundary

```text
external_api_call=false
model_invocation=false
raw_api_key_read=false
raw_api_key_saved=false
member_plaintext_read=false
resident_plaintext_read=false
formal_db_write=false
runtime_model_changed=false
llm_execution_authority=false
deploy=false
service_restart=false
```
