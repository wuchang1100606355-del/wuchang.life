# XiaoJ Local Voice Order Rehearsal Runbook

STATE=SOURCE_ONLY_REHEARSAL_READY

This runbook is for staff voice POS training before live Odoo/POS release.
It does not create POS orders, capture payments, write Odoo DB, save raw audio,
call external APIs, or claim the menu source is locked.

## Staff Speech Rule

Cashier speech order:

```text
尺寸 → 溫度 → 甜度 → 品項
```

Example:

```text
大冰少糖拿鐵
```

Expected parse:

| Slot | 中文 | English | Vietnamese | Value |
| --- | --- | --- | --- | --- |
| 1 | 尺寸 | Size | Kich co | 大 |
| 2 | 溫度 | Temperature | Nhiet do | 冰 |
| 3 | 甜度 | Sweetness | Do ngot | 少糖 |
| 4 | 品項 | Item | Mon | 拿鐵 |

## Local Rehearsal Command

```bash
python3 tools/xiaoj_p1_local_rehearsal.py --transcript '大冰少糖拿鐵'
```

Reverse or mixed-order confirmation rehearsal:

```bash
python3 tools/xiaoj_p1_local_rehearsal.py --transcript '拿鐵大冰少糖'
```

Expected result:

```text
grammar_valid=false
repeat_confirmation_required=true
canonical_transcript=大冰少糖拿鐵
```

The packet links:

```text
voice parse → menu source resolution → order candidate → payment candidate → receipt candidate
```

## Runtime Gates

The rehearsal stays HOLD for live operation until:

- `HOLD_REAL_MENU_SOURCE_LOCK` is released by a live QuickClick export and human source review.
- `HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED` is released by explicit human approval.
- `HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED` is released by explicit human approval.
- Odoo module upgrade/reload is separately approved if route runtime is needed.

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
