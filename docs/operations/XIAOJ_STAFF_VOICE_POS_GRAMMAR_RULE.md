# XiaoJ Staff Voice POS Grammar Rule

RUN_ID=D8_MANDATORY_TASK_20260624_090117_XIAOJ_P1_STAFF_VOICE_POS_GRAMMAR_RULE
STATE=VOICE_POS_GRAMMAR_RULE_READY

## Rule

店員語音 POS 必須照以下順序念：

```text
尺寸 → 溫度 → 甜度 → 品項
```

Example:

```text
大冰少糖拿鐵
```

Parsed as:

| Slot | Value |
| --- | --- |
| 尺寸 | 大 |
| 溫度 | 冰 |
| 甜度 | 少糖 |
| 品項 | 拿鐵 |

## Product Reason

This grammar reduces ambiguity during rush-hour cashier work and keeps XiaoJ from guessing item/options out of order.

## Reverse Or Out-Of-Order Speech

If a cashier says the same parts in reverse or mixed order, XiaoJ must not
create a live POS action. XiaoJ may infer the likely candidate and repeat it
back for confirmation.

Example:

```text
拿鐵大冰少糖
```

XiaoJ repeat-confirmation:

```text
我聽到像是「大冰少糖拿鐵」，請店員或店長確認。
```

State:

```text
repeat_confirmation_required=true
grammar_valid=false
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
ODOO_DB_WRITE=FALSE
```

## Safety

The parser uses transcript text only. It does not save raw audio, create POS orders, capture payments, write Odoo DB, or read member plaintext.

## Runtime Hold

The grammar is source-ready. Runtime route activation still requires Odoo module upgrade/reload approval.
