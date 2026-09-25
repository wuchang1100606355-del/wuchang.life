# Windows GPT / Codex 網路診斷與修復入口

日期：2026-07-01
範圍：本機 Windows（微軟作業系統）上 GPT（大型語言模型）、ChatGPT（聊天式大型語言模型產品）或 Codex（程式代理）無法正常運行之技術診斷。

本文件只描述技術可觀測事實與候選修復路徑，不作設備所有權、使用者授權或法律判斷。

## 一、單一入口

若使用雲端修復套件，優先在 package 根目錄雙擊：

```cmd
00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd
```

這個檔名刻意以 `00_` 開頭，方便在 Windows 檔案總管排序時直接出現在最前面。它會呼叫下列一鍵修復入口：

```cmd
RUN_WINDOWS_ONE_CLICK_REPAIR.cmd
```

這個入口會自動建立新的 `evidence_from_windows_current` 判讀批次，執行 Windows GPT/Codex 修復、readiness gate、證據同步，最後呼叫 `00_SHOW_WINDOWS_EVIDENCE_STATUS.cmd` 顯示 readiness/repair/launch 報告是否存在，並保留視窗供讀取最後狀態。若只要只讀診斷、不修改目前使用者 PATH，改用：

```cmd
00_DOUBLE_CLICK_DIAGNOSE_WINDOWS_GPT_CODEX.cmd
```

或：

```cmd
RUN_WINDOWS_ONE_CLICK_DIAGNOSE.cmd
```

在 Windows 的 Taiji_Hub 專案根目錄執行：

```cmd
scripts\diagnostics\run_windows_gpt_codex_repair.cmd
```

若使用雲端修復套件，可在 package 根目錄直接執行：

```cmd
RUN_WINDOWS_DIAGNOSE.cmd
```

若要重設本次 Windows 修復判讀批次，先在 package 根目錄執行：

```cmd
START_FRESH_WINDOWS_BATCH.cmd
```

此動作會把既有 `evidence_from_windows_current` 搬到 `evidence_from_windows_archive`，再建立新的 `evidence_from_windows_current`。它不刪除舊證據，只是讓後續 Linux/雲端收集器預設只看新的 current 批次。

雙擊保留視窗版本：

```cmd
START_FRESH_WINDOWS_BATCH_KEEP_OPEN.cmd
```

若以滑鼠雙擊執行並希望視窗保留，可使用：

```cmd
RUN_WINDOWS_DIAGNOSE_KEEP_OPEN.cmd
```

這個入口會執行完整流程：診斷、產生安全候選包裝器、尋找最新報告、能使用 Python 時自動做二次判讀、執行 post-repair readiness gate，最後產生 launcher seal。若從本 package 執行 `.cmd`，還會把 `%USERPROFILE%\Taiji_Hub\evidence` 同步回 package 旁的 `evidence_from_windows_current`。

或用 PowerShell（Windows 命令殼）直接執行完整流程：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnostics\run_windows_gpt_codex_full_repair.ps1 -OutputRoot "$env:USERPROFILE\Taiji_Hub\evidence"
```

若只要執行底層診斷腳本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnostics\windows_gpt_codex_repair.ps1 -OutputRoot "$env:USERPROFILE\Taiji_Hub\evidence" -ApplySafeFixes
```

若報告顯示 Codex 可執行檔存在但不在 PATH，可明確啟用目前使用者 PATH 修復：

```cmd
scripts\diagnostics\run_windows_gpt_codex_repair.cmd -RepairUserPath
```

或在 package 根目錄執行：

```cmd
RUN_WINDOWS_REPAIR_USER_PATH.cmd
```

雙擊保留視窗版本：

```cmd
RUN_WINDOWS_REPAIR_USER_PATH_KEEP_OPEN.cmd
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnostics\run_windows_gpt_codex_full_repair.ps1 -OutputRoot "$env:USERPROFILE\Taiji_Hub\evidence" -RepairUserPath
```

`-RepairUserPath` 只會在找到 Codex 候選可執行檔且 `codex` 不在 PATH 時，將該候選檔所在目錄加入目前 Windows 使用者 PATH。既有已開啟的 terminal 需要重開才會讀到新的使用者 PATH。

