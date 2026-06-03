# W7TP-005 LINE 居民入口流程測試

狀態：PLANONLY / MOCK ONLY
目的：驗證居民從 LINE rich menu 進入小J服務後，能被正確分流。

## Test Flow

1. 居民點選「問小J」：走 community_redacted_lane。
2. 居民點選「社區服務」：走 community_redacted_lane。
3. 居民點選「外送協助」：走 W7TP-007 delivery draft。
4. 居民點選「商家點餐」：走 ordering draft。
5. 居民點選「報修 / 反映問題」：走 repair draft / staff review。
6. 居民點選「我的進度」：需要 personal_privacy_lane 驗證。

## Redteam Verdict

- WiFi 只代表社區場域，不代表個人身分。
- 查個人進度需登入、授權或一次性驗證。
- AI 只產生草稿，不直接寫 Odoo。
- 高風險或個資疑似外送進 staff_review_lane / dlq_lane。
