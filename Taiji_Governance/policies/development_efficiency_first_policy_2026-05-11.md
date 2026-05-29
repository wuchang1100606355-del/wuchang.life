# 開發期一般系統開發準則與效率優先政策

版本：2026-05-11  
適用階段：開發期、測試期、封裝期  
正式營運期：需另依正式資料治理、會員資訊庫、Odoo/POS production 與法定責任邊界執行  

## 核心聲明

本系統建置期間，應依一般系統開發準則推進。

目前開發期無正式會員個資庫，僅使用本會幹部帳號與功能測試資料進行開發，因此現階段不應以尚未啟用之正式會員個資治理條款阻礙工程效率。

開發期原則：

```text
效率掛帥
功能落地
本地優先
可測試
可回滾
可封裝
可部署
```

## 適用範圍

開發期可優先推進：

- Runtime artifact
- Gateway
- Five Metric Validator
- POS / Odoo 草稿流程
- schema / tests
- local deployment package
- Linux 子系統遷移
- C 磁碟場景資料夾規劃
- 組織雲端無敏唯讀 staging
- D 磁碟正式營運後會員資訊庫規劃

## 開發期資料狀態

| 項目 | 狀態 |
|---|---|
| 正式會員個資庫 | 未啟用 |
| 正式會員個資處理 | 未啟用 |
| 會員資訊物理封存 | 正式交付營運後才生效 |
| 測試帳號 | 本會幹部帳號功能測試 |
| 雲端資料 | 無敏唯讀 staging |
| production mutation | 未開放自然語言直達 |

## 效率優先但不廢除的底線

效率優先不代表下列行為可被允許：

- 輸出 secret / token / private key / service account JSON
- 將正式會員名冊導入開發測試
- 將商家營業機密直接上雲
- 將管委會敏感資訊未去敏上雲
- 以自然語言直接改 production Odoo/POS
- 刪除 audit / rollback / SHA256 baseline
- 繞過 Gateway / Five Metric Gate

## 開發期判斷規則

若操作符合以下條件，原則上可快速推進：

```text
不含 secret
不含正式會員個資
不改 production
可回滾
可測試
可 audit
不直接外送雲端 AI 明文
```

風險等級：

| 條件 | 等級 | 處置 |
|---|---|---|
| 本地文件 / schema / test / artifact | L0/L1 | allow / allow_with_audit |
| 本地 runtime localhost | L1 | allow_with_audit |
| Docker/systemd 啟動 | L2 | 需人工確認 |
| production Odoo/POS 修改 | L3 | block until formal approval |
| secret / 正式會員個資外送 | L3 | block |

## 正式營運切換

當系統正式交付營運後，以下治理條款才正式生效：

- 會員資訊庫 D 磁碟物理封存
- 會員設備遺失/變更五維碼核對
- 公務機關正式公文書命令開封
- 本人主張資料註銷或變更
- 正式會員資料最小必要處理

正式營運切換前，需建立：

- production readiness checklist
- Odoo/POS data boundary
- member vault activation record
- audit baseline
- rollback plan
- human approval record

## 最終原則

```text
開發期依一般系統開發準則，效率掛帥。
目前無正式會員個資庫，不以尚未啟用條款阻礙工程。
但 secret、production mutation、外部 AI 明文、正式會員資料外送仍為底線。
正式交付營運後，再啟用完整會員資訊庫與法定資料治理條款。
```

