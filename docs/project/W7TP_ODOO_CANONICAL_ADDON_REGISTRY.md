# W7TP Odoo Canonical Addon Registry

TIME=2026-05-26T00:37:33

## 1. 結論

- manifest_records=24
- duplicate_addon_names=2
- 本次只建立 registry，不安裝、不重啟、不寫 DB。

## 2. Addon Registry

| addon | path_class | recommendation | installable | models | bagua_hint | path |
|---|---|---|---:|---:|---|---|
| pm3_base | canonical_candidate | canonical_candidate | True | 1 | unclassified | Taiji_Odoo/addons/pm3_base |
| taiji_member_login | canonical_candidate | canonical_candidate | True | 0 | A2_resident_entry | Taiji_Odoo/addons/taiji_member_login |
| wuchang_cafe_menu_options | canonical_candidate | canonical_candidate | True | 3 | unclassified | Taiji_Odoo/addons/wuchang_cafe_menu_options |
| wuchang_core | canonical_candidate | canonical_candidate | True | 9 | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A5_committee_service | Taiji_Odoo/addons/wuchang_core |
| wuchang_fund_allocation | canonical_candidate | canonical_candidate | True | 2 | unclassified | Taiji_Odoo/addons/wuchang_fund_allocation |
| wuchang_google_member_login | canonical_candidate | canonical_candidate | True | 0 | A2_resident_entry | Taiji_Odoo/addons/wuchang_google_member_login |
| wuchang_knowledge_sync | canonical_candidate | canonical_candidate | True | 3 | unclassified | Taiji_Odoo/addons/wuchang_knowledge_sync |
| wuchang_line_login | canonical_candidate | canonical_candidate | True | 2 | A2_resident_entry, A4_merchant_cloud | Taiji_Odoo/addons/wuchang_line_login |
| wuchang_property_local_cloud | canonical_candidate | canonical_candidate | True | 15 | A1_core_governance, A2_resident_entry, A4_merchant_cloud | Taiji_Odoo/addons/wuchang_property_local_cloud |
| wuchang_property_manpower_surface | canonical_candidate | canonical_candidate | True | 3 | A2_resident_entry | Taiji_Odoo/addons/wuchang_property_manpower_surface |
| wuchang_wish_tree_coin | canonical_candidate | canonical_candidate | True | 5 | unclassified | Taiji_Odoo/addons/wuchang_wish_tree_coin |
| wuchang_comm_incub | unknown | installable_review_first | True | 5 | A1_core_governance, A3_volunteer_delivery | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_comm_incub |
| wuchang_m1_property | unknown | installable_review_first | True | 1 | unclassified | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property |
| wuchang_m3_volunteer | unknown | installable_review_first | True | 3 | A3_volunteer_delivery | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m3_volunteer |
| wuchang_property_core | unknown | installable_review_first | True | 1 | A1_core_governance | reviews/odoo18_property_candidate/wuchang_property_core |
| wuchang_cafe_menu_options | canonical_candidate | canonical_candidate | True | 3 | unclassified | /home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_cafe_menu_options |
| wuchang_core | canonical_candidate | canonical_candidate | True | 3 | A1_core_governance, A2_resident_entry | /home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_core |
| pm3_runtime_sync | unknown | installable_review_first | True | 2 | unclassified | /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync |
| 08_RuntimeSync | unknown | installable_review_first | True | 0 | A7_integration_bridge | /home/taiji_admin/Taiji_Runtime/wuchang_memory_vault/08_RuntimeSync |
| liaoguo_digital_fantasy_ai | unknown | installable_review_first | True | 1 | unclassified | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai |
| wuchang_community_campaign | unknown | installable_review_first | True | 4 | A3_volunteer_delivery | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_campaign |
| wuchang_community_core | unknown | installable_review_first | True | 0 | A1_core_governance | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core |
| wuchang_core | unknown | installable_review_first | True | 72 | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A4_merchant_cloud, A5_committee_service, A6_privacy_custody, A7_integration_bridge | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core |
| wuchang_finance | unknown | installable_review_first | True | 3 | unclassified | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_finance |

## 3. Duplicate Addon Names

### wuchang_cafe_menu_options
- Taiji_Odoo/addons/wuchang_cafe_menu_options
- /home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_cafe_menu_options

### wuchang_core
- Taiji_Odoo/addons/wuchang_core
- /home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_core
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core

## 4. 安裝規則

- 只允許從 `canonical_candidate` 或明確指定的正式 addon path 安裝。
- `runtime` / `staging` / `archive` / `legacy` 不得直接安裝。
- 重複 addon 名稱必須先裁決 canonical path。
- installable=True 只代表可候選，不代表直接安裝。
- 安裝前須確認 company/accounting/POS/privacy 邊界不混亂。

## 5. Hardwall

- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false
- REGISTRY_ONLY=true

JSON=runtime/reports/W7TP_ODOO_CANONICAL_ADDON_REGISTRY_20260526_003729.json
REPORT=runtime/reports/W7TP_ODOO_CANONICAL_ADDON_REGISTRY_20260526_003729.md
