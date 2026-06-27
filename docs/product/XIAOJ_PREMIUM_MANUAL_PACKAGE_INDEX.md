# XiaoJ Premium Manual Package Index

STATE=PREMIUM_MANUAL_PACKAGE_READY_RUNTIME_HOLD

This index binds the polished operator manual and developer guide.

| Document | Audience | Path |
| --- | --- | --- |
| 小J影音點餐雙軌實習精裝使用說明書 | 店長、店員、總場營運 | `docs/operations/XIAOJ_PREMIUM_USER_MANUAL.md` |
| XiaoJ AV Ordering Developer Guide | 開發者、總場工程、Codex agents | `docs/total_field/XIAOJ_DEVELOPER_GUIDE.md` |

Current usable scope:

- Field practicum.
- Dual-track operation.
- Local voice rehearsal.
- Candidate order/payment/receipt packets.
- Training and comparison against human POS action.

Current runtime hold:

- `HOLD_AUTH_ROUTE_GATE`
- `HOLD_REAL_MENU_SOURCE_LOCK`
- `HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED`
- `HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED`

Safety:

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