診斷報告會同時保留 `commands`（修復前命令快照）與 `post_repair_commands`（修復邏輯後命令快照）。因此若 `RUN_WINDOWS_REPAIR_USER_PATH.cmd` 成功讓目前流程看見 `codex`，二次判讀會標示 `CODEX_USER_PATH_UPDATED_AND_VISIBLE` 或 `CODEX_BECAME_VISIBLE_AFTER_REPAIR`；若 PATH 已更新但目前流程仍看不到 `codex`，則標示 `CODEX_USER_PATH_UPDATED_BUT_NOT_VISIBLE`。

不需要先手動改環境。此入口會呼叫既有的 OpenAI（人工智慧公司）網路診斷腳本，並補充 Codex CLI（命令列工具）、Node.js、npm、環境變數、代理設定與 ChatGPT 乾淨瀏覽器測試包裝器。

## 二、輸出位置

預設輸出資料夾格式：

```text
%USERPROFILE%\Taiji_Hub\evidence\windows_gpt_codex_repair_<timestamp>\
```

主要輸出：

| 檔案 | 用途 |
| --- | --- |
| `WINDOWS_GPT_CODEX_REPAIR_REPORT.json` | 完整診斷資料 |
| `WINDOWS_GPT_CODEX_REPAIR_SUMMARY.txt` | 可讀摘要 |
| `EVIDENCE_SEAL.txt` | 報告與摘要之 SHA256（雜湊校驗值）封緘 |
| `CANDIDATE_REPAIR_COMMANDS.txt` | 候選修復指令 |
| `launch_codex_clean_network_env.ps1` | 移除目前行程代理環境變數後啟動 Codex 的候選包裝器 |
| `launch_chatgpt_edge_clean_profile.ps1` | 使用乾淨 Edge（微軟瀏覽器）設定檔測試 ChatGPT 的候選包裝器 |
| `FULL_REPAIR_LAUNCH_REPORT.json` | 完整啟動器執行紀錄，位於 `windows_gpt_codex_full_repair_launcher_<timestamp>` |
| `FULL_REPAIR_EVIDENCE_SEAL.txt` | 完整啟動器封緘 |
| `WINDOWS_GPT_CODEX_READINESS_REPORT.json` | 修復後 readiness gate，位於 `windows_gpt_codex_readiness_<timestamp>` |
| `READINESS_EVIDENCE_SEAL.txt` | readiness gate 封緘 |

## 三、二次判讀

Windows 端產生 `WINDOWS_GPT_CODEX_REPAIR_REPORT.json` 後，可用下列指令產生更短的 root-cause 判讀摘要：

```powershell
python .\scripts\diagnostics\triage_windows_gpt_codex_report.py "<report-folder>\WINDOWS_GPT_CODEX_REPAIR_REPORT.json"
```

會輸出：

| 檔案 | 用途 |
| --- | --- |
| `WINDOWS_GPT_CODEX_TRIAGE_SUMMARY.json` | 分類後的斷點與修復候選 |
| `WINDOWS_GPT_CODEX_TRIAGE_SUMMARY.txt` | 人可讀判讀摘要 |
| `TRIAGE_EVIDENCE_SEAL.txt` | 二次判讀封緘 |

## 四、結果回收與完成判定

Windows 端跑完完整入口後，可在 Linux（類 Unix 作業系統）或雲端同步目錄中掃描實際 evidence，驗證 readiness seal，並判定是否達到可宣告修復完成。

預設 Windows evidence 位置是：

```text
%USERPROFILE%\Taiji_Hub\evidence
```

若從 package 內的 `.cmd` 執行，結果會同步到：

```text
<package_root>\evidence_from_windows_current
```

此時可直接掃描 package 根目錄：

```bash
python3 scripts/diagnostics/collect_windows_gpt_codex_results.py /mnt/taiji_cloud_drive/WINDOWS_GPT_CODEX_REPAIR_PACKAGE_20260701
```

若人在 package 根目錄，可使用避免 Python 快取污染的根入口：

```bash
bash ./00_CHECK_CURRENT_STATUS.sh
```

或使用原始收集入口：

```bash
bash ./COLLECT_WINDOWS_RESULTS.sh
```

