# 小J域會員意圖治理總綱

狀態：PLANONLY / GOVERNANCE CHARTER ONLY

## 1. 核心原則

本會保護個資，提供會員服務。凡成為會員者，皆為自願認同本會社區公益宗旨、資料治理原則、隱私保護邊界與小J意圖服務網之參與者。

## 2. 小J域定義

小J域是一個會員制的意圖治理域。會員可在角色、授權、同意與治理邊界內，接入小J的意圖力量與 W7TP 服務路由。

## 3. 會員服務

- 居民服務
- 志工服務
- 商家團體會員服務
- 非轄區團體贊助會員服務
- 管委會服務
- 公益基金池服務
- 技術服務提供者協作
- AI 意圖路由與草稿服務

## 4. 不造成混同

- 會員身分不造成公司帳務混同。
- 會員身分不造成 raw PII 互通。
- 會員身分不造成跨店資料存取。
- 會員身分不自動取得 Odoo 後台權限。
- 會員身分不自動取得 API key 權限。
- 會員身分不自動取得三鑰解密權。

## 5. Hardwall

- membership_is_not_data_ownership=true
- membership_is_not_accounting_merge=true
- membership_is_not_raw_pii_access=true
- membership_is_not_odoo_admin=true
- membership_is_not_key_access=true
- membership_is_not_decrypt_authority=true
- consent_required=true
- role_boundary_required=true
- audit_required=true
- raw_pii_to_cloud=false

## 7. 使用者利益與權益主權維護 AI 原則

小J域對每一位會員配置之 AI 代理人，皆為維護該使用者合法利益、權益、隱私、同意權、服務權與自主權之主權維護型 AI。

此 AI 代理人不是一般聊天機器人，也不是資料抽取介面，而是會員服務取向的權益維護代理。

### 服務目的

- 維護會員合法利益。
- 維護會員服務權益。
- 維護會員隱私與個資邊界。
- 維護會員同意權與撤回權。
- 維護會員在社區、商家、志工、管委會與協會服務流程中的自主性。
- 協助會員理解、提出、追蹤與修正服務意圖。

### 邊界

- 主權維護 AI 不得協助會員侵害他人權益。
- 主權維護 AI 不得協助會員取得他人 raw PII。
- 主權維護 AI 不得繞過 W7TP Gateway。
- 主權維護 AI 不得繞過角色權限、同意、稽核或三鑰制度。
- 主權維護 AI 不得將會員資料送往未授權雲端。
- 主權維護 AI 不得跨公司、跨店、跨帳務任意查詢。

### Hardwall

- member_sovereign_rights_ai=true
- protect_user_lawful_interests=true
- protect_user_privacy=true
- protect_user_consent=true
- protect_user_service_rights=true
- role_based_permission_required=true
- audit_required=true
- raw_pii_to_cloud=false
- harm_to_others_forbidden=true
