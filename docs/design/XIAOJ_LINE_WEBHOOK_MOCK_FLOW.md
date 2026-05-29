# W7TP-005 LINE Webhook Mock Flow

狀態：PLANONLY / MOCK ONLY
目的：模擬 LINE 事件進入 W7TP Gateway 後，如何轉成居民意圖草稿。
Odoo：不寫入。LINE：不連線。雲端：不送 raw PII。

## Flow

LINE event
-> W7TP Gateway
-> redaction gate
-> intent classifier
-> xiaoj_line_resident_intent_draft
-> community_redacted_lane / personal_privacy_lane / staff_review_lane / dlq_lane

## Mock Case

居民點選「申請外送協助」。
系統只產生去識別化 summary 與 route，不產生正式派單。

## Hardwall

- 不讀取完整姓名、電話、精確門牌。
- 不將 raw PII 送雲端。
- 不自動寫 Odoo。
- 不自動派單。
- 高風險轉 staff_review_lane 或 dlq_lane。
