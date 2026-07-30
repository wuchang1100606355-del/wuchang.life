# 五常 Google 一鍵加入會員

本模組提供 Odoo 治理層的 Google OAuth 加入會員入口。

## 角色定位

- 層級：Odoo Governance Layer
- 入口：`/google/member/login`
- 回呼：`/google/member/callback`
- 會員資料：只解析既有本地會員綁定與不可反查引用，不自動建立或合併會員
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

## 正式設定工具

工具位於 `tools/odoo/configure_google_member_provider.py`。預設 check 只讀取狀態；它會在 Odoo 容器內沿用官方 entrypoint 的既有資料庫連線設定，以 stdin 執行 Odoo shell，不使用本機 PostgreSQL socket、`psql` 或暫存檔。

```bash
python3 tools/odoo/configure_google_member_provider.py --plan
python3 tools/odoo/configure_google_member_provider.py --check
```

Apply 僅更新既有 `auth_oauth.provider_google`，不會建立重複 Provider。它需要明確確認字串、公開 HTTPS base URL，以及由執行環境提供的 `WUCHANG_GOOGLE_CLIENT_ID`、`WUCHANG_GOOGLE_CLIENT_SECRET`；工具只輸出 `PRESENT`、`MISSING`、`INVALID_REF`、`INACTIVE` 與健康狀態，不輸出 credential 原文。

管理員可由 **主權 AI 會員系統 → Google 登入健康狀態** 查看 Provider、Client ID、Secret、Callback URI、Public base URL 與登入健康狀態。該頁為唯讀狀態介面。

Google Console 的 redirect URI 應對應：

```text
https://member.wuchang.life/google/member/callback
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

1. Google `sub` 先雜湊為 provider subject reference，再交由既有本地會員權威解析。
2. Email 只能形成不可反查的候選訊號，不得自動合併相同 Email 的帳號。
3. 找不到既有綁定時維持待確認，不自動建立 `res.partner` 或授予會員角色。
4. 只有既有本地綁定、身分前綴與 verifier 均通過時，才產生五分鐘內有效的 ref-only 身分投影。

## 不可寫入

- Google client secret
- OAuth access token / refresh token
- 私鑰
- DB 密碼
- Tailscale auth key
