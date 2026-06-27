# XiaoJ Avatar Broadcast and Order Rehearsal Runbook

## Purpose

Use the XiaoJ VRM avatar as a visual host for P0 onsite shadow rehearsal. The avatar helps staff rehearse menu introduction and candidate order confirmation, while all operational authority remains with the human store team and Total Field verifier.

## Safety Boundary

```text
AVATAR_ROLE=VISUAL_CARRIER_ONLY
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
ODOO_DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
COMMERCIAL_RELEASE=FALSE
LICENSE_REVIEW_REQUIRED=TRUE
```

## Rehearsal Flow

1. Staff speaks the product in the store-defined order.
2. XiaoJ converts the utterance into a candidate order phrase.
3. Avatar repeats the candidate phrase visually and verbally.
4. Staff confirms, corrects, or cancels.
5. P0 stops at rehearsal evidence. It does not write POS or capture payment.

Recommended order phrase:

```text
size -> temperature -> sweetness -> item
```

Example:

```text
large iced low sugar latte
```

If staff speaks in another order, XiaoJ may repeat the normalized candidate and ask for confirmation:

```text
Confirm: large, iced, low sugar, latte?
```

## Broadcast Rehearsal

Allowed:

- Menu introduction using real cafe menu source.
- Candidate order confirmation.
- Staff training rehearsal.
- Vietnamese manager-friendly visual prompts.

Not allowed:

- Inventing menu items.
- Formal commercial use of the avatar before license review.
- Treating the avatar as member identity.
- Creating POS orders.
- Capturing payments.

## Hold Conditions

Stop the avatar rehearsal and use HOLD if any condition occurs:

| Condition | State |
| --- | --- |
| `assets/xiaoj/avatar/J.vrm` missing | `HOLD_XIAOJ_VRM_AVATAR_NOT_READY` |
| License review requested for commercial release | `HOLD_LICENSE_REVIEW_REQUIRED` |
| POS write requested | `HOLD_POS_WRITE_NOT_ALLOWED_IN_P0` |
| Payment requested | `HOLD_PAYMENT_NOT_ALLOWED_IN_P0` |
| Identity authority requested | `HOLD_AVATAR_IDENTITY_AUTHORITY_FORBIDDEN` |

## Evidence Checklist

- Avatar file exists at the registered path.
- Viewer plan references local VRM only.
- Avatar state packet is non-executable.
- License boundary document exists.
- Report and seal are created.
