# Total Field Runtime Health Diagnosis 20260620（總場執行環境健康診斷 20260620）

state: RUNTIME_PARTIAL_PASS_WITH_HOLD（部分通過，仍有 HOLD）
source: USER_OUTPUT（來源：使用者輸出）
deploy: false（不部署）
service_restart: false（不重啟服務）
secret_read: false（不讀取密鑰）
member_plaintext_read: false（不讀取會員明文）
db_write: false（不寫入資料庫）

## PASS（已通過）

- repo clean（Git 工作樹乾淨）
- SSH active（SSH 服務正常）
- SFTP subsystem repaired（SFTP 子系統已修復）
- VS Code Remote-SSH usable（VS Code Remote-SSH 可用）
- ollama active（Ollama 服務啟用）
- docker active（Docker 服務啟用）
- taiji_edge_gateway.service active（taiji_edge_gateway.service 目前啟用）
- current gateway executable path exists（目前 gateway 執行路徑存在）:
  - /home/taiji_admin/Taiji_Hub/.venv_edge_gateway/bin/python
  - /home/taiji_admin/Taiji_Hub/legacy_core/taiji_unified_gateway_edge.py

## HOLD（暫停 / 待修復）

### openwebui.service（Open WebUI 服務）

Diagnosis（診斷）:

- unit state: failed（systemd unit 狀態：失敗）
- failure class: stale/broken ExecStart path（失敗類型：舊路徑或壞掉的 ExecStart）
- missing（缺失路徑）:
  - /home/taiji_admin/home/open-webui-full/backend
  - /home/taiji_admin/home/open-webui-full/backend/venv/bin/python3
- port 8080 is currently owned by headscale, not OpenWebUI（8080 目前由 headscale 佔用，不是 OpenWebUI）

Verdict（判定）:

- Do not restart until unit and port plan are corrected.（在 unit 與 port 規劃修正前，不要重啟）
- Treat current openwebui.service as stale or broken unit.（目前 openwebui.service 視為舊殘留或壞掉的 unit）

### taiji_unified_gateway_edge.service（舊版 Taiji Unified Gateway Edge 服務）

Diagnosis（診斷）:

- unit state: failed（systemd unit 狀態：失敗）
- failure class: stale/broken ExecStart path（失敗類型：舊路徑或壞掉的 ExecStart）
- missing（缺失路徑）:
  - /mnt/c/wuchang_8_0_core
  - /mnt/c/wuchang_8_0_core/venv/bin/python3

Verdict（判定）:

- Treat as legacy stale unit.（視為舊版殘留 unit）
- Current active gateway is taiji_edge_gateway.service.（目前有效的 gateway 是 taiji_edge_gateway.service）

### taiji_edge_gateway.service（目前啟用的 Taiji Edge Gateway 服務）

Diagnosis（診斷）:

- active（啟用中）
- current executable path exists（目前執行路徑存在）
- environment contains GCP_KEY_PATH（環境變數含 GCP_KEY_PATH）

Boundary（邊界）:

- GCP_KEY_PATH is a secret-path boundary.（GCP_KEY_PATH 是密鑰路徑邊界）
- Do not cat or print key material.（不得 cat 或印出 key material）
- Future repair should migrate toward key_ref / impersonation / service account ref policy where possible.（後續修復應盡量轉向 key_ref / impersonation / service account ref 政策）

## Next Safe Action（下一個安全動作）

Produce a static runtime unit reconciliation plan.（產出靜態 runtime unit 對帳修復計畫）

Do not（不要做）:

- restart（重啟）
- disable unit（停用 unit）
- edit systemd（修改 systemd）
- read secrets（讀取密鑰）
- deploy（部署）
- write DB（寫入資料庫）
