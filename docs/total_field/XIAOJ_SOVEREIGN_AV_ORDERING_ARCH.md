# XiaoJ Sovereign AV Ordering Architecture

STATE=XIAOJ_SOVEREIGN_AV_ORDERING_ARCH_READY
RUN_ID=D8_MANDATORY_TASK_20260624_133320_XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_TO_ARCH_PACKET

## Purpose

This document turns the attached research report into a local, docs-only architecture packet for 聊國咖啡館主權式影音點餐小J.

This packet does not deploy services, create orders, capture payments, write Odoo DB, call Google APIs, read secrets, or read member plaintext.

## Core Architecture

The project should use a two-layer sovereignty architecture:

| Layer | Scope | Data Rule |
| --- | --- | --- |
| Association sovereignty layer | member governance, registration, review, code issuance, permission routing, sensitive data authority | May hold governed member data only inside association-controlled vaults and formal governance boundaries |
| Cafe operation layer | kiosk, voice guide, AV ordering, POS transaction flow, staff operation, customer display | Ref-only: `member_ref`, `code_ref`, `group_code`, `permission_ref`, `evidence_ref`, TTL, route refs |

The cafe layer must not become the long-term member plaintext custodian.

## Domain Split

| Domain | Role |
| --- | --- |
| `assoc.wuchang.life` | association registration, member review, 8D code issuance, governance portal |
| `auth.wuchang.life` | login, short-lived token, device authorization, route policy |
| `pos.wuchang.life` | Odoo POS, kiosk, staff operator, self-order route |
| `ai.wuchang.life` | XiaoJ interaction, broadcast, customer-facing AI surface |
| `vault.local` | temporary sealed vault, member map, evidence bundles, migration package |
| `edge-broker.local` | STT/TTS broker, AV packet broker, TTL cache, evidence writer |

## Lane Design

| Lane | First Release Rule | Reason |
| --- | --- | --- |
| Transaction voice | local-first VAD / wakeword / menu-slot grammar; cloud only through broker if approved | Transaction truth must not depend on raw cloud output |
| Broadcast / show voice | authorized broker may call commercial TTS after text is controlled | High-quality speech can be impressive without touching POS truth |
| Video / image understanding | W7TP packetization; no raw video persistence | Preserve no-raw-data boundary |
| POS order | candidate only until human release | Existing D8 gates still hold |
| Payment | human-only until release | No unauthorized capture |

## Main Transaction Chain

```text
voice / touch / visual cue
→ local broker
→ policy gate
→ menu source lock
→ candidate order
→ staff/customer confirmation
→ human-confirmed action
→ sealed committed action
```

Until release, XiaoJ may produce only `candidate_action`.

## Odoo Role

Odoo is the operation backbone for:

- POS products and categories.
- self-order / kiosk / QR menu if enabled.
- preparation display and staff operation.
- order records after human-confirmed release.

Odoo is not the association member plaintext vault.

## Runtime Gates Still Required

- `HOLD_AUTH_ROUTE_GATE`
- `HOLD_REAL_MENU_SOURCE_LOCK`
- `HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED`
- `HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED`

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