根入口預設只掃描 `evidence_from_windows_current`；如果該資料夾尚未建立，才退回掃描整個 package 根目錄。

結果回收器也支援同時掃描多個根目錄，例如 package 目錄加另行同步的 evidence 目錄：

```bash
python3 scripts/diagnostics/collect_windows_gpt_codex_results.py \
  /mnt/taiji_cloud_drive/WINDOWS_GPT_CODEX_REPAIR_PACKAGE_20260701 \
  /mnt/taiji_cloud_drive/WINDOWS_GPT_CODEX_EVIDENCE_FROM_WINDOWS
```

完成條件：

1. 找到 `WINDOWS_GPT_CODEX_READINESS_REPORT.json`。
2. `READINESS_EVIDENCE_SEAL.txt` 中的 SHA256（雜湊校驗值）驗證通過。
3. readiness 狀態為 `PASS_WINDOWS_GPT_CODEX_READINESS`。
4. `codex` 可被找到，且 `codex --version` 成功。
5. `api.openai.com/v1/models` 回 `200` 或 `401`，表示 API（應用程式介面）網路路徑可達。

若上述條件成立，結果回收器輸出 `PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED`；否則輸出 `HOLD_WINDOWS_GPT_CODEX_REPAIR_NOT_VERIFIED`。

回收器輸出的 JSON/TXT 也包含 `next_action` 欄位。當 readiness 證據缺失或未完成時，該欄位會列出 Windows 端應執行的 `RUN_WINDOWS_ONE_CLICK_REPAIR_KEEP_OPEN.cmd`；若只要只讀診斷，則列出 `RUN_WINDOWS_ONE_CLICK_DIAGNOSE_KEEP_OPEN.cmd` 作為替代入口。

若 Windows 端尚未同步完成，可用等待器持續輪詢 package 根目錄，直到收到可驗證 readiness 證據或逾時：

```bash
python3 scripts/diagnostics/wait_for_windows_gpt_codex_results.py \
  /mnt/taiji_cloud_drive/WINDOWS_GPT_CODEX_REPAIR_PACKAGE_20260701 \
  --timeout-sec 1800 \
  --interval-sec 10
```

等待器會輸出：

| 檔案 | 用途 |
| --- | --- |
| `WINDOWS_GPT_CODEX_WAIT_REPORT.json` | 等待期間最後一次收集狀態 |
| `WINDOWS_GPT_CODEX_WAIT_REPORT.txt` | 人可讀等待摘要 |
| `WINDOWS_GPT_CODEX_WAIT_REPORT_SEAL.txt` | 等待報告與最後一次收集報告之 SHA256 封緘 |
| `latest_collection/WINDOWS_GPT_CODEX_RESULT_COLLECTION.json` | 最後一次回收判定 |

若等待器輸出 `PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED`，表示 Windows 端 readiness 證據已被收集器與 seal 驗證；若輸出 `HOLD_WINDOWS_GPT_CODEX_REPAIR_WAIT_TIMEOUT`，表示逾時前仍未捕捉到足以完成的 Windows 端證據。

若使用 package 根目錄入口，在 Linux（類 Unix 作業系統）或雲端節點可直接執行：

```bash
bash ./WAIT_FOR_WINDOWS_RESULTS.sh 1800 10
```

等待入口同樣預設只等待 `evidence_from_windows_current` 中的新批次結果；若尚未建立 current 批次，才退回等待 package 根目錄。

完整啟動器 `FULL_REPAIR_LAUNCH_REPORT.json` 會彙整實際狀態，包括：

| 欄位 | 用途 |
| --- | --- |
| `side_effects.actual_changes_user_path` | 本輪是否實際更新目前 Windows 使用者 PATH |
| `repair_state.codex_initial_present` | 修復前 `codex` 是否可見 |
| `repair_state.codex_post_repair_present` | 修復邏輯後 `codex` 是否可見 |
| `repair_state.codex_post_repair_version_ok` | 修復邏輯後 `codex --version` 是否成功 |
| `readiness_state.state` | readiness gate 狀態 |
| `readiness_state.openai_api_status` | OpenAI API HEAD 狀態碼，`200` 或 `401` 代表 API 網路路徑可達 |

