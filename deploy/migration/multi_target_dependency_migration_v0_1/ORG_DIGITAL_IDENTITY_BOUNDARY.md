# Organization Digital Identity Boundary

版本：2026-05-11

## Digital Identity

| 欄位 | 內容 |
|---|---|
| Organization | 新北市三重區五常社區發展協會 |
| Domain | wuchang.life |
| Digital representative account | admin@wuchang.life |
| Information officer | 江政隆，本會授權之總幹事 |

## Boundary

`admin@wuchang.life` is an organization representative account, not a personal unrestricted bypass.

Allowed:

- organization shared cloud administration
- readonly non-sensitive cloud staging review
- Taiji Hub governance administration
- audit and document archive coordination
- Odoo / POS governance configuration after policy review

Blocked:

- secret exposure
- personal-data plaintext cloud upload
- business secret cloud upload
- production mutation without Gateway / Five Metric / Audit / Rollback
- deleting audit history
- using admin authority to override public-interest metric

