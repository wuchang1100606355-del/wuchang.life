# 主權 AI 會員系統：部署前本地完成手冊

## 完成邊界

本階段完成產品程式、管理介面、設定工具、操作說明與本地驗證，不執行公開部署、DNS、反向代理、憑證、路由器、重啟或 live DB write。Client ID、Secret 與 public HTTPS origin 是部署輸入，不是未完成的產品程式。

## 端到端產品鏈

```text
Google／8D 身分
→ 會員登入
→ 會員註冊
→ 主權 AI 會員入口
→ 小J意圖處理
→ 去識別化雲端候選
→ 本地總場 ALLOW／HOLD／BLOCK 裁決
→ HOLD／人工確認介面
→ evidence seal 與操作員證據紀錄
```

- Google callback 只連結或建立本地會員，並保留既有 group packet return。
- 小J先建立本地 intent、authority packet、candidate action 與 evidence seal。
- 雲端封包只包含 refs、intent code、schema 與去識別化技術上下文；cloud role 固定為 candidate only。
- 本地總場接受 canonical verifier 結果，正式決策只允許 `ALLOW`、`HOLD`、`BLOCK`。
- 付款、會員明文、角色授予與正式寫入保留 HOLD 或人工確認。

## Provider 設定工具

```bash
python3 tools/odoo/configure_google_member_provider.py --plan
python3 tools/odoo/configure_google_member_provider.py --check
```

工具預設唯讀。它會在指定 Odoo 容器內，使用既有 entrypoint 連線環境唯讀識別唯一 Odoo DB，再透過 Odoo shell stdin 讀取 Provider 狀態。它不建立本機 PostgreSQL socket 連線、不呼叫 `psql`、不建立 `/tmp` 腳本，也不輸出 Client ID、Secret、token、cookie 或 session。

Apply 模式只供已核准操作員使用：

```bash
python3 tools/odoo/configure_google_member_provider.py \
  --apply \
  --confirm APPLY_EXISTING_GOOGLE_PROVIDER \
  --public-base-url https://你的正式會員網域
```

執行環境必須先提供 `WUCHANG_GOOGLE_CLIENT_ID` 與 `WUCHANG_GOOGLE_CLIENT_SECRET`。工具只更新既有 `auth_oauth.provider_google`；若該 Provider 不存在，立即 HOLD，不自動建立第二筆。

## 管理員介面

系統管理員由 **主權 AI 會員系統 → Google 登入健康狀態** 查看：

- Provider 是否存在與啟用
- Client ID 是否存在
- Secret 是否存在
- Callback URI 與狀態
- Public base URL 與狀態
- 登入健康狀態

狀態頁不提供 secret 欄位，也不顯示 credential 原文。

## 會員頁、錯誤與 HOLD

會員入口提供登入、註冊、LINE、Google 與流程說明。Google callback 錯誤頁只顯示人類可理解的說明與參考代碼。小J與本地總場在風險、設定不完整或需人工權限時回傳 HOLD，不把候選結果描述成已執行。

## 本地驗證

```bash
python3 -m py_compile \
  tools/odoo/configure_google_member_provider.py \
  scripts/verify/verify_sovereign_ai_member_local_completion.py
python3 scripts/verify/verify_sovereign_ai_member_local_completion.py
python3 tools/odoo/configure_google_member_provider.py --plan
python3 tools/odoo/configure_google_member_provider.py --check
PYTHONPATH=/usr/lib/python3/dist-packages .venv-health/bin/python -m pytest -q \
  tests/test_google_member_provider_configuration.py \
  tests/test_sovereign_ai_member_end_to_end_local_flow.py
```

`--check` 是 live DB read-only 狀態查詢；其餘驗證均為 source-only 或 synthetic local flow。部署前仍須由 Owner 提供正式 OAuth 與 public origin 設定，並另行核准 module update 與限定服務操作。
