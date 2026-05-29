# Odoo 帳號角色映射

版本：2026-05-12

## 狀態

```text
ACTIVE_GOVERNANCE_MAPPING_ONLY
```

此文件只建立 Odoo 帳號角色治理資訊，尚未直接修改 Odoo production 資料庫、使用者、權限或公司資料。

## 帳號映射

| Account | Role | Window | Notes |
|---|---|---|---|
| `o970106@gmail.com` | 團體會員帳號、開發商帳號 | group_member / developer_vendor | 已由使用者確認修正；正式建立仍需 Odoo 治理寫入窗 |
| `admin@wuchang.life` | 超級管理員帳號、主公司負責人帳號 | main_company_super_admin / accountable_company_owner | 本會數位代表號；不得繞過度規、Gateway、audit、人類決策 |

## 五維碼

```yaml
intent: odoo_account_role_mapping
resource: account_role_metadata
time: development_pre_live_odoo_mutation
authority: human_confirmed_odoo_governance_window
topology: odoo_main_company_group_member_developer_admin
```

## Live Apply Boundary

任何正式 Odoo 寫入前必須具備：

- account identifier human confirmation
- Odoo user/company/role manifest
- Five Metric Gate decision
- audit record
- rollback plan
- no secret output
- no member plaintext export

## Risk

| Case | Risk | Action |
|---|---|---|
| governance mapping only | L1_near | allow_with_audit |
| confirmed account mapping before live creation | L1_near | allow_with_audit |
| direct Odoo permission mutation without manifest | L3_metric_hazard | block |
| AI using admin account to bypass Gate | L3_metric_hazard | block / deadbox |
