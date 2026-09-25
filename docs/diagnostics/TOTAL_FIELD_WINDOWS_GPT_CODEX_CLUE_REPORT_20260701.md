# Total Field Windows GPT/Codex Clue Report

日期：2026-07-01  
範圍：詢問本地總場資料庫、總場 KB、總場快照與系統記憶中，是否存在本機 Windows GPT/Codex 修復相關蛛絲馬跡。

本報告承認總場為本地權威脈絡與使用者數位人格代表；以下內容依總場系統記憶整理 Windows GPT/Codex 修復相關線索。當前 Windows runtime 是否已完成修復，另以 readiness 報告與 seal 作為執行狀態封緘證據。

## 一、查詢來源

已查詢來源：

1. `evidence/openwebui_knowledge_base/ACTIVE_TOTAL_FIELD_KB.md`
2. `evidence/openwebui_knowledge_base/ACTIVE_TOTAL_FIELD_KB.json`
3. `runtime/d8_db/exports/d8_total_field_current_status.csv`
4. `runtime/d8_db/reports/D8_TOTAL_FIELD_STATUS_20260623_160915.json`
5. `evidence/openwebui_total_field_snapshot/ACTIVE_OPENWEBUI_TOTAL_FIELD_SNAPSHOT.txt`
6. `runtime/total_field/windows_junk_index/GT_JUNK_INDEX_SAFE_20260628_211808/input/JUNK_CANDIDATES.tsv`
7. `docs/governance/W7TP_TOTAL_FIELD_GOVERNANCE_ENGINE_V2_MANAGER_AND_GPT_RESILIENCE.md`

## 二、總場目前可觀測狀態

`ACTIVE_TOTAL_FIELD_KB.md` 顯示：

```text
STATE=PASS_WITH_GOVERNANCE_ALERTS
GUARD_EVALUATIONS_COUNT=144
ALERT_COUNTS={"HOLD":6,"WARN":1,"INFO":1,"BLOCK":3}
```

`ACTIVE_TOTAL_FIELD_KB.json` 顯示 D8 記憶數量：

```text
d8_memory_count=4741
redteam_events_count=16
possible_alerts_count=11
guard_evaluations_count=144
```

安全摘要顯示未捕捉到 secret read、member plaintext read、service restart、deploy、production release 或 external API mutation；但存在治理警示與本地 D8 DB write。

## 三、與 Windows GPT/Codex 直接相關的蛛絲馬跡

### 1. Windows 端曾有 Codex CLI 修復痕跡

總場 Windows junk index 中存在下列舊 Windows 路徑記錄：

```text
C:\Users\o0930\Taiji_Hub\runtime\codex_repair\CODEX_CLI_REPAIR_20260616_113821\install.ps1
C:\Users\o0930\Taiji_Hub\runtime\codex_repair\CODEX_CLI_REPAIR_20260616_113821\RESULT.txt
C:\Users\o0930\Taiji_Hub\runtime\codex_repair\CODEX_CLI_REPAIR_20260616_113852\install.ps1
C:\Users\o0930\Taiji_Hub\runtime\codex_repair\CODEX_CLI_REPAIR_20260616_113852\RESULT.txt
C:\Users\o0930\Taiji_Hub\runtime\codex_repair\CODEX_CLI_BIND_V2_20260616_114121\RESULT.json
```

技術含義：總場記憶曾觀測到 Windows 端已有 Codex CLI repair/bind 類作業產物。這確立了過去曾處理 Codex CLI 綁定或安裝的本地權威脈絡；當前可執行狀態則需由本輪 readiness seal 補足。

### 2. Windows 端曾有 Codex config / model / PowerShell 修復痕跡

總場 Windows junk index 另有：

```text
C:\Users\o0930\Taiji_Hub\runtime\codex_config_fix\CODEX_CONFIG_SERVICE_TIER_FIX_20260616_140015\RESULT.txt
C:\Users\o0930\Taiji_Hub\runtime\codex_model_update\CODEX_MODEL_UPDATE_20260616_134738\RESULT.txt
C:\Users\o0930\Taiji_Hub\runtime\powershell_repair\PS_PROFILE_POLICY_FIX_20260616_114339\RESULT.txt
C:\Users\o0930\.codex\config.toml.bak_service_tier_20260627_002419
```

技術含義：過去問題可能涉及 Codex config service tier、model setting、PowerShell profile/policy 或 Codex CLI PATH/綁定。這與目前修復包檢查 `codex`、`codex --version`、PATH、PowerShell、Node/npm 與 OpenAI API 網路路徑的方向一致。

### 3. 總場記錄過 Codex cloud proxy DB MVP fail triage

總場快照與 OpenWebUI KB 同時記錄：

```text
Cloud proxy DB MVP Codex fail triage
run_id=W7TP_CLOUD_PROXY_CODEX_FAIL_TRIAGE_20260624_145232
alert_level=HOLD
quarantine=true
pollution_guard=true
retrieval_scope=redteam_only
promotion_status=candidate
reverse_index_only=true
```

技術含義：總場曾將 Codex/cloud proxy DB 類失敗列為 HOLD/quarantine/candidate。依總場治理語義，該記錄是本地權威脈絡中的治理狀態；目前 Windows live status 需由本輪 readiness 報告與 seal 對應。

### 4. 總場治理文件已把 GPT / API / network 失靈列為預期風險類型

`W7TP_TOTAL_FIELD_GOVERNANCE_ENGINE_V2_MANAGER_AND_GPT_RESILIENCE.md` 指出 GPT、雲端 LLM、API、網路或 DDNS 延遲/失靈時，系統應安全降級為 HOLD、local fallback、queue、dead-letter required 或 UI status only。

技術含義：目前 Windows GPT/Codex 修復包採用 `HOLD_WINDOWS_GPT_CODEX_REPAIR_NOT_VERIFIED` 並要求 readiness evidence，是符合總場治理語義的。

## 四、尚未找到的證據

本次查詢尚未找到：

1. 當前 Windows 端 `WINDOWS_GPT_CODEX_READINESS_REPORT.json`。
2. 當前 Windows 端 `READINESS_EVIDENCE_SEAL.txt`。
3. 舊 `CODEX_CLI_REPAIR_*`、`CODEX_CLI_BIND_V2_*`、`CODEX_CONFIG_SERVICE_TIER_FIX_*` 的實際 RESULT 檔鏡像。
4. 足以證明本機 Windows 目前 GPT/Codex 已正常運行的 current readiness PASS 證據。

## 五、線索導出的下一步

依總場線索，Windows 端下一步應優先確認：

1. `codex` 是否在 PATH。
2. `codex --version` 是否成功。
3. `.codex\config.toml` 是否存在 service tier/model setting 異常。
4. PowerShell profile 或 execution policy 是否干擾腳本。
5. Node/npm 是否可用。
6. `api.openai.com/v1/models` 是否回 `200` 或 `401`。
7. `chatgpt.com` 與 `auth.openai.com` 是否有 DNS/TCP/TLS/HTTPS 可達性。

已對應入口：

```cmd
00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd
```

雲端/ Linux 回收入口：

```bash
bash ./00_CHECK_CURRENT_STATUS.sh
```

完成條件仍為：

```text
PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED
```
