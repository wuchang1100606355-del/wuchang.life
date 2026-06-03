# Odoo Identity Model

## Representation

| Entity | Recommended Odoo representation | Boundary |
| --- | --- | --- |
| 新北市三重區五常社區發展協會 | Odoo 主公司 / main company | public-interest controller and main accountable Odoo company |
| 聊國咖啡館重新店 / 上品食品行 | 開發商協力廠商 / 技術轉移者 / vendor partner | not Odoo main company; separate vendor/technology-transfer window |
| Cooperative POS customers | customer / tenant / branch customer | service agreement required |
| Wuchang Sovereign Property AI service | branch customer / service tenant / governed AI service node | separate from cafe operation |
| Private Liaoguo Coffee Chongxin main store | technology sponsor / technical transfer / hardware lending provider | not public-interest asset controller |

## Rules

- Odoo must preserve company/branch/customer separation.
- Private store authority must not control association assets.
- Community fund-pool records must not be mixed with private commercial income.
- POS service tenants do not receive governance authority.
- Brand name, legal business entity, association entity, and Odoo company/branch records must be separated.
- The association is the Odoo main company.
- Liaoguo Coffee Reopen Store / 上品食品行 is represented as developer vendor, cooperation contractor, and technology transferor.

## Account Role Mapping

Status: governance mapping only; no live Odoo database mutation has been performed.

| Account | Odoo role meaning | Boundary |
| --- | --- | --- |
| `o970106@gmail.com` | 團體會員帳號 / 開發商帳號 | corrected and confirmed by user; live account creation still requires governed Odoo change window |
| `admin@wuchang.life` | 超級管理員帳號 / 主公司負責人帳號 | organization digital representative; does not bypass Five Metric Gate, audit, rollback, or human decision boundary |

Rules:

- Account mapping is metadata until applied through a governed Odoo change window.
- `admin@wuchang.life` may represent Odoo administrative responsibility, but it must not become an unrestricted AI execution identity.
- Group member/developer account and main company responsible account must remain separate authority windows.
- Any live Odoo user creation, role assignment, or permission mutation requires manifest, dry-run/preflight, audit, rollback, and human decision.
