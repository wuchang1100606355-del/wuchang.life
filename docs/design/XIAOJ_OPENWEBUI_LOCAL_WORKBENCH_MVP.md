# W7TP-004 Open WebUI 本地小J工作台 MVP

狀態：PLANONLY / DESIGN + MOCK ONLY
目的：讓協會人員、店員、志工、管理者在 Open WebUI 內審核小J草稿與服務流程。
Odoo：不寫入。服務：不啟動。個資：不送雲端。

## 1. 工作台定位

- 小J居民入口的人工審核台
- 志工外送服務的審核卡與派單前檢查台
- LINE webhook 草稿的檢視台
- 社區服務、商家點餐、報修、程式需求的草稿整理台
- DLQ / 高風險事件的人工判讀台

## 2. 角色

- staff：協會人員 / 店員
- volunteer：志工
- committee：管委會
- merchant：商家
- developer：開發者 / 維護者
- human_review：人工審核節點

## 3. 工作台主要卡片

1. LINE 居民意圖草稿卡
2. 志工外送審核卡
3. 高風險 DLQ 卡
4. 商家點餐草稿卡
5. 報修 / 管委會問題卡
6. 小J社區程式設計需求卡

## 4. 操作原則

- 所有按鈕只產生 plan-only action。
- 不直接寫 Odoo。
- 不自動派單。
- 不自動結案。
- 高風險需 human_review。
- 個資只顯示最小必要摘要。

## 5. Hardwall

- No Odoo write
- No service start/restart
- No .env/logs/memory/vault/backup read
- No raw PII to cloud
- AI result is candidate only
