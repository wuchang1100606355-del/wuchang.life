# Temporary Operation Bridge to Association Machine Upgrade

STATE=TEMPORARY_CUSTODY_AND_ASSOCIATION_MACHINE_UPGRADE_RULE_DEFINED
AUTHORITY=五常社區發展協會
SCOPE=聊國咖啡館重新總店營運恢復與 POS 現金流過渡治理

## Rule

目前 Odoo、本機、外接磁碟只作為咖啡館恢復營運的過渡營運橋，不是長期會員資料保管者。

長期會員資料主權、會員治理權、member vault、local vault、governance workloads，仍屬五常社區發展協會。咖啡館端只可保存營運所需的 reference、狀態與時效資訊，不得把 POS 或 Odoo 定義成永久會員資料庫。

## Temporary Bridge Boundary

| Component | Temporary Role | Long-Term Custody |
|---|---|---|
| Odoo | service bridge for POS/account/login state | false |
| POS | sales and cashier workflow | false |
| cafe machine | transition operation node | false |
| external disk | temporary operation vault | false |
| association machine | future long-term governed vault | true |

Allowed temporary references:

- member_ref
- code_ref
- group_code
- permission_ref
- handoff_status
- ttl
- evidence_ref
- migration_ref

Forbidden long-term storage:

- Odoo_member_plaintext
- POS_member_plaintext
- cafe_machine_as_final_member_vault
- external_disk_as_permanent_association_infrastructure

## Authority

The association remains the member governance authority.

Cafe operation may use temporary references only to keep the store running, receive cash, coordinate permissions, and produce evidence for later sealed migration. No temporary operational convenience may override association registration or member governance rules.

## Trigger

When cafe revenue reaches the association-approved hardware upgrade threshold, the next state is:

```text
ASSOCIATION_MACHINE_UPGRADE_AND_SEALED_MIGRATION
```

That future migration must be packetized, evidenced, and sealed before any long-term member vault workload moves.

## Safety

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
PRODUCTION_DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
