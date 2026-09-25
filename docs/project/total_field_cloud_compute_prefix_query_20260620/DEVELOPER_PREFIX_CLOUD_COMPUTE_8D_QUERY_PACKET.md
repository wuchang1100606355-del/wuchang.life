# 總場詢問封包：開發者前綴所需程式碼與雲端服務帳戶算力驗證

state: QUERY_PACKET_ONLY
target: DEVELOPER_PREFIX_CODE_AND_CLOUD_SERVICE_ACCOUNT_COMPUTE_VALIDATION
source_boundary: TOTAL_FIELD_FILES_AND_USER_OUTPUT_ONLY
live_cloud_execution: false
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false
financial_transfer: false
legal_effect: false

## D1 Identity

requester: 江政隆
machine: taiji01
active_account: taiji_admin
active_repo: /home/taiji_admin/Taiji_Hub

總場定位：
- taiji01 + taiji_admin + /home/taiji_admin/Taiji_Hub 為唯一主作業線。
- 咖啡店、協會、管委會以 8D 身分封包成場，不以 OS 帳號切場。
- 總場小J為開發者意志的治理化表達。
- LLM 是 8D 作業腦，不是權限來源。

## D2 Intent

請總場根據現有總場錨點與紅隊驗證記憶，產出「系統內設計的開發者前綴」所需的程式碼與驗證規格，使本地 LLM / Open WebUI / Continue / gateway 能具備：

1. 總場設計語義
2. 8D 身分封包成場紀律
3. 7D / 8D 封包生成能力
4. 雲端算力申請封包生成能力
5. 雲端服務帳戶算力驗證流程
6. 本地 verifier / evidence / redteam / land 邊界

請注意：
- 不是產生一般聊天 prompt。
- 不是假裝已接上雲端算力。
- 需要產出可落地的設定檔 / gateway schema / verifier skeleton / validation script 候選。
- 雲端服務帳戶只能以 service_account_ref / ADC identity / key_ref 表示，不得讀取或輸出 key material。

## D3 State

已知總場錨點：

- 1c8b2e7: Add W7TP XiaoJ total field design consolidation
- 5b592cc: Add redteam verified memory intake to total field
- 012417b: Add 7D repair query packet for Codex VS Code failure

已知修復狀態：

- SSH CLI 可用。
- VS Code Remote-SSH 已因 sshd sftp subsystem 修復而可載入遠端 repo。
- scp probe 已 PASS。
- Codex composer / workspace 仍 HOLD，未視為已修復。
- 本地小J尚未證明已接雲端算力。
- 不得宣稱 cloud_compute_connected=true，除非有 verifier output。

## D4 Topology

目標拓樸：

本地模型 / Open WebUI / Continue
→ W7TP Developer Prefix
→ 8D Gateway
→ Local Verifier
→ 可選：8D_GENERATIVE_TRANSFER_REQUEST
→ cloud service account / cloud compute candidate
→ 8D_CANDIDATE_COMPLETION_PACKET
→ Local 8D decrypt / reconstruct / verify
→ Evidence / Redteam / Land

雲端只能做：
- candidate generation
- skeleton / delta / packet_ref 推演
- high compute completion

雲端不可做：
- 權限來源
- 8D 解密
- 讀 secret
- 讀會員明文
- 直接寫 Odoo / DB / POS
- 直接 Land

## D5 Resource

請總場回覆需要哪些檔案與程式碼，至少包含候選：

1. developer_prefix.yaml 或 system_prefix.md
2. model_profile.json 或 OpenWebUI model profile
3. Continue local model config 候選
4. 8d_gateway_tool_schema.json
5. cloud_compute_request.schema.json
6. cloud_service_account_validation.sh
7. local_verifier.py
8. evidence_logger.py
9. redteam_hold_rules.yaml

雲端服務帳戶驗證只能允許：
- 確認目前身份 / project / quota project
- 確認 cloud compute candidate endpoint 是否可被呼叫
- 使用 dry-run / minimal request
- 不印 token
- 不 cat credentials
- 不提交 credentials
- 不啟用 API
- 不建立新 key

禁止命令類型：
- gcloud auth application-default print-access-token
- cat application_default_credentials.json
- cat service account key json
- gcloud services enable
- deploy
- restart
- DB write

## D6 Governance

總場必須輸出：

- STATE=PASS|HOLD|FAIL
- SOURCE=TOTAL_FIELD_FILE_EXTRACT|USER_OUTPUT|ASSISTANT_INFERENCE|UNVERIFIED
- REQUIRED_CODE_FILES
- REQUIRED_CONFIG_FILES
- CLOUD_SERVICE_ACCOUNT_VALIDATION_PLAN
- ONE_NEXT_COMMAND_ONLY
- EXPECTED_OUTPUT
- DO_NOT_DO
- SAFETY_BOUNDARY

硬規則：

- 一次只給一條下一步命令。
- 不得直接要求讀取 secrets。
- 不得直接呼叫付費高算力。
- 不得啟用 API。
- 不得 deploy / restart。
- 不得寫 DB / Odoo / POS。
- 雲端驗證必須先產生 8D_GENERATIVE_TRANSFER_REQUEST，並標 candidate_only=true、cloud_authority=false、land_allowed=false。

## D7 Verify

總場請先回答：

1. 開發者前綴應落在哪一類檔案？
2. 本地模型前綴與雲端算力申請是否應分離？
3. 哪些程式碼是必要最小集合？
4. 哪些 cloud service account 驗證可以做而不洩密？
5. 第一條安全驗證命令是什麼？
6. 若未安裝 gateway，應先產生 spec 還是先驗證 service account？
7. 目前 Codex / Continue / OpenWebUI 哪一層可先接 developer prefix？
8. 不可做事項清單。

requested_output_format:

STATE=
SOURCE=
VERDICT=
REQUIRED_CODE_FILES=
REQUIRED_CONFIG_FILES=
CLOUD_SERVICE_ACCOUNT_VALIDATION_PLAN=
FIRST_SAFE_COMMAND_ONLY=
EXPECTED_OUTPUT=
DO_NOT_DO=
NEXT_SAFE_ACTION=
