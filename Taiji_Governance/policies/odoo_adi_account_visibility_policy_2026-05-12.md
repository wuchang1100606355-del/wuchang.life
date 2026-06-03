# Odoo ADI 帳務可見性與公益公開政策

版本：2026-05-12  
適用主體：新北市三重區五常社區發展協會  
系統：Odoo / ADI 度規資料庫法則 / Taiji Hub  

## 核心原則

本會 Odoo 會計帳務套用 ADI 度規資料庫法則。

帳務分為兩類可見性：

```text
一般會計帳務：權限可見、可稽核。
公益帳戶：上雲、公開、24H 可見。
```

公益帳戶公開方式進一步限定為：

```text
數據科目可見。
摘要可見。
明細不可見。
```

公開端可查核公益分類、總額、趨勢與基金池流向；不可見個人、商家、憑證、合約、單筆交易與敏感明細。

## 一般會計帳務

一般會計帳務包含：

- 社區產業收入
- POS/Odoo 營收明細
- 系統維運支出
- 勞務補償
- 智慧貢獻
- 商家營業資料
- 合約與供應商資訊
- 內部成本結構
- 未公開帳務憑證

可見性：

```text
權限可見
可稽核
不可任意公開
不可無敏雲端全公開
```

需要：

- Odoo 權限分窗
- 角色控制
- audit log
- SHA256 baseline
- 會計科目與專案分窗
- 必要時本人或會計審查

## 公益帳戶

公益帳戶用於展示本會公益目的、公益收入流向、社區服務與公共價值。

公益帳戶應：

```text
上雲
公開
24H 可見
可被居民與社會查核
```

但公開內容必須是：

- 無敏摘要
- 公益收入總額
- 公益支出分類
- 基金池留存
- 公益服務成果
- 社區向量資訊授權收入之公益回流摘要
- 去識別 ESG 指標
- 不含個資、不含營業機密、不含 secret

## 公益帳戶不得公開

以下不得放入 24H 公開公益帳戶：

- 會員明文個資
- 個別會員服務紀錄
- 商家營業機密
- 供應商未公開價格
- 未公開合約
- 管委會敏感會議資訊
- secret / token / key / service account JSON
- 個別 POS 交易可識別資料
- 可逆推出個人的行為向量

## ADI 帳務欄位

每筆帳務建議具有：

```json
{
  "account_visibility": "permissioned_auditable | public_24h",
  "adi_metric_tag": "public_interest | community_industry | system_operation | labor | intellectual_contribution | risk_reserve",
  "personal_data_included": false,
  "business_secret_included": false,
  "public_cloud_allowed": true,
  "audit_required": true,
  "sha256_required": true
}
```

## 可見性分級

| 帳務類型 | 可見性 | 雲端 | 說明 |
|---|---|---|---|
| 一般會計帳務 | 權限可見 | NO public | 可稽核但不公開 |
| 商家營業帳務 | 權限可見 | NO public | 保護營業機密 |
| 勞務/智慧貢獻 | 權限可見摘要 | CONDITIONAL | 可公開總額或政策，不公開個人敏感明細 |
| 公益收入摘要 | 公開 | YES | 24H 可見 |
| 公益支出摘要 | 公開 | YES | 24H 可見 |
| 基金池留存摘要 | 公開 | YES | 24H 可見 |
| 社區向量資訊授權收入摘要 | 公開摘要 | YES | 不公開買方敏感契約細節 |

## L3 Metric Hazard

以下一律封鎖：

- 將一般會計帳務全公開
- 公益帳戶公開會員明文
- 公益帳戶公開商家營業機密
- 公益帳戶公開 secret
- 私帳收取社區向量資訊授權收入
- AI 自動執行付款或轉帳
- 刪除帳務 audit / SHA256 / Odoo 記錄

## 最終原則

```text
一般帳務：權限可見，可稽核。
公益帳戶：上雲公開，24H 可見。
公開的是公益流向與無敏摘要，不是個資、機密或憑證。
Odoo 管帳，ADI 管責任，度規管公益方向。
```
