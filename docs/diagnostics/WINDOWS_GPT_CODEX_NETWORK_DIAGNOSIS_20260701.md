# Windows GPT/Codex 網路環境診斷紀錄

日期：2026-07-01  
範圍：本機 Windows GPT/ChatGPT/Codex 無法正常運行之網路與工具鏈診斷  
註記：使用者文字中的 `gtp` 於本紀錄按 GPT/ChatGPT/Codex 問題處理。

## 一、目前已觀測事實

### 1. Windows 端實測證據狀態

截至本紀錄產生時，Linux/雲端節點尚未捕捉到 Windows 端同步回來的 readiness 或 network diagnostic 報告。

收集器結果：

```text
STATE=HOLD_WINDOWS_GPT_CODEX_REPAIR_NOT_VERIFIED
reason=readiness_report_missing
readiness_found=False
completion_ready=False
```

此狀態僅表示「Windows 端證據未捕捉」，不能直接判定 Windows 網路一定失敗。

### 2. Linux/雲端節點對照結果

同一時間，Linux/雲端節點對 OpenAI 相關端點的低階網路觀測如下：

| 端點 | DNS | TCP 443 | TLS | HTTP 結果 |
| --- | --- | --- | --- | --- |
| `api.openai.com` | 可解析 | OK | TLSv1.3 OK | `/v1/models` 回 `401` |
| `chatgpt.com` | 可解析 | OK | TLSv1.3 OK | 回 Cloudflare challenge `403` |
| `auth.openai.com` | 可解析 | OK | TLSv1.3 OK | 回 Cloudflare challenge `403` |
| `cdn.oaistatic.com` | 可解析 | 未列入 TCP 表 | 未列入 TLS 表 | 根路徑回 `404` |
| `files.oaiusercontent.com` | 可解析 | 未列入 TCP 表 | 未列入 TLS 表 | 未測 HTTP |

技術解讀：

1. `api.openai.com/v1/models` 回 `401` 代表 API 網路路徑、DNS、TCP 443 與 TLS 皆可達；失敗點不是基礎網路，而是需要 Bearer 認證。
2. `chatgpt.com` 與 `auth.openai.com` 對 headless curl 回 Cloudflare challenge `403`，代表非瀏覽器自動請求被挑戰；這不等同於一般 Windows 瀏覽器一定失敗。
3. `cdn.oaistatic.com` 根路徑回 `404` 可視為 CDN 連線存在，但根 URL 非應用資源路徑。
4. Linux/雲端節點未設定 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 或 `NO_PROXY` 環境變數。
5. 本 Linux 節點缺少 `node`，導致 Codex 官方手冊 helper 無法在本節點執行；此為 Linux 工具鏈事實，不能外推為 Windows 問題。

## 二、目前最可能的 Windows 問題分類

在 Windows 端報告尚未回傳前，不能下最終結論。依現有工具設計與 Linux 對照，Windows 本機 GPT/Codex 無法正常運行通常落在下列技術類別：

1. `DNS_FAILURE`：Windows DNS 無法解析 `api.openai.com`、`chatgpt.com` 或 `auth.openai.com`。
2. `TCP_443_FAILURE`：公司網路、防火牆、VPN 或安全軟體阻擋 443 連線。
3. `TLS_HANDSHAKE_FAILURE`：憑證攔截、企業代理、時間錯誤或 TLS 檢查造成握手失敗。
4. `CHATGPT_WEB_CHALLENGE`：瀏覽器或自動化請求被 Cloudflare challenge 擋下，尤其是非互動式 headless 請求。
5. `PROXY_CONFIGURATION_PRESENT`：Windows、npm、PowerShell 或環境變數存在代理設定，導致 Codex/API 路徑與瀏覽器路徑不一致。
6. `OPENAI_API_KEY_NOT_VISIBLE`：Codex CLI/API 模式需要 `OPENAI_API_KEY`，但目前 Windows shell 看不到該變數。
7. `CODEX_CLI_NOT_IN_PATH`：Codex 已安裝但不在 Windows 使用者 PATH，或根本未安裝。
8. `NODE_MISSING`：若 Codex 安裝/更新依賴 npm 或 node，Windows 端缺 Node.js 會導致安裝鏈失敗。

## 三、Windows 端應執行的封緘診斷入口

從同步套件根目錄在 Windows 執行：

```bat
scripts\diagnostics\run_windows_gpt_codex_repair.cmd -RepairUserPath
```

預期會在套件內同步出：

```text
evidence_from_windows\
```

其中應包含：

```text
WINDOWS_OPENAI_NETWORK_DIAGNOSTIC_REPORT.json
WINDOWS_GPT_CODEX_REPAIR_REPORT.json
WINDOWS_GPT_CODEX_TRIAGE_SUMMARY.json
WINDOWS_GPT_CODEX_READINESS_REPORT.json
READINESS_EVIDENCE_SEAL.txt
```

回到 Linux/雲端節點後執行：

```bash
python3 scripts/diagnostics/collect_windows_gpt_codex_results.py /mnt/taiji_cloud_drive/WINDOWS_GPT_CODEX_REPAIR_PACKAGE_20260701
```

若輸出為：

```text
STATE=PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED
```

才表示 Windows 端 GPT/Codex 修復與網路 readiness 已被本地封緘證據驗證。

## 四、目前結論

目前不能把 Windows 本機 GPT/Codex 無法正常運行歸因於單一網路原因，因為 Windows 端實測報告尚未捕捉。

已能確認的是：Linux/雲端節點對 OpenAI API 端點的 DNS、TCP 443 與 TLS 是可達的，API 回 `401` 屬於認證需求；ChatGPT/auth 對 headless curl 回 `403` 屬於 challenge 對照訊號。若 Windows 端仍失敗，優先檢查 Windows 本機 DNS、443/TLS、代理/VPN、防火牆、瀏覽器 challenge、`OPENAI_API_KEY` 可見性、Codex CLI PATH 與 Node.js 工具鏈。
