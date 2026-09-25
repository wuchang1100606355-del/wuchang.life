# Cafe Revenue to Association Hardware Upgrade Rule

STATE=ASSOCIATION_MACHINE_UPGRADE_REQUIRED_AFTER_REVENUE
BUSINESS_CONTEXT=聊國咖啡館重新總店恢復營運與現金流
LONG_TERM_OWNER=五常社區發展協會

## Principle

Cafe recovery revenue is used first to restore daily operation, POS cash flow, and store continuity. After the association-approved threshold is reached, the cafe supports the association machine upgrade so long-term member governance can move to association-owned hardware.

This is not a transfer of member custody to Odoo, POS, the cafe machine, or the external disk.

## Revenue Rule

| Stage | Condition | Required Action |
|---|---|---|
| Recovery | cafe POS cash flow is being restored | keep Odoo/POS as temporary operation bridge |
| Threshold | revenue reaches association-approved upgrade level | reserve upgrade budget for association machine |
| Upgrade | association confirms hardware plan | purchase or prepare association-owned machine |
| Migration | machine ready and approved | run sealed migration packet |
| Completion | migration verified and sealed | association machine becomes long-term vault host |

## Product Narrative Boundary

For product/homepage wording, describe the cafe role as:

```text
聊國咖啡館重新總店協助協會數位計畫與公益營運，店端系統先支援現場營運與現金流；會員資料與長期治理主權仍屬五常社區發展協會，待營收達標後協助協會升級新機並完成封存遷移。
```

Do not claim:

- the cafe permanently owns member data
- POS stores member plaintext
- Odoo is the association member vault
- external disk is permanent association infrastructure
- public self-signup in POS replaces association registration

## Safety

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
