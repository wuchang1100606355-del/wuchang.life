# XiaoJ Google Speech Broker Spec

STATE=XIAOJ_GOOGLE_SPEECH_BROKER_SPEC_READY
RUN_ID=D8_MANDATORY_TASK_20260624_133320_XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_TO_ARCH_PACKET

## Boundary

This is a docs-only broker specification derived from the attached research report. It does not call Google APIs, create credentials, read `.env`, inspect secrets, or deploy containers.

## Broker Principle

Google commercial speech capability, if used, should be placed behind an association-authorized local broker. POS clients, kiosk tablets, and staff devices must not directly hold primary cloud credentials.

```text
POS / kiosk / XiaoJ UI
→ local edge broker
→ policy gate
→ minimal payload
→ Google speech service if authorized
→ transcript/audio result
→ local validation / evidence
```

## Credential Rule

- Credentials belong to an association-controlled project or equivalent approved authority.
- Service account material must never be copied into POS clients.
- Broker receives only minimum necessary credential access.
- Any future key material must use key refs / vault refs, not plaintext in docs or chat.

## STT Lane

Allowed design:

- local VAD / wakeword first.
- menu grammar and slot parser first.
- optional commercial STT only through broker.
- phrase hints / custom classes may be prepared from real menu source only.
- transcript is never transaction truth by itself.

Disallowed before release:

- raw continuous recording storage.
- sending member plaintext.
- accepting cloud transcript as final POS order.
- direct POS order creation.

## TTS Lane

Allowed design:

- controlled text for greeting, menu storytelling, broadcast, role scripts.
- no member plaintext.
- no payment instruction generation.
- no legal/accounting/patent claim without human review.

TTS is suitable for customer experience before POS automation because it can produce product feeling without taking transaction authority.

## Audit Fields

Future broker records should use:

| Field | Meaning |
| --- | --- |
| `session_ref` | short-lived interaction ref |
| `member_ref` | optional pseudonymous member ref |
| `menu_version_ref` | real menu source version |
| `transcript_ref` | bounded transcript evidence ref |
| `tts_script_ref` | controlled script evidence ref |
| `policy_decision` | PASS / WARN / HOLD / BLOCK |
| `ttl_expires_at` | expiry for temporary refs |

## No-Raw-Data Rule

Audio and image handling must preserve:

- no raw customer video persistence.
- no long-lived raw audio unless explicit future release and signage exist.
- state packet / hash / evidence refs instead of raw customer material.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
