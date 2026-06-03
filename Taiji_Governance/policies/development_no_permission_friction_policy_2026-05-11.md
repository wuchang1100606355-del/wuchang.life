# 開發期無權限干擾高效開發政策

版本：2026-05-11  
適用階段：開發期  
目的：避免正式會員資料權限流程干擾系統開發效率  

## 核心原則

開發期間，系統開發不得依賴真實會員資料庫。

即使未來存在會員資料庫，開發流程也應維持：

```text
schema-first
mock-first
adapter-first
redacted-fixture-first
no-production-pii-dependency
```

目的：

```text
本人開發時不被會員資料權限流程干擾。
系統功能可高效開發、測試、封裝、部署。
真實會員資料不成為開發依賴。
```

## 權限不干擾開發的意思

「無權限干擾」不是解除資訊保護，而是讓開發不需要碰受保護資料也能推進。

正確模式：

```text
開發者 / 小J / Codex
→ 使用 schema / mock / adapter / redacted fixture
→ 完成功能、測試、部署 artifact
→ 正式營運前再接 production data gateway
```

錯誤模式：

```text
為了方便開發
→ 直接讀會員明文
→ 直接把會員資料放進測試
→ 直接送外部 AI
```

## 若開發期間看見會員資料庫

若開發期間出現會員資料庫或類似會員資料檔案，系統應：

1. 不讀取內容。
2. 不輸出內容。
3. 不送外部 AI。
4. 只記錄檔案存在與路徑 hash。
5. 標記為 `protected_member_data_present`.
6. 改用 schema/mock 繼續開發。

此情境不應中斷整體開發，但該資料本身不得成為開發輸入。

## 開發期快速路徑

以下操作可快速推進：

| 項目 | 是否允許 |
|---|---|
| schema 設計 | YES |
| validator | YES |
| fake member fixture | YES |
| redacted sample | YES |
| Odoo import dry-run | YES |
| POS draft flow | YES |
| production member write | NO |
| real member plaintext AI processing | NO |

## Runtime 標記

開發期 packet 應標記：

```json
{
  "permission_window": "development",
  "developer_permission_friction": "minimized",
  "production_member_pii_required": false,
  "uses_mock_or_redacted_data": true,
  "real_member_database_access": false,
  "member_vault_policy_effective": false
}
```

若偵測到真實會員資料庫存在：

```json
{
  "protected_member_data_present": true,
  "real_member_database_access": false,
  "development_continues_with_mock": true,
  "risk_level": "L2_drift"
}
```

## L3 Metric Hazard

以下一律封鎖：

- 以開發效率為由讀取真實會員明文
- 將真實會員資料送外部 AI
- 將真實會員資料放入測試 fixture
- 將 D 磁碟會員庫當作開發資料庫
- 將 production Odoo 會員資料作為測試來源
- 刪除真實會員資料出現的 audit 記錄

## 最終原則

```text
高效開發靠 mock、schema、adapter，不靠真實會員明文。
權限流程不應卡住開發，但真實會員資料也不應成為開發依賴。
小J可以幫助把系統做快、做準、做可部署，但不能拿會員明文換效率。
```

