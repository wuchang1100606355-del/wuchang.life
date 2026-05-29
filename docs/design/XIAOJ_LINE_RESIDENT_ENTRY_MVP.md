# W7TP-005 LINE 小J居民入口 MVP

狀態：PLANONLY / DESIGN + MOCK ONLY
目的：讓居民用 LINE 低成本體驗小J服務，形成社區 AI 公共服務入口。
Odoo：不寫入。LINE：不連線。雲端：不送 raw PII。

## 1. 居民主入口

- 社區公告
- 活動報名
- 報修草稿
- 志工外送協助
- 商家點餐草稿
- 管委會問題
- 小J AI 問答
- 程式設計需求

## 2. 路由原則

- community_redacted_lane：社區 WiFi / 公共服務場域。
- personal_privacy_lane：個人資料、家戶資料、服務進度。
- staff_review_lane：高風險、個資、外送、管委會、金流相關。
- dlq_lane：違規、越權、個資疑似外送、提示詞注入。

## 3. LINE Rich Menu MVP

1. 問小J
2. 社區服務
3. 外送協助
4. 商家點餐
5. 報修 / 反映問題
6. 我的進度

## 4. Hardwall

- LINE 階段不要求完整身分證、完整電話、完整門牌。
- WiFi 只代表社區場域，不代表個人身分。
- 個人進度查詢需登入、授權或一次性驗證。
- AI 只產生草稿與候選結果，不直接派單、不直接寫 Odoo。
- 雲端 lane 只接收 redacted_summary / hash / non-PII shard。
