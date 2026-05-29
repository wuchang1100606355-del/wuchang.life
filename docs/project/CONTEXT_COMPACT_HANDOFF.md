# CONTEXT_COMPACT_HANDOFF

用途：跨對話 / 跨代理交接用壓縮索引。
狀態：PLANONLY / SUMMARY ONLY
原則：不展開照片、不保留大段終端輸出、不保留逐字貼文，只保留標題、成果、路徑、狀態。

## 1. 全域硬牆

- PLANONLY=true
- ODOO_WRITE=false
- DB_CONNECT=false
- ADDON_CREATE=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false
- WIFI_IS_NOT_IDENTITY=true
- SINGLE_ADMIN_DECRYPT_ALLOWED=false
- ROOT_ADMIN_IS_NOT_PRIVACY_ACCESS=true
- AI_RESULT_IS_CANDIDATE_ONLY=true
- VOLUNTEER_SELF_ACCEPT_ALLOWED=false
- RENYI_STORE_STAFF_CAREGIVER_QUALIFIED=true
- RENYI_STORE_STAFF_APPROVAL_AND_ACCOMPANIMENT_REQUIRED=true

## 2. 工項狀態總覽

| ID | Module | Status | Completion |
|---|---|---|---:|
| W7TP-004 | Open WebUI 本地小J工作台 | workspace_integration_design_done | 75% |
| W7TP-005 | LINE 小J居民入口 | consent_one_time_verification_done | 75% |
| W7TP-007 | 志工外送服務接單 | renyi_caregiver_hardwall_synced | 95% |
| W7TP-008 | Odoo 預留模組 | addon_file_layout_design_done | 75% |
| W7TP-016 | Admin-blind privacy + 三鑰制度 | cryptographic_design_only_done | 90% |

## 3. 整合服務鏈

LINE 小J居民入口 W7TP-005
-> Open WebUI 本地小J工作台 W7TP-004
-> 志工外送服務接單 W7TP-007
-> Odoo 預留後台設計 W7TP-008
-> Admin-blind privacy / 三鑰保管 W7TP-016

## 4. 核心證據檔

### 總表
- docs/project/W7TP_ENGINEERING_CONTROL_REGISTER_LATEST.md
- docs/project/W7TP_COMMUNITY_AI_MVP_CONTROL_SUMMARY_V1.md

### W7TP-004
- docs/project/W7TP_004_OPENWEBUI_LOCAL_WORKBENCH_FINAL_EVIDENCE.md
- docs/design/XIAOJ_OPENWEBUI_WORKSPACE_INTEGRATION_DESIGN.md
- web/xiaoj_openwebui_workbench/index.html
- schemas/xiaoj_openwebui_tool_manifest_draft.schema.json
- runtime/mock/xiaoj_openwebui_tool_manifest_mock.json

### W7TP-005
- docs/project/W7TP_005_LINE_RESIDENT_ENTRY_FINAL_EVIDENCE.md
- docs/design/XIAOJ_LINE_CONSENT_ONE_TIME_VERIFICATION.md
- schemas/xiaoj_line_one_time_verification.schema.json
- runtime/mock/xiaoj_line_one_time_verification_mock.json

### W7TP-007
- docs/project/W7TP_007_VOLUNTEER_DELIVERY_FINAL_EVIDENCE.md
- docs/governance/XIAOJ_VOLUNTEER_QUALIFICATION_POLICY.md
- schemas/xiaoj_volunteer_qualification_record.schema.json
- runtime/mock/xiaoj_volunteer_qualification_mock.json

### W7TP-008
- docs/project/W7TP_008_ODOO_RESERVED_MODULE_FINAL_EVIDENCE.md
- docs/design/XIAOJ_ODOO_RESERVED_MODULE_DESIGN_ONLY.md
- docs/design/XIAOJ_ODOO_SECURITY_ACCESS_MATRIX_DESIGN_ONLY.md
- docs/design/XIAOJ_ODOO_ADDON_FILE_LAYOUT_DESIGN_ONLY.md
- schemas/xiaoj_odoo_addon_file_layout_manifest.schema.json
- runtime/mock/xiaoj_odoo_addon_file_layout_manifest_mock.json

### W7TP-016
- docs/project/W7TP_016_ADMIN_BLIND_PRIVACY_FINAL_EVIDENCE.md
- docs/governance/XIAOJ_ADMIN_BLIND_PRIVACY_HARDWALL.md
- docs/governance/XIAOJ_THREE_KEY_CIVIC_CUSTODY_POLICY.md
- docs/governance/XIAOJ_CRYPTOGRAPHIC_IMPLEMENTATION_DESIGN_ONLY.md
- schemas/xiaoj_encrypted_payload_envelope.schema.json
- runtime/mock/xiaoj_encrypted_payload_envelope_mock.json

## 5. 重要制度定案

### 仁義店照服員硬牆
- 志工接單須由具照服員資格之仁義店職員核定並陪同 / 監督。
- 志工不得自行接單。
- 未核定不得進入 accepted。
- 未陪同 / 監督不得進入 pii_limited_unlocked。

### Admin-blind privacy
- 協會依法物理控管個資。
- 單一 admin / founder / root 不等於解密權。
- 三里長三 USB / 硬體金鑰門檻制。
- break-glass 必須有目的、範圍、期限、稽核。

### LINE 身分邊界
- WiFi 只代表社區場域，不代表個人身分。
- LINE user hash 不等於完整會員身分。
- 個人進度查詢需 one-time verification / staff_verified / renyi_staff_verified。

### Odoo 邊界
- 目前只做預留模組設計。
- 不建立 addon。
- 不連 DB。
- 不寫 Odoo。
- 不允許 Odoo action 繞過 W7TP Gateway。

## 6. 已清理上下文規則

- 照片：只保留用途標題，不展開內容。
- 終端輸出：只保留 DONE_*、json_ok、路徑、狀態。
- 指令錯誤：只保留原因分類，不保留長輸出。
- 重複貼文：只保留最後成功結果。

## 7. 下一步候選

1. W7TP-004 actual Open WebUI plugin/workspace design only。
2. W7TP-005 real LINE endpoint design only。
3. W7TP-008 Odoo implementation gate checklist。
4. W7TP-016 human governance review checklist。
5. 產出可交付壓縮包 / evidence package index。

## Device Federation Topology Update

- docs/design/W7TP_XIAOJ_DEVICE_FEDERATION_TOPOLOGY.md
- 三類設備：會員使用者設備、團體會員三件式設備、協會意圖架構設備。
- 團體會員三件式設備=POS + 店內伺服器/服務電腦 + 客顯服務電腦。
- 協會意圖架構設備=W7TP Gateway + Open WebUI + Odoo 邦聯 + privacy custody + audit/DLQ。
