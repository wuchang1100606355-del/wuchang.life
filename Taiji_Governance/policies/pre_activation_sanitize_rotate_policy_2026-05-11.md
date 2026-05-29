# 正式啟用前清洗與輪替政策

版本：2026-05-11  
適用階段：開發期 → 正式啟用前 cutover  

## 核心規則

開發期間出現或使用過的金鑰、測試帳號、可能個資、類個資、測試資料與權限設定，在正式啟用前必須清洗、更換、輪替或作廢。

此規則使開發期可高效推進，但 production 啟用前必須通過清洗與輪替硬閘。

## 必須清洗或輪替的項目

| 項目 | 正式啟用前處置 |
|---|---|
| API key | revoke / rotate |
| OAuth token | revoke / rotate |
| service account key | revoke / rotate |
| private key | rotate |
| password | rotate |
| test admin account | disable / downgrade / replace |
| test member-like data | delete / anonymize |
| test POS data | reset / archive as test-only |
| test Odoo data | reset / rebuild / migrate only approved baseline |
| browser session cookie | invalidate |
| webhook secret | rotate |
| tunnel token | rotate |
| Tailscale auth key | rotate if used in dev |

## 可能個資或類個資

以下資料即使在開發期被視為測試，也必須在正式啟用前清洗：

- 幹部測試帳號個人資訊
- 類會員資料
- 假資料中混入的真實電話、Email、地址
- POS 測試訂單中的真實姓名或聯絡方式
- Odoo 測試 partner/customer 中的真實資訊
- Chat / voice / browser 測試中殘留的識別資訊

## Cutover Gate

正式啟用前必須完成：

```text
secret inventory
credential rotation
test data purge
production env rebuild
audit baseline
SHA256 baseline
rollback plan
owner approval
```

## Runtime Cutover Packet

正式啟用前應產生：

```json
{
  "event": "pre_activation_sanitize_rotate",
  "permission_window": "deployment_preparation",
  "keys_rotated": true,
  "tokens_revoked": true,
  "test_accounts_reviewed": true,
  "test_data_purged_or_anonymized": true,
  "production_env_rebuilt": true,
  "sha256_baseline_created": true,
  "rollback_plan_created": true,
  "owner_approved": true
}
```

## 開發期效率與正式啟用責任

開發期：

```text
效率優先
mock / schema / adapter
測試資料可用
```

正式啟用前：

```text
全部清洗
全部輪替
全部重新基準化
```

## L3 Metric Hazard

以下一律封鎖：

- 使用開發期金鑰進入 production
- 使用開發期 OAuth token 進入 production
- 使用開發期 service account key 進入 production
- 未清洗測試資料即啟用正式服務
- 將測試帳號保留為正式高權限帳號
- 未建立 SHA256 baseline 即 production cutover
- 未建立 rollback plan 即 production cutover

## 最終原則

```text
開發期間可以高效。
正式啟用前必須清洗。
開發金鑰不可進 production。
測試資料不可成正式資料。
啟用必須有 audit、SHA256、rollback、owner approval。
```

