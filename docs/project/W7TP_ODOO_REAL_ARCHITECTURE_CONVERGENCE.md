# W7TP Odoo 真實架構收斂表

TIME=2026-05-26T00:36:08

## 1. 來源

- parsed_observer_json=runtime/reports/W7TP_REAL_ODOO_ADDON_FIELD_OBSERVATION_20260526_002908.json
- field_scan_md=runtime/reports/W7TP_FIELD_SCAN_20260526_003138.md

## 2. 場觀結論

- parsed_addons=15
- field_manifest_lines=56
- field_compose_lines=50

判斷：目前 Odoo 架構不得視為單一 addon。應以真實 manifest、depends、models、security、views、docker compose 與掛載路徑建立 canonical 架構圖。

## 3. Parsed Addon 總覽

| addon | path | installable | depends | models | bagua_hint |
|---|---|---:|---|---:|---|
| pm3_base | Taiji_Odoo/addons/pm3_base | True | base | 1 | A1_core_governance |
| taiji_member_login | Taiji_Odoo/addons/taiji_member_login | True | web | 0 | A2_resident_entry |
| wuchang_cafe_menu_options | Taiji_Odoo/addons/wuchang_cafe_menu_options | True | base, product, point_of_sale, wuchang_cafe_ai_gateway | 3 | A4_merchant_cloud |
| wuchang_core | Taiji_Odoo/addons/wuchang_core | True | base, point_of_sale, account | 9 | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A5_committee_service |
| wuchang_fund_allocation | Taiji_Odoo/addons/wuchang_fund_allocation | True | base, wuchang_fund_reserve | 2 | unclassified |
| wuchang_google_member_login | Taiji_Odoo/addons/wuchang_google_member_login | True | base, web | 0 | A1_core_governance, A2_resident_entry |
| wuchang_knowledge_sync | Taiji_Odoo/addons/wuchang_knowledge_sync | True | base | 4 | unclassified |
| wuchang_line_login | Taiji_Odoo/addons/wuchang_line_login | True | base, web | 2 | A2_resident_entry, A4_merchant_cloud, A7_integration_bridge |
| wuchang_property_local_cloud | Taiji_Odoo/addons/wuchang_property_local_cloud | True | base | 22 | A1_core_governance, A2_resident_entry, A4_merchant_cloud |
| wuchang_property_manpower_surface | Taiji_Odoo/addons/wuchang_property_manpower_surface | True | base | 4 | A2_resident_entry |
| wuchang_wish_tree_coin | Taiji_Odoo/addons/wuchang_wish_tree_coin | True | base, wuchang_property_local_cloud | 8 | unclassified |
| wuchang_comm_incub | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_comm_incub | True | base, portal, point_of_sale | 5 | A1_core_governance, A3_volunteer_delivery |
| wuchang_m1_property | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property | True | wuchang_m3_volunteer, project, maintenance, mail | 1 | A3_volunteer_delivery |
| wuchang_m3_volunteer | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m3_volunteer | True | hr, project | 4 | A3_volunteer_delivery |
| wuchang_property_core | reviews/odoo18_property_candidate/wuchang_property_core | True | base, mail, project, maintenance | 1 | A1_core_governance |

## 4. 七維八陣歸類

### A1_core_governance
- pm3_base
- wuchang_comm_incub
- wuchang_core
- wuchang_google_member_login
- wuchang_property_core
- wuchang_property_local_cloud

### A2_resident_entry
- taiji_member_login
- wuchang_core
- wuchang_google_member_login
- wuchang_line_login
- wuchang_property_local_cloud
- wuchang_property_manpower_surface

### A3_volunteer_delivery
- wuchang_comm_incub
- wuchang_core
- wuchang_m1_property
- wuchang_m3_volunteer

### A4_merchant_cloud
- wuchang_cafe_menu_options
- wuchang_line_login
- wuchang_property_local_cloud

### A5_committee_service
- wuchang_core

### A7_integration_bridge
- wuchang_line_login

### unclassified
- wuchang_fund_allocation
- wuchang_knowledge_sync
- wuchang_wish_tree_coin

## 5. 真實系統處理原則

- 不再假設單一 addon。
- 若 xiaoj_community_service 存在，先標 phase0_integrated_addon。
- 既有 addon 不刪除，先建立依賴與職責定位。
- 商家、志工、會員、管委會、隱私 custody 可分模組，但必須共享 W7TP ontology。
- 多 Odoo 邦聯、多公司、多 POS、多網域可並存；不得混帳、不得混 raw PII、不得繞過 Gateway。

## 6. 下一步

1. 建立 W7TP_ODOO_CANONICAL_ADDON_REGISTRY.md。
2. 標示正式、暫存、舊版、重複、可安裝、不可安裝 addon。
3. 再依 registry 安裝或更新指定 addon。

## 7. Hardwall

- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false
- ARCHITECTURE_CONVERGENCE_ONLY=true

