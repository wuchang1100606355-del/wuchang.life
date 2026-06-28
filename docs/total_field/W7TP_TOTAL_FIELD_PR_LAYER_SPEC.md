# W7TP Total Field PR Layer Spec

LLM is the public-relations layer of Total Field, not the authority of Total Field.
LLM 是總場的公關層，不是總場的權威層。

## Position

The Total Field PR Layer is a candidate-only language polishing layer. It receives verifier-gated packet runtime output and may rewrite the safe answer draft in calmer Traditional Chinese.

It is not Total Field, not the verifier, not an executor, and not an authority source.

## Flow

```text
user text
-> packet inference runtime
-> verifier ALLOW/HOLD/BLOCK
-> semantic_ir / safe answer draft / forbidden actions
-> TOTAL_FIELD_PR_REQUEST_PACKET
-> local PR layer or template fallback
-> TOTAL_FIELD_PR_RESPONSE_PACKET
-> final answer text with verifier decision unchanged
```

## Local Model Lane

The layer may detect an existing localhost Ollama service using `OLLAMA_HOST` or `http://127.0.0.1:11434/api/tags`. It must not download models, install models, call non-local URLs, read credentials, or use the model as authority.

If the local model is unavailable or its output fails safety checks, the layer falls back to template rendering.

## Safety

The safety flags remain:

```text
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
MODEL_DOWNLOAD=FALSE
LLM_AUTHORITY=FALSE
```

The PR request packet contains only hashes, semantic IR, verifier reasons, forbidden actions, safety flags, and public/context-safe drafts. It must not include raw member plaintext, full contact data, identity numbers, secrets, raw DB records, or private profile content.

## Cockpit Integration

The cockpit server runs packet inference first, then passes the verified answer draft to the PR layer. The PR layer can change only wording. It cannot change the verifier decision.

The UI displays:

```text
PR Layer: OFF / LOCAL_MODEL / TEMPLATE_FALLBACK
LLM Authority: FALSE
Verifier Decision Locked: TRUE
Model Output: candidate-only
Scene Context
Final Answer
Raw Verified Draft
PR Layer Refined Answer
Decision Locked
```

## Scene Tone

The PR layer may adjust tone based on `semantic_ir.scene_context`:

```text
STORE_CONTEXT: counter/service tone
PROPERTY_CONTEXT: property/resident service tone
ASSOCIATION_CONTEXT: association/public-interest governance tone
FOUNDER_CONTEXT: Total Field engineering/architecture tone
CLAIMED_FOUNDER_CONTEXT: respectful but not identity-verifying
GENERAL_CHAT_CONTEXT: natural companionship tone
```

This tone routing remains candidate-only and cannot grant scope, verify identity, or change the verifier decision.

If `scene_context.dev_identity_override.enabled=true`, the PR layer may explain that a local development `role_ref` was provided. It must also preserve that the override is local-dev only, does not grant production authority, and does not allow member plaintext, DB writes, payment, or verifier bypass.

## Verification

Use:

```bash
python3 scripts/verify/verify_w7tp_total_field_pr_layer.py
```

The verifier runs without opening any network listener. It checks fallback behavior, identity claims, member context boundaries, payment boundaries, chat tone, and capability explanation.
