# XiaoJ Field Practicum Dual-Track Rule

STATE=FIELD_PRACTICUM_DUAL_TRACK_DEFINED

This rule lets XiaoJ go into the cafe field as an intern without taking over
live cashier authority.

## Core Rule

The cafe runs two tracks at the same time:

| Track | Name | Purpose | Authority |
| --- | --- | --- | --- |
| A | Live Operation Track | Real customer service, real POS, real cash, real receipts | Human cashier / manager |
| B | XiaoJ Shadow Track | Listen, parse, translate, suggest, rehearse, and produce candidate packets | XiaoJ candidate-only |

XiaoJ may help the field, but Track B never becomes Track A automatically.

## Track A: Live Operation

Track A is the only path for real business today.

- Staff uses the approved existing POS / cashier process.
- Cash is handled by the counter and manager.
- Price changes, refunds, voids, and cash advances require manager confirmation.
- Receipts and closing cash remain human-accounted until a runtime release is approved.

Track A can use XiaoJ output only as reference. The human operator must still
confirm every real POS action.

## Track B: XiaoJ Shadow Practicum

Track B is where XiaoJ learns in the field.

Allowed:

- Staff voice POS rehearsal.
- Speech-to-text text input only; raw audio is not saved.
- Parse `尺寸 → 溫度 → 甜度 → 品項`.
- Example: `大冰少糖拿鐵`.
- Translate helper text for Chinese, Vietnamese, and English.
- Produce order, payment, and receipt candidates.
- Produce manager review notes and evidence refs.
- Compare candidate output with what the cashier really did.
- Record gaps as future requirements or redteam candidates.

Forbidden:

- Create a real POS order.
- Capture payment.
- Write Odoo DB.
- Modify price in production.
- Read member plaintext.
- Save raw audio.
- Call external APIs.
- Restart services.
- Deploy.

## Staff Voice Practicum

Cashier speech order:

```text
尺寸 → 溫度 → 甜度 → 品項
```

Example:

```text
大冰少糖拿鐵
```

Parse:

| Slot | 中文 | English | Vietnamese | Value |
| --- | --- | --- | --- | --- |
| 1 | 尺寸 | Size | Kich co | 大 |
| 2 | 溫度 | Temperature | Nhiet do | 冰 |
| 3 | 甜度 | Sweetness | Do ngot | 少糖 |
| 4 | 品項 | Item | Mon | 拿鐵 |

If the item or price is not locked by real menu source, XiaoJ must say:

```text
HOLD_REAL_MENU_SOURCE_LOCK
```

and stay in rehearsal mode.

## Vietnamese Manager Rule

The manager can operate directly with short bilingual confirmations:

| Chinese | Vietnamese | Meaning |
| --- | --- | --- |
| 確認候選 | Xac nhan ban nhap | Confirm candidate |
| 只做演練 | Chi dien tap | Rehearsal only |
| 不寫 POS | Khong ghi POS | Do not write POS |
| 等店長確認 | Doi quan ly xac nhan | Wait for manager |
| 現金櫃台確認 | Quay xac nhan tien mat | Counter confirms cash |

## Daily Field Practicum Loop

1. Staff serves the customer on Track A.
2. XiaoJ listens through text/STT transcript on Track B.
3. XiaoJ parses the candidate.
4. Human compares XiaoJ candidate with the real cashier action.
5. If correct, mark as training success.
6. If wrong, record the mismatch.
7. No real POS write occurs from Track B.

## Promotion Gate

XiaoJ may move from shadow to assisted live operation only when all are true:

- Real menu source is locked.
- LINE / Google member routes are runtime verified.
- Odoo module release is human-approved.
- POS order create is human-approved.
- Payment capture is human-approved.
- Rollback plan exists.
- Store manager signs the release.

Until then:

```text
TRACK_A_LIVE_OPERATION=HUMAN_ONLY
TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY
```

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
