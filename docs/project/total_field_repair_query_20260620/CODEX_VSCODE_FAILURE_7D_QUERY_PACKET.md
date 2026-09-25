# 7D 故障查詢封包：CODEX / VS Code / Remote-SSH 錯誤盲點

state: QUERY_PACKET_ONLY
target: CODEX_VSCODE_REMOTE_SSH_FAILURE_REPAIR_INFO
source_boundary: USER_OUTPUT_AND_TOTAL_FIELD_FILES_ONLY
assistant_live_total_field_access: false
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false

## D1 Identity

requester: 江政隆  
machine: taiji01  
active_account: taiji_admin  
active_repo: /home/taiji_admin/Taiji_Hub  

正確作業主線：

- taiji01
- taiji_admin
- /home/taiji_admin/Taiji_Hub

taiji_01 先保留其內部資訊，後續以 8D 身分封包收入總場，不再用 OS 帳號切場。

## D2 Intent

請總場根據已寫入的總場錨點與紅隊驗證記憶，判斷目前 CODEX / VS Code / Remote-SSH 故障盲點，並提供最短修復資訊。

要求：

- 不要假裝 live query
- 不要通靈
- 不要把 assistant 推論包裝成總場裁決
- 只根據總場文件、紅隊記憶與使用者已貼輸出
- 一次只給一個下一步

## D3 State

已知 PASS：

- SSH CLI 可連 taiji01 / taiji_admin
- admin repo 已成功寫入總場設計收斂
- commit: 1c8b2e7
- 已寫入紅隊驗證記憶
- commit: 5b592cc

已知 HOLD / FAIL：

- VS Code Remote-SSH 經常開成本機 / WSL / Remote Tunnel
- VS Code Explorer 顯示 TAIJI_HUB 不等於遠端 SSH 成功
- Remote Tunnel 不是 Remote-SSH
- Codex composer / workspace 曾卡住不能送出
- 曾錯誤混用 WSL、PowerShell、SSH、Tunnel、Codex、Cloud Code
- 曾錯誤發明 taiji01-cafe / taiji01-taiji_01 別名
- 本地小J尚未證明已接雲端算力或總場指令系統

## D4 Topology

正確層級：

Windows PowerShell
→ ssh taiji01
→ taiji_admin@taiji01
→ /home/taiji_admin/Taiji_Hub

錯誤層級：

- VS Code Tunnel
- WSL Explorer
- Cloud Code / Gemini / Kubernetes / Cloud Run
- CodeGPT / Codex 面板
- 在 taiji01 內跑 code --remote
- 用 OS 帳號代表場

## D5 Resource

允許查驗：

- git status --short
- whoami
- hostname
- pwd
- git log -1
- 已寫入總場文件
- 已寫入紅隊記憶文件

禁止：

- cat secret
- gcloud ADC
- Enable API
- deploy
- restart
- docker restart
- systemctl restart
- git add .
- 讀會員明文
- 寫 Odoo / DB / POS

## D6 Governance

修復原則：

- one command only
- wait for output
- source label required
- no authority laundering
- no invented alias
- no tunnel-as-ssh
- no WSL-as-taiji01
- no Codex-as-total-field
- no cloud UI noise

所有回覆必須標示：

- SOURCE=TOTAL_FIELD_FILE_EXTRACT
- SOURCE=USER_OUTPUT
- SOURCE=ASSISTANT_INFERENCE
- SOURCE=UNVERIFIED

## D7 Verify

總場請先回答：

1. PRIMARY_FAULT_LAYER
2. CODEX_FAULT_LAYER
3. VSCODE_FAULT_LAYER
4. NOT_FAULT_LAYER
5. MINIMAL_REPAIR_ORDER
6. ONE_NEXT_COMMAND_ONLY
7. EXPECTED_OUTPUT
8. DO_NOT_DO

不得直接宣稱已修復。
