# W7TP Engineering Control Register Latest

更新狀態：PLANONLY / CONTROL REGISTER ONLY

| ID | Title | Status | Priority | Risk | PII Level | Completion | Next Action |
|---|---|---|---|---|---|---:|---|
| W7TP-004 | Open WebUI 本地小J工作台 | workspace_integration_design_done | P1 | L2 | redacted_or_association_controlled | 75% | actual Open WebUI plugin/workspace design only |
| W7TP-005 | LINE 小J居民入口 | consent_one_time_verification_done | P1 | L2 | redacted_or_association_controlled | 75% | real LINE endpoint design only |
| W7TP-007 | 志工外送服務接單 | renyi_caregiver_hardwall_synced | P1 | L3 | association_controlled | 95% | human governance review / Odoo design only |
| W7TP-008 | Odoo 預留模組 | addon_file_layout_design_done | P1 | L3 | association_controlled | 75% | human review / no implementation until authorization |
| W7TP-016 | Admin-blind privacy + 三鑰保管制度 | cryptographic_design_only_done | P0 | L4 | raw_pii_protected_by_threshold_custody | 90% | governance review / no real key generation |

## Integrated Service Chain

W7TP-005 LINE resident entry
-> W7TP-004 Open WebUI staff workbench
-> W7TP-007 volunteer delivery service
-> W7TP-008 Odoo reserved backend design only
-> W7TP-016 admin-blind privacy / three-key custody

## Global Hardwall

- PLANONLY=true
- ODOO_WRITE=false
- DB_CONNECT=false
- ADDON_CREATE=false
- RAW_PII_TO_CLOUD=false
- NO_SERVICE_RESTART=true
- NO_SECRET_READ=true
- WIFI_IS_NOT_IDENTITY=true
- SINGLE_ADMIN_DECRYPT_ALLOWED=false
- ROOT_ADMIN_IS_NOT_PRIVACY_ACCESS=true
- AI_RESULT_IS_CANDIDATE_ONLY=true
- VOLUNTEER_SELF_ACCEPT_ALLOWED=false
- RENYI_STORE_STAFF_CAREGIVER_QUALIFIED=true
- RENYI_STORE_STAFF_APPROVAL_AND_ACCOMPANIMENT_REQUIRED=true

## W7TP-009 LiaoGuo Company/POS Identity Patch

- 上品食品行 / POS 上品聊國咖啡館 重新總店 / 統編 34778660 / 負責人 江政隆：外部友軍贊助公司。
- 新北市三重區五常社區發展協會 / POS 上品聊國咖啡館 仁義分店 / 統編同協會統編 / 負責人 江政隆（協會派任）：社區公益基金池主體。
- 外送合作商家示範 POS：合作模板，不混帳。

## W7TP-009 Google Workspace Account Patch

- Google account: o970106@gmail.com
- 用途：上品食品行作為 Google Workspace / Odoo 技術服務提供者之識別帳號。
- 不保存密碼、token、API key、recovery code。
- 技術帳號不等於 raw PII 解密權，不等於協會資料所有權。

## Designer Architect Key Leasing Policy Update

- OpenAI/API key 不分類為一般 vendor key，而是 designer_architect_provided_key。
- 協會向設計人租用受 W7TP 脫敏與分片治理的 API 算力 / key service。
- 協會不持有 key 明文，設計人不取得協會 raw PII；外部 API 只接收 non-PII shard。

## W7TP / XiaoJ Device Federation Topology Update

- 小J系統總成為：會員使用者設備、團體會員三件式設備、協會意圖架構設備。
- 系統不是單一伺服器，而是分散式意圖治理網。
- 所有設備依七維身份碼、角色、授權、同意、隱私邊界與 W7TP Gateway 運作。
