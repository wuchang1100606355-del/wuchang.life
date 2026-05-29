# W7TP-008 Odoo Security Access Matrix Design Only

狀態：PLANONLY / DESIGN ONLY / NO IMPLEMENTATION
本階段不建立 addon、不連 DB、不寫 ir.model.access.csv、不啟動服務。

## 角色邊界

- resident：不進 Odoo 後台。
- volunteer：只可看已核定任務的區域級摘要，不看姓名、電話、精確地址。
- renyi_store_staff：可核定陪同志工外送任務草稿。
- staff：可審核草稿與產生 plan-only action，不可單獨解密 raw PII。
- committee：只看統計與公共議題摘要。
- system_maintainer：只看系統狀態與錯誤碼，不看 raw PII、API key、encrypted payload。
- privacy_officer：管理 break-glass 流程，不可單人開封。

## Odoo Hardwall

- 不保存 plaintext master key。
- 不讓 system_maintainer 讀 raw PII。
- 不讓 volunteer 直接查居民資料。
- 不允許 AI 自動 write。
- 不允許 Odoo action 繞過 W7TP Gateway。
- break-glass 必須接 W7TP-016 三鑰制度。
