# Association Data Authority Matrix

版本：2026-05-11

| 資料類型 | 權限主體 | 可用位置 | 上雲 | 審查 |
|---|---|---|---|---|
| 無敏白皮書 | 本會 / 專案 | Linux, Cloud, D | YES readonly | 一般 audit |
| 架構圖 / schema | 本會 / 專案 | Linux, Cloud, D | YES readonly | 一般 audit |
| 團體會員資料 | 本會保護資訊責任 | C, Linux conditional, D conditional | NO plaintext | 權限分窗 |
| 商家營業資料 | 社區產業 / 合作商家 / 本會專案 | C, Linux conditional, D conditional | NO plaintext | 權限分窗 |
| 管委會會議資訊 | 管委會 / 本會專案場景 | C, Linux conditional, D conditional | NO sensitive plaintext | 權限分窗 |
| Odoo/POS 明細 | 本會專案 / 場景系統 | C, Linux runtime, D conditional | NO plaintext | Gateway + audit |
| Secret / key / token | 憑證治理主體 | 專用安全儲存 | NO | L3 block unless formal credential flow |

## 會員資料治理語意

本會有保護資訊權限與責任，但系統不得因此將會員資料變成：

- AI 任意記憶
- 外部雲端明文
- 個人私用資料
- 無 audit 的查詢結果
- 可任意 replay 的 runtime packet

## Runtime Rule

所有涉及會員、商家營業、管委會資訊的操作，必須先轉為：

```text
TensorPacket
→ Authority Metric
→ Data Scope Metric
→ Gateway Decision
→ Audit Record
```

