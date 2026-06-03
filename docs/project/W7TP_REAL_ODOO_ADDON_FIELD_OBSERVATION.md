# W7TP 真實 Odoo Addon 場觀報告

TIME=2026-05-26T00:29:08
ROOT=/home/taiji_admin/Taiji_Hub

## 1. 場觀結論

- 掃描到 addon manifest 數量：15
- 掃描到 docker-compose 檔案：15
- 本次只讀掃描：DB_WRITE=false / MODULE_INSTALL=false / SERVICE_RESTART=false / SECRET_READ=false

## 2. 必讀治理文件狀態

- docs/project/CONTEXT_COMPACT_HANDOFF.md: exists size=4881
- docs/project/W7TP_ENGINEERING_CONTROL_REGISTER_LATEST.md: exists size=3144
- docs/project/W7TP_COMMUNITY_AI_MVP_CONTROL_SUMMARY_V1.md: exists size=2182
- docs/governance/XIAOJ_MEMBERSHIP_INTENT_DOMAIN_CHARTER.md: exists size=2681
- docs/design/W7TP_ODOO_MODULE_WORLD_CONTEXT_TOPOLOGY.md: missing size=0
- docs/design/W7TP_FEDERATED_ODOO_ORGANIZATION_DOMAIN_TOPOLOGY.md: missing size=0
- docs/design/W7TP_XIAOJ_DEVICE_FEDERATION_TOPOLOGY.md: exists size=1993
- docs/design/W7TP_009_LIAOGUO_COMPANY_POS_IDENTITY_PATCH.md: exists size=1746
- docs/governance/XIAOJ_DESIGNER_ARCHITECT_KEY_LEASING_POLICY.md: exists size=1419

## 3. Docker / Odoo 容器場觀

```text
wuchang_os_indexer w7tp-indexer:latest Restarting (0) 7 seconds ago
wuchang_os_odoo_18 odoo:18.0 Up 4 hours
wuchang_os_pg postgres:15 Up 4 hours
wuchang_gpu_brain ollama/ollama:latest Up 4 hours
```

### wuchang_os_odoo_18 / mounts
```text
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/config/odoo.conf -> /etc/odoo/odoo.conf
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons -> /mnt/extra-addons
/mnt/c/Taiji_Runtime -> /mnt/taiji_runtime
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/odoo_data -> /var/lib/odoo
```

### wuchang_os_odoo_18 / extra_addons_ls
```text
total 64
drwxrwxrwx 13 ubuntu ubuntu  4096 May 23 23:29 .
drwxr-xr-x  1 root   root    4096 May 23 22:20 ..
-rw-r--r--  1 ubuntu ubuntu 10834 May 17 19:09 PM3_SYSTEM_STATUS_INVENTORY.md
drwxr-xr-x  6 ubuntu ubuntu  4096 May 15 05:08 pm3_base
drwxr-xr-x  5 ubuntu ubuntu  4096 May 22 22:02 taiji_member_login
drwxr-xr-x  5 ubuntu ubuntu  4096 May  8 21:36 wuchang_cafe_menu_options
drwxr-xr-x  5 ubuntu ubuntu  4096 May 13 10:58 wuchang_core
drwxr-xr-x  5 ubuntu ubuntu  4096 May 23 17:27 wuchang_fund_allocation
drwxr-xr-x  6 ubuntu ubuntu  4096 May 18 05:32 wuchang_google_member_login
drwxr-xr-x  5 ubuntu ubuntu  4096 May 23 17:20 wuchang_knowledge_sync
drwxr-xr-x  4 ubuntu ubuntu  4096 May 18 06:07 wuchang_line_login
drwxr-xr-x  5 ubuntu ubuntu  4096 May 23 16:16 wuchang_property_local_cloud
drwxr-xr-x  5 ubuntu ubuntu  4096 May 23 23:29 wuchang_property_manpower_surface
drwxr-xr-x  5 ubuntu ubuntu  4096 May 23 22:33 wuchang_wish_tree_coin
```

## 4. Compose Addon / Odoo 線索

