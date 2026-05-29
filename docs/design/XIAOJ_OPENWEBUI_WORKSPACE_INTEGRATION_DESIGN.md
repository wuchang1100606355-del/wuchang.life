# W7TP-004 Open WebUI 工作區整合設計

狀態：PLANONLY / DESIGN + MOCK ONLY
目的：把 Open WebUI 作為協會人員、店員、志工、管理者的小J工作台入口。
本階段不修改 Open WebUI、不啟動服務、不新增真實 tool、不寫 Odoo。

## 1. Workspace 定位

- 工作區名稱：小J社區服務工作台
- 使用對象：協會人員、仁義店職員、志工、管委會、商家、開發維護者
- 功能定位：審核草稿、檢查風險、產生 PLANONLY action、查看 mock evidence

## 2. 建議 Open WebUI 工作區卡片

1. LINE 居民入口草稿卡：W7TP-005
2. 志工外送審核卡：W7TP-007
3. 仁義店照服員核定陪同卡：W7TP-007 hardwall
4. Admin-blind privacy / break-glass 卡：W7TP-016
5. DLQ 高風險事件卡
6. 工程管制總表卡

## 3. 建議 Functions / Tools 設計

- xiaoj_read_control_register：只讀工程管制總表。
- xiaoj_load_line_intent_mock：只讀 LINE intent mock。
- xiaoj_load_delivery_review_mock：只讀外送審核 mock。
- xiaoj_create_staff_action_draft：只產生 plan-only action draft。
- xiaoj_send_to_dlq_draft：只產生 DLQ draft。
- xiaoj_privacy_break_glass_plan：只產生 break-glass plan，不開封。

## 4. 禁止 Functions / Tools

- 不提供 Odoo write tool。
- 不提供 shell / docker / ssh tool。
- 不提供 secrets / env / logs / vault / memory 讀取 tool。
- 不提供 raw PII export tool。
- 不提供自動派單或自動結案 tool。

## 5. Prompt / System Instruction 邊界

- 所有 action 均為 PLANONLY。
- AI 回覆只可作候選建議。
- 個資欄位需顯示為 redacted_summary / hash / area_level。
- 高風險事件必須進 human_review 或 DLQ。
- 志工外送須由具照服員資格之仁義店職員核定陪同。

## 6. Hardwall

- PLANONLY=true
- ODOO_WRITE=false
- RAW_PII_TO_CLOUD=false
- NO_SERVICE_RESTART=true
- NO_SECRET_READ=true
- VOLUNTEER_SELF_ACCEPT_ALLOWED=false
- RENYI_STORE_STAFF_CAREGIVER_QUALIFIED=true
- SINGLE_ADMIN_DECRYPT_ALLOWED=false
