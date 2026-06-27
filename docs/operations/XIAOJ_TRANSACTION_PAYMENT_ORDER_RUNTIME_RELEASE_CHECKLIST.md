# XiaoJ Transaction Payment Order Runtime Release Checklist

RUN_ID=D8_MANDATORY_TASK_20260624_084513_XIAOJ_P1_TRANSACTION_PAYMENT_ORDER_CAPABILITY_SPEC
STATE=RUNTIME_RELEASE_CHECKLIST_READY
ROOT=/home/taiji_admin/Taiji_Hub

## Product Requirement

XiaoJ must be able to trade, take orders, and support payment.

This requirement is accepted as a product target. It does not by itself authorize a live POS order or live payment capture.

## What Must Be Built

| Capability | Required behavior | Verification |
| --- | --- | --- |
| Tradeable order flow | User can select real menu items and form an order | Cart/order payload exists |
| POS order creation | Confirmed order can be sent to Odoo POS after release | Odoo test order verifier |
| Cash payment | Cashier can confirm cash received at counter | Cash payment method verifier |
| External payment | Approved payment provider can be referenced | Provider/token gate; no secret printed |
| Receipt | Receipt/hand-off state waits for Odoo POS order id | Receipt verifier |
| Manager override | Price change/return requires manager approval | Role verifier |
| Safety | No hidden order/payment from AI suggestion | Candidate-action verifier |

## Runtime Release Required Before Real Transaction

Before Codex may create a real POS order or capture/confirm real payment, the human release must include:

```text
允許本輪建立測試/正式 POS 訂單。
DB=wuchang_odoo
POS_CONFIG_ID=<id>
POS_SESSION_ID=<id>
PRODUCTS=<approved product refs and quantities>
PAYMENT_METHOD=<cash or approved provider>
AMOUNT=<exact amount>
MODE=<test or live>
ALLOW_ODOO_DB_WRITE=TRUE
ALLOW_POS_ORDER_CREATED=TRUE
ALLOW_PAYMENT_CAPTURE=<TRUE only if real capture is intended>
ALLOW_SERVICE_RESTART=FALSE unless explicitly stated
```

If any value is missing, the state remains:

```text
HOLD_TRANSACTION_RELEASE_REQUIRED
```

## Current Non-Runtime Prototype

The static P1 console now includes:

- transaction order panel
- payment panel
- receipt panel
- cart/order payload
- cash/external payment mode selector
- runtime release warning

The prototype still performs no real transaction.

## Safety Flags For This Run

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
D8_LOCAL_DB_WRITE=TRUE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
ODOO_FILES_TOUCHED=FALSE
LINE_LOGIN_FILES_TOUCHED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
