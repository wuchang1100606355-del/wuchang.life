# W7TP-004 / W7TP-005 / W7TP-007 Handoff Map

狀態：PLANONLY / CONTROL MAP ONLY

## Flow

LINE 居民入口 W7TP-005
-> xiaoj_line_resident_intent_draft
-> Open WebUI 本地工作台 W7TP-004
-> staff_action_draft
-> 志工外送服務 W7TP-007
-> delivery_request_draft / staff_review / volunteer_accept

## Responsibility

- W7TP-005：居民 LINE 入口、webhook mock、resident flow routing。
- W7TP-004：人工審核台、DLQ 判讀、草稿 action 產生。
- W7TP-007：志工外送草稿、漸進式個資解鎖、動態完成 token。

## Hardwall

- LINE 不等於身分驗證。
- WiFi 只代表社區場域，不代表個人身分。
- Open WebUI action 只產生 plan-only 草稿。
- W7TP-007 不自動派高風險單。
- Odoo 本階段不寫入。
- raw PII 不送雲端。
