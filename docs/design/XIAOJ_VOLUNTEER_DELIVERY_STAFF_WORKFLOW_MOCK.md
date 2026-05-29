# W7TP-007 Staff Review Workflow Mock

狀態：PLANONLY / MOCK ONLY
Odoo：不寫入

## Staff Workflow

1. staff 開啟 Open WebUI 審核卡。
2. 匯入 delivery_request_draft mock JSON。
3. 檢查 high_risk_flags。
4. 檢查是否需要人工關懷。
5. 檢查是否可進 waiting_volunteer_accept。
6. 產生 staff_decision JSON。

## Decision Types

- approve_to_waiting_volunteer_accept
- request_more_info
- human_care_review
- dead_letter_review
- cancelled_by_requester

## Hardwall

- staff decision 仍為 plan-only。
- 不自動寫 Odoo。
- 不自動派高風險單。
- 不揭露姓名、電話、精確地址、即時位置到雲端。
- 志工接單前只可見區域級資訊。
