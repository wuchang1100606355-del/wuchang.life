# W7TP-009 上品食品行 Google Workspace 開發帳號補丁

狀態：PLANONLY / DESIGN PATCH ONLY

## Google Workspace / 技術服務帳號

- google_account=o970106@gmail.com
- account_role=Google Workspace / Odoo 技術服務識別帳號
- provider_entity=上品食品行
- provider_role=外部友軍贊助公司 + Odoo / Google Workspace 開發商

## Hardwall

- 不保存 Google 密碼。
- 不保存 OAuth token。
- 不保存 API key。
- 不保存 recovery code。
- 不把 credential 寫入 prompt、logs、memory、Git、DLQ raw payload。
- 技術服務帳號不等於 raw PII 解密權。
- 技術服務帳號不等於協會資料所有權。
- 技術服務帳號不得繞過 W7TP Gateway。

## Boundary

- account_identifier_allowed=true
- credential_storage_allowed=false
- token_storage_allowed=false
- raw_pii_access=false
- single_admin_decrypt_allowed=false
- plan_only=true
