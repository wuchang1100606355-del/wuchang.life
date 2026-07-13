# 五常 Google 一鍵加入會員

本模組提供 Odoo 治理層的 Google OAuth 加入會員入口。

## 角色定位

- 層級：Odoo Governance Layer
- 入口：`/google/member/login`
- 回呼：`/google/member/callback`
- 會員資料：連結或建立 `res.partner`
- 安全邊界：不在程式碼保存 Google client secret

## Odoo Provider 與參數

重用 Odoo `auth_oauth.provider_google`，不得建立第二筆 Google Provider。Provider 需啟用並設定：

- `client_id`
- `auth_endpoint`
- `validation_endpoint`
- `scope`

授權碼交換所需的 secret 不寫入原始碼，僅由 Owner 核准後透過既有安全設定流程寫入：

- `wuchang_google_member_login.client_secret`

正式回呼網址由下列非 secret 參數決定：

- `wuchang_google_member_login.base_url`
- `wuchang_google_member_login.redirect_uri`

若未設定上述兩者，才使用 `web.base.url`，最後才使用當前 request host。正式環境不得使用 loopback URL。

Google Console 的 redirect URI 應對應：

```text
https://你的網域/google/member/callback
```

## 目前狀態

- addon 已可安裝。
- route 在選定 `postgres` DB session 後可進入。
- 若直接無 session 呼叫 public route 出現 404，需先進入：

```text
http://127.0.0.1:8069/web?db=postgres
```

再開：

```text
http://127.0.0.1:8069/google/member/login
```

## 會員連結規則

1. 優先用 Google `sub` 尋找既有 partner。
2. 找不到時用 email 尋找既有 partner。
3. 仍找不到時建立新的 `res.partner`。
4. 寫入：
   - `wuchang_google_sub`
   - `wuchang_google_email_verified`
   - `wuchang_member_join_source = google`

## 不可寫入

- Google client secret
- OAuth access token / refresh token
- 私鑰
- DB 密碼
- Tailscale auth key