回收器會把上述 launcher 摘要納入 `WINDOWS_GPT_CODEX_RESULT_COLLECTION.json` 的 `launch` 欄位，並把 repair 摘要納入 `repair` 欄位。

Windows launcher 會以 readiness 結果回傳 exit code：只有達到 `PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED` 時 exit code 為 `0`；若仍是 `HOLD_WINDOWS_GPT_CODEX_REPAIR_NOT_VERIFIED`，exit code 為 `1`，但報告與 evidence 仍會照常輸出。

## 五、判讀矩陣

| 觀測結果 | 技術含義 | 下一步 |
| --- | --- | --- |
| `api.openai.com` 回 `401` | API（應用程式介面）網路路徑可達，缺認證或憑證未被程式讀到 | 檢查 `OPENAI_API_KEY` 是否存在，但不得輸出 key 內容 |
| `api.openai.com` DNS 失敗 | DNS（網域解析）層斷裂 | 比對 Windows DNS、VPN、路由器 DNS、公司/校園網路政策 |
| DNS 成功但 TCP 443 失敗 | 443 連線被阻斷或路由異常 | 檢查防火牆、VPN、代理、ISP 或路由器規則 |
| TCP 成功但 TLS 失敗 | TLS（加密通訊）握手被攔截或憑證鏈異常 | 檢查安全軟體、TLS inspection、公司代理憑證 |
| ChatGPT / auth 回 `403` 或 challenge | Web 端可達，但被 Cloudflare 或瀏覽器狀態挑戰 | 用乾淨 Edge profile 測試；若乾淨 profile 可用，問題多半在 cookie、extension、service worker 或瀏覽器快取 |
| Codex CLI 找不到 | `codex` 不在 PATH 或未安裝於目前 Windows 使用者環境 | 檢查 Codex 安裝來源與 PATH，不先假設網路問題 |
| Codex 候選檔存在但 `codex` 找不到 | Codex 可能已安裝但 PATH 未包含其目錄 | 使用報告中的候選路徑直接啟動，或把該目錄加入目前使用者 PATH |
| Node.js / npm 找不到 | npm 型安裝、文件 helper 或部分工具鏈會失敗 | 補 Node.js 後再重跑診斷 |
| proxy 環境變數存在 | 目前行程可能被代理設定污染 | 用 `launch_codex_clean_network_env.ps1` 測試無代理行程 |

## 六、技術邊界

此入口不會：

1. 安裝套件。
2. 改 Windows 網路設定。
3. 改防火牆。
4. 讀取或輸出 API key 內容。
5. 對外部 API 進行資料寫入或狀態突變。

只有在明確加入 `-RepairUserPath` 時，才可能改目前使用者 PATH；報告與 seal 會記錄 `side_effects.changes_user_path`。

此入口會：

1. 產生診斷報告。
2. 產生 SHA256 封緘。
3. 產生候選修復包裝器。
4. 以技術觀測結果區分 DNS、TCP、TLS、HTTP、認證、瀏覽器狀態、CLI 缺件與代理污染。
5. 重新檢查 `codex --version`、OpenAI API 網路路徑及 ChatGPT/auth Web 可達性，輸出 `PASS_WINDOWS_GPT_CODEX_READINESS` 或 `HOLD_WINDOWS_GPT_CODEX_READINESS`。

## 七、與 Linux 節點觀測的對照

截至 2026-07-01，Linux（類 Unix 作業系統）節點已觀測到：

1. `https://api.openai.com/v1/models` 回 `401`，表示 API 網路路徑可達，缺認證是預期結果。
2. `https://chatgpt.com/` 與 `https://auth.openai.com/` 對 headless `curl` 回 `403/challenge`，表示 Web 端可達但存在瀏覽器/Cloudflare challenge 層。
3. `cdn.oaistatic.com` 與 `files.oaiusercontent.com` root path 回 `404`，表示 CDN（內容傳遞網路）可達，root path 無內容是預期現象。

因此，若 Windows 端仍無法正常運行，優先比較 Windows 報告與 Linux 觀測在 DNS、代理、TLS、瀏覽器 profile、Codex CLI 與 Node/npm 層的差異。
