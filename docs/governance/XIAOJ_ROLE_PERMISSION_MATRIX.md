# 小J角色權限矩陣

狀態：PLANONLY / GOVERNANCE DESIGN ONLY

| Role | Default Visible | Forbidden | Notes |
|---|---|---|---|
| AI / 小J | hash、摘要、任務類型 | 姓名、電話、精確地址、API Key、即時位置 | AI 只產候選結果 |
| resident | 自己的服務摘要與進度 | 他人個資、內部審核紀錄 | 個人進度需驗證 |
| volunteer | 已接單任務的最小必要資訊 | 未接單完整個資、電話、API Key | progressive PII unlock |
| staff | 審核所需摘要與必要欄位 | 任意瀏覽全量個資 | 高風險需稽核 |
| merchant | 訂單草稿摘要 | 住戶完整個資 | 僅限業務必要 |
| committee | 統計、公共議題摘要 | 會員個資原文 | 不可匯出個資 |
| system_maintainer | 系統狀態、錯誤碼 | 會員個資、API Key、encrypted payload 解密 | root 不等於解密權 |
| association_admin | 制度管理、稽核流程 | 單獨解密原文 | break-glass 需三鑰門檻 |
| three_key_holder | 持有 key shard / hardware key | 單獨開封 | 2-of-3 或 3-of-3 |

## Hardwall

- single_admin_decrypt_allowed=false
- root_admin_is_not_privacy_access=true
- raw_pii_to_cloud=false
- api_key_plaintext_visible=false
- break_glass_audit_required=true
