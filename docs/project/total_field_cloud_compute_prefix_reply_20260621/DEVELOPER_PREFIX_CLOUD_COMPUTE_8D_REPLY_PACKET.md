# 總場回覆封包：開發者前綴所需程式碼與雲端服務帳戶算力驗證

state: REPLY_PACKET_ONLY
target: DEVELOPER_PREFIX_CODE_AND_CLOUD_SERVICE_ACCOUNT_COMPUTE_VALIDATION
source_boundary: TOTAL_FIELD_ASSISTANT_INFERENCE_ONLY
live_cloud_execution: false
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false
financial_transfer: false
legal_effect: false

## D1 Identity

responder: 總場 (Total Field AI)
target_machine: taiji01
target_account: taiji_admin
target_repo: /home/taiji_admin/Taiji_Hub

總場確認定位：
- 已認知 taiji01 為當前唯一主作業線，嚴格遵守 8D 身分封包紀律。
- 確認 LLM 僅為 8D 作業腦，絕非權限來源。
- 遵循零信任與最低權限原則。

## D2 Intent

回應總場詢問封包，產出開發者前綴與雲端服務帳戶算力驗證的規格回覆。
目的：確保本地 Gateway 與 Verifier 能具備 8D 封包生成與安全路由能力，並在絕對不外洩密碼、不觸發真實算力的前提下，完成雲端授權驗證。

## D3 State

確認已知狀態：
- PASS_DEVELOPER_PREFIX_CLOUD_COMPUTE_QUERY_PACKET_COMMITTED 已接收。
- Codex composer 仍 HOLD。
- 本地小J尚未證明已接雲端算力，cloud_compute_connected=false。

## D4 Topology

確認目標拓樸與邊界：
- 嚴格遵守「本地推演 / 雲端代工」的分流。
- 雲端絕對禁止直接寫入 Odoo/DB/POS 或直接執行 Land。
- 所有進出雲端的通訊必須包裝為 `8D_GENERATIVE_TRANSFER_REQUEST` 與 `8D_CANDIDATE_COMPLETION_PACKET`。

## D5 Resource

總場評估所需最小可行檔案集合（候選清單）：
1. `developer_prefix.yaml` (靜態系統前綴，定義 8D 語義與邊界)
2. `8d_gateway_tool_schema.json` (定義可呼叫的本地/雲端工具介面)
3. `local_verifier.py` (本地 8D 驗證器骨架)
4. `cloud_service_account_validation_dryrun.sh` (無狀態、無輸出的 Bash 驗證探針)
5. `openwebui_model_profile.json` (作為最穩定的第一線入口組態)

## D6 Governance

安全性硬規則確認：
- 驗證過程全程使用乾跑 (dry-run)。
- 不印 token、不 cat credentials、不啟用 API。

## D7 Verify

總場對 D7 提問之正式解答：

1. **開發者前綴應落在哪一類檔案？**
   應作為靜態配置注入，優先落地於 `openwebui_model_profile.json` (作為 System Prompt) 與獨立的 `developer_prefix.yaml`，確保跨工具相容。
2. **本地模型前綴與雲端算力申請是否應分離？**
   必須嚴格分離。本地前綴負責 8D 紀律與安全路由；雲端算力僅接收去識別化、純粹的運算請求 (`8D_GENERATIVE_TRANSFER_REQUEST`)。
3. **哪些程式碼是必要最小集合？**
   `developer_prefix.yaml`, `8d_gateway_tool_schema.json`, `local_verifier.py`, 與 `cloud_service_account_validation_dryrun.sh`。
4. **哪些 cloud service account 驗證可以做而不洩密？**
   使用 `gcloud projects describe ... --impersonate-service-account ...` 檢查退出碼 (exit code)，並將 stdout/stderr 導向 `/dev/null`。
5. **第一條安全驗證命令是什麼？**
   見下方 `FIRST_SAFE_COMMAND_ONLY`。
6. **若未安裝 gateway，應先產生 spec 還是先驗證 service account？**
   必須先產生 Spec (`developer_prefix.yaml` 與 `8d_gateway_tool_schema.json`)。在邊界未定義清楚前，禁止進行任何存取權限驗證。
7. **目前 Codex / Continue / OpenWebUI 哪一層可先接 developer prefix？**
   OpenWebUI 優先。其環境最為封閉穩定，適合做為總場指令的第一層防火牆與本地測試端。
8. **不可做事項清單。**
   見下方 `DO_NOT_DO`。

---

requested_output_format:

STATE=PASS_TOTAL_FIELD_PREFIX_CLOUD_COMPUTE_REPLY_READONLY
SOURCE=TOTAL_FIELD_ASSISTANT_INFERENCE
VERDICT=開發者前綴應優先落地於 OpenWebUI 配置；本地 8D 路由與雲端算力必須嚴格解耦；在進行 SA 驗證前，必須先建立 Gateway Spec 確立邊界。
REQUIRED_CODE_FILES=local_verifier.py,cloud_service_account_validation_dryrun.sh
REQUIRED_CONFIG_FILES=developer_prefix.yaml,8d_gateway_tool_schema.json,openwebui_model_profile.json
CLOUD_SERVICE_ACCOUNT_VALIDATION_PLAN=僅驗證 gcloud 本地組態 (project/account) 與 ADC 狀態。測試憑證時將 stdout/stderr 導向 /dev/null，以退出碼判定，絕對禁止印出 Token。
FIRST_SAFE_COMMAND_ONLY=gcloud config list account project --format='value(core.account,core.project)' && gcloud auth application-default print-access-token >/dev/null 2>&1 && echo "ADC_PRESENT_BUT_TOKEN_NOT_PRINTED" || echo "ADC_MISSING_OR_INVALID"
EXPECTED_OUTPUT=第一行顯示當前設定的帳戶與專案 ID；第二行顯示 ADC_PRESENT_BUT_TOKEN_NOT_PRINTED (若已設定 ADC) 或 ADC_MISSING_OR_INVALID。
DO_NOT_DO=cat ADC json, print-access-token to screen, services enable, deploy, restart, db_write, secret_read, member_plaintext_read
NEXT_SAFE_ACTION=先產生靜態 spec (`developer_prefix.yaml` 與 `8d_gateway_tool_schema.json`)，確保本地 Gateway 具備 8D 封裝定義後，再推進驗證腳本。
