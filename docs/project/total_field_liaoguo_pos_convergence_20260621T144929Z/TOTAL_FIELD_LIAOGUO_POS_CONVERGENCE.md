# Total Field Liaoguo POS Convergence Packet

STATE=TOTAL_FIELD_CONVERGED
RUN_ID=TOTAL_FIELD_LIAOGUO_POS_CONVERGENCE_20260621T144929Z
HOST=taiji01
ROOT=/home/taiji_admin/Taiji_Hub
WRITE_SCOPE=docs/project total_field packet only

## D1_IDENTITY
Converged subject: Shangpin Liaoguo Cafe / Liaoguo Cafe commercial POS system design.

Local authority remains Total Field / taiji01. Google Drive findings are account-local candidate evidence and must be reconstructed against local repo evidence before action.

## D2_INTENT
Converge account-local and repo-local evidence about the cafe POS design into one Total Field packet for later verification, reconstruction, and governed action.

## D3_STATE
Read-only probe completed.

No database write, service restart, deployment, sync, LINE WORKS send, Odoo mutation, POS mutation, or browser automation was performed.

Observed current POS design state:

- Odoo POS is the core business system design surface.
- PostgreSQL is the persistence layer in the design documents.
- Store Apprentice / local agent is described as the edge bridge for Android POS and browser-managed legacy systems.
- Quick Click source menu data exists in Drive as `pos_menu_source_20260108.xlsx`.
- Local Odoo addons exist for POS topology, cafe menu option normalization, POS config extension, community coin/ticket policy, and menu import.
- The Drive POS reports list two active Odoo POS configs named `上品聊國咖啡館重新總店` with IDs 3 and 4, both company_id 1, plus one disabled `Shop` and one active `Restaurant`.
- A naming/identity collision exists in the Drive POS reports: POS ID 3 and POS ID 4 share the same cafe POS name.

## D4_TOPOLOGY
Converged topology:

```text
Member / staff / customer intent
-> local / mobile / POS interface
-> Natural Intent POS Gateway or Quick Click / Android POS
-> Odoo POS draft or controlled POS config
-> human confirmation / policy gate
-> Odoo / PostgreSQL record
-> audit / rollback / evidence
```

Physical / network design from evidence:

- Cafe main store / Chongxin store: `上品聊國咖啡館重新總店`.
- Store address from local POS setup: `新北市三重區重新路三段204號`.
- Store node design includes Odoo on port 8069, Android/Sunmi POS, Store Apprentice, Quick Click label printer, ASUS router, and LAN `192.168.50.x/24`.
- Prior deployment status marks POS and customer display device identities as pending inventory before live deployment.

## D5_RESOURCE
Primary local repo evidence:

- `docs/design/W7TP_009_LIAOGUO_COMPANY_POS_IDENTITY_PATCH.md`
- `docs/taiji_natural_intent_pos_gateway_zh.md`
- `docs/system_memory/pos_four_piece_and_community_merchant_member.md`
- `Taiji_Governance/deployments/cafe_main_redeploy_status.md`
- `Taiji_Odoo/addons/wuchang_pos_topology/__manifest__.py`
- `Taiji_Odoo/addons/wuchang_cafe_menu_options/__manifest__.py`
- `Taiji_Odoo/addons/wuchang_cafe_menu_options/models/menu_options.py`
- `Taiji_Odoo/addons/wuchang_core/models/pos_config_ext.py`
- `Taiji_Odoo/addons/wuchang_core/data/pos_setup.xml`
- `Taiji_Odoo/addons/wuchang_core/controllers/menu_import.py`
- `Taiji_Odoo/addons/wuchang_core/models/menu.py`
- `Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_pos_policy.py`

Primary Drive evidence observed through connector search:

- `LIAOGUO_CAFE_SYSTEM_PLAN.md`
- `POS_SYSTEMS_SUMMARY.md`
- `POS_SYSTEMS_REPORT.md`
- `pos_menu_source_20260108.xlsx`
- `ABILITY_ABSORPTION_POS.md`
- `社區Odoo二次消費評估與行銷`

## D6_GOVERNANCE
Hard boundaries:

- `上品食品行 / 重新總店` must not be mixed with `五常社區發展協會 / 仁義分店`.
- `34778660` belongs to 上品食品行 and must not replace the association tax ID.
- Re-main store accounting must not flow into the association fund pool.
- Renyi public-welfare fund pool must not flow into the main store commercial account.
- POS scopes require separation by company, branch, accounting scope, and POS scope.
- Raw PII to cloud is forbidden.
- Odoo write, POS write, DB connect, deployment, and service restart remain forbidden in this convergence packet.

## D7_VERIFICATION
Completed checks:

- Local repo read-only `rg` and file reads found POS/Odoo/cafe system design and addon sources.
- Google Drive read-only searches found matching POS reports, system plans, menu source data, and community economic model documents.
- Python syntax check passed for:
  - `Taiji_Odoo/addons/wuchang_core/models/pos_config_ext.py`
  - `Taiji_Odoo/addons/wuchang_cafe_menu_options/models/menu_options.py`
  - `Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_pos_policy.py`

Verification limits:

- This packet does not prove live Odoo runtime status.
- This packet does not prove current database state.
- This packet does not prove Store Apprentice is currently running.
- This packet does not prove Sunmi POS identity is currently bound.
- Drive POS reports are evidence of prior observed state, not current live state.

## D8_ENVELOPE
Convergence result:

```text
STATE
-> Coordinate
-> Hash
-> Packet
-> Evidence
```

Generative Transfer is not invoked here because the user requested convergence to Total Field, not cloud candidate generation.

## LOCAL_RECONSTRUCTION
Local reconstruction path:

1. Treat Drive files as candidate evidence.
2. Reconstruct concrete design state from local repo files.
3. Require runtime read-only Odoo/database probe before claiming live state.
4. Require device inventory for Sunmi POS and customer display before action.
5. Require human approval before any Odoo/POS/router/LINE WORKS write.

## NEXT_SAFE_ACTION
Next safe action, if requested:

Run a read-only runtime probe of Odoo POS config names and device identities, then compare the live result against this convergence packet.

## SAFETY_FLAGS
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
TOKEN_PRINT=FALSE
DB_WRITE=FALSE
ODOO_WRITE=FALSE
POS_ACTION=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
