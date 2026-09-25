# XiaoJ AV Ordering MVP Roadmap

STATE=XIAOJ_AV_ORDERING_MVP_ROADMAP_READY
RUN_ID=D8_MANDATORY_TASK_20260624_133320_XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_TO_ARCH_PACKET

## Product Direction

Build the fastest useful XiaoJ product without violating Total Field sovereignty:

```text
local broker
→ real menu source
→ candidate order
→ human confirmation
→ Odoo/POS only after release
```

## MVP Priorities

| Priority | Item | Release Boundary |
| --- | --- | --- |
| P0 | real menu source lock | no invented menu |
| P0 | ref-only member / permission route | no member plaintext in POS |
| P0 | local broker spec | docs first, no credentials |
| P0 | candidate order grammar | no live order |
| P1 | Gemini-style TTS broadcast lane | no external API this run |
| P1 | kiosk / QR self-order shell | no deploy this run |
| P1 | local vault / migration manifest | no secret material in docs |
| P2 | menu phrase adaptation plan | real menu only |
| P2 | video packet lane | no raw video persistence |

## Suggested First Demonstrable Experience

1. Staff says a controlled phrase such as `大冰少糖拿鐵`.
2. XiaoJ parses size, temperature, sweetness, and item.
3. XiaoJ repeats the normalized order.
4. XiaoJ shows candidate order only.
5. Staff confirms manually in Track A POS.
6. XiaoJ records evidence refs only.

## Product Feeling Without Risk

The impressive first surface should be:

- multilingual menu storytelling.
- store broadcast.
- guided ordering rehearsal.
- staff Vietnamese-friendly confirmation.
- customer display with image-and-table support.

These create product value before true POS/payment authority is released.

## Not Yet Allowed

- live POS order creation.
- payment capture.
- Google credential setup.
- runtime deploy.
- direct Google API calls.
- member plaintext use.
- raw audio/video retention.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
