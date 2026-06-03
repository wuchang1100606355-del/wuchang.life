# W7TP Odoo Addon Install Decision Plan

TIME=2026-05-26T00:39:28
SOURCE=runtime/reports/W7TP_ODOO_CANONICAL_ADDON_REGISTRY_20260526_003729.json

## 1. 結論

- manifest_records=24
- duplicate_addon_names=2
- 本文件只做安裝裁決，不執行 DB 寫入、不安裝、不重啟。

## 2. Duplicate Addon Decision

### wuchang_cafe_menu_options
- score=103 | class=canonical_candidate | rec=canonical_candidate | installable=True | path=Taiji_Odoo/addons/wuchang_cafe_menu_options
- score=103 | class=canonical_candidate | rec=canonical_candidate | installable=True | path=/home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_cafe_menu_options

### wuchang_core
- score=109 | class=canonical_candidate | rec=canonical_candidate | installable=True | path=Taiji_Odoo/addons/wuchang_core
- score=103 | class=canonical_candidate | rec=canonical_candidate | installable=True | path=/home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_core
- score=30 | class=unknown | rec=installable_review_first | installable=True | path=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core

## 3. Top Install Candidates

| score | addon | path_class | recommendation | installable | models | bagua | path |
|---:|---|---|---|---:|---:|---|---|
| 110 | wuchang_property_local_cloud | canonical_candidate | canonical_candidate | True | 15 | A1_core_governance, A2_resident_entry, A4_merchant_cloud | Taiji_Odoo/addons/wuchang_property_local_cloud |
| 109 | wuchang_core | canonical_candidate | canonical_candidate | True | 9 | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A5_committee_service | Taiji_Odoo/addons/wuchang_core |
| 105 | wuchang_wish_tree_coin | canonical_candidate | canonical_candidate | True | 5 | unclassified | Taiji_Odoo/addons/wuchang_wish_tree_coin |
| 103 | wuchang_cafe_menu_options | canonical_candidate | canonical_candidate | True | 3 | unclassified | /home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_cafe_menu_options |
| 103 | wuchang_cafe_menu_options | canonical_candidate | canonical_candidate | True | 3 | unclassified | Taiji_Odoo/addons/wuchang_cafe_menu_options |
| 103 | wuchang_core | canonical_candidate | canonical_candidate | True | 3 | A1_core_governance, A2_resident_entry | /home/taiji_admin/Taiji_Hub_Dependency_Local/Taiji_Odoo/addons/wuchang_core |
| 103 | wuchang_knowledge_sync | canonical_candidate | canonical_candidate | True | 3 | unclassified | Taiji_Odoo/addons/wuchang_knowledge_sync |
| 103 | wuchang_property_manpower_surface | canonical_candidate | canonical_candidate | True | 3 | A2_resident_entry | Taiji_Odoo/addons/wuchang_property_manpower_surface |
| 102 | wuchang_fund_allocation | canonical_candidate | canonical_candidate | True | 2 | unclassified | Taiji_Odoo/addons/wuchang_fund_allocation |
| 102 | wuchang_line_login | canonical_candidate | canonical_candidate | True | 2 | A2_resident_entry, A4_merchant_cloud | Taiji_Odoo/addons/wuchang_line_login |
| 101 | pm3_base | canonical_candidate | canonical_candidate | True | 1 | unclassified | Taiji_Odoo/addons/pm3_base |
| 100 | taiji_member_login | canonical_candidate | canonical_candidate | True | 0 | A2_resident_entry | Taiji_Odoo/addons/taiji_member_login |
| 100 | wuchang_google_member_login | canonical_candidate | canonical_candidate | True | 0 | A2_resident_entry | Taiji_Odoo/addons/wuchang_google_member_login |
| 30 | wuchang_core | unknown | installable_review_first | True | 72 | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A4_merchant_cloud, A5_committee_service, A6_privacy_custody, A7_integration_bridge | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core |
| 25 | wuchang_comm_incub | unknown | installable_review_first | True | 5 | A1_core_governance, A3_volunteer_delivery | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_comm_incub |
| 24 | wuchang_community_campaign | unknown | installable_review_first | True | 4 | A3_volunteer_delivery | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_campaign |
| 23 | wuchang_finance | unknown | installable_review_first | True | 3 | unclassified | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_finance |
| 23 | wuchang_m3_volunteer | unknown | installable_review_first | True | 3 | A3_volunteer_delivery | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m3_volunteer |
| 21 | liaoguo_digital_fantasy_ai | unknown | installable_review_first | True | 1 | unclassified | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai |
| 21 | wuchang_m1_property | unknown | installable_review_first | True | 1 | unclassified | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property |
| 21 | wuchang_property_core | unknown | installable_review_first | True | 1 | A1_core_governance | reviews/odoo18_property_candidate/wuchang_property_core |
| 20 | wuchang_community_core | unknown | installable_review_first | True | 0 | A1_core_governance | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core |
| -8 | pm3_runtime_sync | unknown | installable_review_first | True | 2 | unclassified | /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync |
| -10 | 08_RuntimeSync | unknown | installable_review_first | True | 0 | A7_integration_bridge | /home/taiji_admin/Taiji_Runtime/wuchang_memory_vault/08_RuntimeSync |

## 4. 安裝門檻

- 只安裝 score 最高且 path_class=canonical_candidate 的 addon。
- duplicate addon 必須先指定 canonical path。
- runtime / staging / archive / legacy 不直接安裝。
- installable=True 只是候選，不代表立刻安裝。
- 安裝前須確認該 addon 不會破壞 company/accounting/POS/privacy 邊界。

## 5. 建議下一步

1. 人工確認 duplicate addon 的 canonical path。
2. 人工確認第一個要安裝的 addon。
3. 執行指定 addon 安裝，不再掃全域。

## 6. Hardwall

- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false
- DECISION_PLAN_ONLY=true

