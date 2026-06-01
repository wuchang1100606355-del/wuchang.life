# 開發期間無會員個資政策

版本：2026-05-11  
適用階段：開發期間  
正式會員資訊庫條款生效時點：系統正式交付營運後  

## 核心聲明

目前 Taiji Hub 處於開發期間。

開發期間：

- 無正式會員個資庫
- 無正式會員個資處理問題
- 無正式會員日常查詢功能
- 無正式會員資料上雲
- 無正式會員資料送外部 AI

目前測試資料定位為：

```text
本會幹部帳號功能測試資料
```

此類資料僅用於：

- 功能驗證
- 權限分窗測試
- Odoo / POS / Gateway 場景測試
- Runtime / Audit / Rollback 流程測試

## 正式營運後才生效之條款

以下條款屬於正式交付營運後才生效：

- 會員資訊資料庫物理封存
- D 磁碟會員資訊庫
- 會員個人設備遺失或變更之五維碼核對
- 中華民國公務機關依法定權限公文書命令開封
- 本人主張資料註銷或變更
- 會員資訊庫開封前後 SHA256
- 會員資訊庫重新物理封存

開發期間不得誤判為：

```text
系統已持有正式會員個資庫
```

## 開發期資料邊界

| 資料類型 | 開發期狀態 | 備註 |
|---|---|---|
| 本會幹部帳號測試資料 | 可用 | 功能測試用途 |
| 正式會員個資庫 | 不存在 / 未啟用 | 正式交付營運後才可建立 |
| 會員資訊物理封存庫 | 未生效 | 正式交付營運後生效 |
| Odoo / POS 測試資料 | 可用 | 不得混入正式會員個資 |
| 雲端無敏文件 | 可用 | 僅無敏、唯讀、全設備可用 |

## 開發期允許事項

允許：

- 使用本會幹部帳號測試功能
- 測試登入、權限、流程、Odoo/POS 草稿
- 測試 Gateway / Five Metric / Audit / Rollback
- 使用假資料或去識別化資料測試
- 建立正式營運後資料保護制度

## 開發期禁止事項

禁止：

- 將正式會員個資導入開發測試
- 將會員名冊作為測試資料
- 將幹部測試資料上傳外部 AI 明文分析
- 將測試帳號擴張為 production 權限
- 將開發期測試資料誤標為正式會員資料庫

## Runtime Window

開發期所有相關 TensorPacket 應標記：

```json
{
  "permission_window": "development",
  "formal_member_database_active": false,
  "test_subject_type": "association_cadre_account",
  "member_vault_policy_effective": false,
  "production_member_pii_processing": false
}
```

正式交付營運後，才可改為：

```json
{
  "permission_window": "production",
  "formal_member_database_active": true,
  "member_vault_policy_effective": true
}
```

## L3 Metric Hazard

以下一律封鎖：

- 開發期間導入正式會員名冊
- 將正式會員個資當作測試資料
- 將幹部測試帳號誤當 production 會員資料庫
- 未正式交付營運即啟用會員資訊封存庫
- 開發期將會員個資送外部 AI 或雲端明文