### Taiji_Odoo/docker-compose.yml
```text
wuchang_os_odoo_18:
image: odoo:18.0
container_name: wuchang_os_odoo_18
- odoo
- "127.0.0.1:8069:8069"
- ./addons:/mnt/extra-addons
- ./odoo_data:/var/lib/odoo
- ./config/odoo.conf:/etc/odoo/odoo.conf:ro
USER: odoo
POSTGRES_USER: odoo
```
### Wuchang_Odoo_Core/docker-compose.yml
```text
container_name: wuchang_odoo_db
- POSTGRES_USER=odoo
- wuchang_odoo_pg_data:/var/lib/postgresql/data
# 🏢 企業後勤大腦 (Odoo 18)
image: odoo:18.0
container_name: wuchang_odoo_web
- "8069:8069"
- USER=odoo
- wuchang_odoo_web_data:/var/lib/odoo
wuchang_odoo_pg_data:
wuchang_odoo_web_data:
```
### _imports/wuchang-ai-main/wuchang-ai-main/docker-compose.yml
```text
image: odoo:17.0
- "8069:8069"
- ODOO_MASTER_PASSWORD=admin
- ./wuchang_comm_incub:/mnt/extra-addons/wuchang_comm_incub
- ./odoo.conf:/etc/odoo/odoo.conf
- POSTGRES_PASSWORD=odoo
- POSTGRES_USER=odoo
```
### deploy/packages/taiji01_metric_identity_gateway_v0_1/docker-compose.yml
```text
TAIJI_IDENTITY_ALLOWLIST: /taiji/Taiji_Odoo/identity_map/five_code_identity_allowlist.json
- /home/taiji_01/Taiji_Hub/Taiji_Odoo/identity_map:/taiji/Taiji_Odoo/identity_map:ro
```

## 5. Addon 總覽

| addon | path | class | installable | depends | bagua_hint | models |
|---|---|---|---:|---|---|---:|
| pm3_base | Taiji_Odoo/addons/pm3_base | wuchang_taiji | True | base | A1_core_governance | 1 |
| taiji_member_login | Taiji_Odoo/addons/taiji_member_login | wuchang_taiji | True | web | A2_resident_entry | 0 |
| wuchang_cafe_menu_options | Taiji_Odoo/addons/wuchang_cafe_menu_options | wuchang_taiji | True | base, product, point_of_sale, wuchang_cafe_ai_gateway | A4_merchant_cloud | 3 |
| wuchang_core | Taiji_Odoo/addons/wuchang_core | wuchang_taiji | True | base, point_of_sale, account | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A5_committee_service | 9 |
| wuchang_fund_allocation | Taiji_Odoo/addons/wuchang_fund_allocation | wuchang_taiji | True | base, wuchang_fund_reserve | unclassified | 2 |
| wuchang_google_member_login | Taiji_Odoo/addons/wuchang_google_member_login | wuchang_taiji | True | base, web | A1_core_governance, A2_resident_entry | 0 |
| wuchang_knowledge_sync | Taiji_Odoo/addons/wuchang_knowledge_sync | wuchang_taiji | True | base | unclassified | 4 |
| wuchang_line_login | Taiji_Odoo/addons/wuchang_line_login | wuchang_taiji | True | base, web | A2_resident_entry, A4_merchant_cloud, A7_integration_bridge | 2 |
| wuchang_property_local_cloud | Taiji_Odoo/addons/wuchang_property_local_cloud | wuchang_taiji | True | base | A1_core_governance, A2_resident_entry, A4_merchant_cloud | 22 |
| wuchang_property_manpower_surface | Taiji_Odoo/addons/wuchang_property_manpower_surface | wuchang_taiji | True | base | A2_resident_entry | 4 |
| wuchang_wish_tree_coin | Taiji_Odoo/addons/wuchang_wish_tree_coin | wuchang_taiji | True | base, wuchang_property_local_cloud | unclassified | 8 |
| wuchang_comm_incub | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_comm_incub | wuchang_taiji | True | base, portal, point_of_sale | A1_core_governance, A3_volunteer_delivery | 5 |
| wuchang_m1_property | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property | wuchang_taiji | True | wuchang_m3_volunteer, project, maintenance, mail | A3_volunteer_delivery | 1 |
| wuchang_m3_volunteer | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m3_volunteer | wuchang_taiji | True | hr, project | A3_volunteer_delivery | 4 |
| wuchang_property_core | reviews/odoo18_property_candidate/wuchang_property_core | wuchang_taiji | True | base, mail, project, maintenance | A1_core_governance | 1 |

## 6. 重複 Addon 名稱

- none

## 7. 本地依賴圖

- wuchang_wish_tree_coin -> wuchang_property_local_cloud
- wuchang_m1_property -> wuchang_m3_volunteer

## 8. 七維八陣初步歸類

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

## 9. 真實架構判讀規則

- 若 `Taiji_Odoo/addons/xiaoj_community_service` 存在：視為 phase0_integrated_addon，不強制刪除。
- 若已有多個 addon：以實際 manifest / depends / model / security / view 形成真實架構圖。
- 多模組不是分裂；必須共用 W7TP ontology、治理硬牆、角色、隱私、稽核與 company/accounting/POS 邊界。
- 任何安裝 / DB 寫入 / Odoo restart 應在本報告確認真實架構後再執行。

## 10. Hardwall

- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false
- SCAN_ONLY=true

## 11. Output

- JSON=runtime/reports/W7TP_REAL_ODOO_ADDON_FIELD_OBSERVATION_20260526_002908.json
- REPORT=runtime/reports/W7TP_REAL_ODOO_ADDON_FIELD_OBSERVATION_20260526_002908.md
- PROJECT=docs/project/W7TP_REAL_ODOO_ADDON_FIELD_OBSERVATION.md
