# W7TP Odoo 七維八陣張量網整合任務

請讀取目前 repo，以七維八陣張量網整理並整合 Odoo 架構。

## 模式

- PLANONLY + FILE_LAYER_ONLY
- 禁止 DB_CONNECT
- 禁止 MODULE_INSTALL
- 禁止 SERVICE_RESTART
- 禁止 SECRET_READ
- 禁止 RAW_PII_TO_CLOUD
- 禁止 CROSS_COMPANY_ACCOUNTING_MIX

## 七維

D1 Identity：會員、居民、志工、商家團體會員、非轄區團體贊助會員、仁義店照服員資格職員、管委會、協會人員、技術服務提供者、設計人  
D2 Time：一次性驗證、動態 token、break-glass expiry、服務狀態時間窗  
D3 Topology：會員設備、團體會員三件式設備、協會意圖架構設備、Odoo 邦聯子域/次級網域  
D4 Resource：Odoo addon、POS、Open WebUI、LINE、Gateway、Google Workspace、API key service  
D5 Risk：L0/L1/L2/L3/L4/DLQ  
D6 Governance：PLANONLY、Admin-blind privacy、三鑰制度、仁義店照服員陪同、WiFi 不等於身分、會員主權維護 AI  
D7 Action：read/report/design/file_patch only

## 八陣

A1 xiaoj_core_governance  
A2 xiaoj_resident_entry  
A3 xiaoj_volunteer_delivery  
A4 xiaoj_merchant_cloud  
A5 xiaoj_committee_service  
A6 xiaoj_privacy_custody  
A7 xiaoj_integration_bridge  
A8 xiaoj_federation_registry  

## 必讀

- docs/project/CONTEXT_COMPACT_HANDOFF.md
- docs/project/W7TP_ENGINEERING_CONTROL_REGISTER_LATEST.md
- docs/project/W7TP_COMMUNITY_AI_MVP_CONTROL_SUMMARY_V1.md
- docs/governance/XIAOJ_MEMBERSHIP_INTENT_DOMAIN_CHARTER.md
- docs/design/W7TP_ODOO_MODULE_WORLD_CONTEXT_TOPOLOGY.md
- docs/design/W7TP_FEDERATED_ODOO_ORGANIZATION_DOMAIN_TOPOLOGY.md
- docs/design/W7TP_XIAOJ_DEVICE_FEDERATION_TOPOLOGY.md
- docs/design/W7TP_009_LIAOGUO_COMPANY_POS_IDENTITY_PATCH.md
- docs/design/W7TP_009_SHANGPIN_DEVELOPER_PROVIDER_PATCH.md
- docs/design/W7TP_009_EXTERNAL_SPONSOR_GROUP_MEMBER_PATCH.md
- docs/governance/XIAOJ_DESIGNER_ARCHITECT_KEY_LEASING_POLICY.md
- docs/project/W7TP_008_ODOO_RESERVED_MODULE_FINAL_EVIDENCE.md
- Taiji_Odoo/addons

## 任務

1. 產出 docs/project/W7TP_ODOO_7D_BAGUA_ARCHITECTURE_INDEX.md
2. 產出 docs/design/W7TP_ODOO_PHASE0_TO_BAGUA_MODULE_MIGRATION_MAP.md
3. 產出 schemas/w7tp_odoo_bagua_module_manifest.schema.json
4. 產出 runtime/mock/w7tp_odoo_bagua_module_manifest_mock.json
5. 產出 runtime/reports/W7TP_ODOO_7D_BAGUA_ARCHITECTURE_INDEX_<timestamp>.md
6. 驗證 JSON 為 json_ok
7. 若 Taiji_Odoo/addons/xiaoj_community_service 存在，標為 transitional_monolith / phase0_integrated_addon，不刪除。
8. 不強迫單一 addon；多 addon 必須同世界、同治理、同資料邊界。
9. 最後輸出 DONE_* 與 json_ok。
