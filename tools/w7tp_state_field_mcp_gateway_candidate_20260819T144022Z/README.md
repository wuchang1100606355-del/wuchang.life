# W7TP 8D 狀態場分散式算力 MCP 閘道候選

狀態：`CANDIDATE_ONLY`。本目錄不構成正式啟用、W7TP 正典、總場裁決、Connector 註冊或遠端授權。

## 定義與邊界

本候選把 8D 實作成八個具啟動條件、處理函數、狀態轉換與融合規則的 Runtime OS 程式：Identity、Intent、Authority、Relation、Resource、Time、Risk、Governance。不同工具會啟動不同維度集合；治理失敗即不呼叫 bounded adapter。

ADI 只在執行後建立 coordinate、relation、decision、transition、time、space、evidence 索引。ADI 不含 callable、handler、command 或啟動權限，亦不是 8D 本體。

每次成功呼叫形成：`State → Coordinate → SHA-256 → Candidate Packet`。Packet 固定標示 `land=NOT_REQUESTED_CANDIDATE_ONLY`。

Tailscale、SSH、HTTPS 只列為 `CARRIER_ONLY`，`generative_transport=false`。本候選沒有啟用或修改它們。

## 實作

- Python 3.12，沿用既有 FastAPI／Uvicorn；未安裝套件。
- 只綁定精確字面值 `127.0.0.1`；拒絕 `0.0.0.0`、IPv6、`localhost` 或其他 host 覆寫。
- MCP JSON-RPC Streamable HTTP 候選端點：`POST /mcp`；本機健康端點：`GET /healthz`。
- 無任意 Shell、命令、路徑、檔案讀取、遠端 HTTP、SSH、Docker socket、systemd、資料庫或控制面 client。
- 所有 input schema 均為 closed schema (`additionalProperties=false`)。
- 六個觀測工具標示 `readOnlyHint=true`。兩個 `prepare_*` 工具因會更新 process-local 的限時／防重放候選 registry，誠實標示 `readOnlyHint=false`；它們仍是非破壞性、非 open-world、不持久化且不執行。

## 八個能力函數

1. `list_nodes`
2. `get_node_health`
3. `get_compute_capability`
4. `get_service_status`
5. `read_bounded_logs`
6. `get_state_field_topology`
7. `prepare_task_candidate`
8. `prepare_authorization_request`

`read_bounded_logs` 初期只允許候選內合成 fixture；現有 production/runtime log 一律拒絕。輸入讀取、服務、行數、時間與輸出 byte 皆有上限，缺少合法時間標記的行會 fail closed 省略；JSON token、Basic/Bearer、JWT、key 與登入識別均遮罩。

`prepare_task_candidate` 與 `prepare_authorization_request` 不寫檔、不發送、不執行。Task 的 candidate ID、目標、具體參數、簽發／到期時間與 SHA-256 綁定在最多 256 筆的 process-local registry；授權候選只能由仍有效的 task 產生一次，TTL 不得超過 task 剩餘生命期，rollback/stop 皆走 allowlist。此單次限制僅在目前 process 記憶體範圍，輸出仍明確標示 `authority_effect=NONE`、`exactly_once_enforced=false`、`consumer_present=false`。

## 節點與故障域

去識別化盤點共 11 個 Tailscale 邏輯節點、9 個在線：Linux 5、Windows 2、Android 3、iOS 1。MSI Windows/WSL 共用 `physical-msi-host`；taiji03 Windows/Linux 共用 `physical-taiji03-host`，各只計一個實體故障域。其餘節點缺硬體識別證據，不宣稱獨立故障域。Android/iOS 僅提供 App/API/遙測候選且 `shell_capable=false`。未觀察到可證成的 subnet gateway 或 cloud extension node。

## 本機驗證

最終完成 40 個單元／合成 fixture／HTTP／紅隊案例；語法檢查與 dependency-free bounded static type-resolution 均通過。後者解析全部來源、要求完整 annotation、載入所有模組並解析 58 個 callable type hints；它不冒充 mypy/pyright 的 whole-program inference。

完整驗證（候選完成後可重跑）：

```bash
cd /home/taiji_admin/Taiji_Hub/tools/w7tp_state_field_mcp_gateway_candidate_20260819T144022Z && PYTHONPATH=src python3 scripts/verify_candidate.py
```

前景啟動本機候選（不安裝、不註冊）：

```bash
cd /home/taiji_admin/Taiji_Hub/tools/w7tp_state_field_mcp_gateway_candidate_20260819T144022Z && PYTHONPATH=src python3 -m w7tp_state_field_gateway.server --host 127.0.0.1 --port 8765
```

## 強制停止線

未執行 systemd 安裝/啟用、port 開放、Tailscale Serve/Funnel/SSH/ACL/Subnet 變更、Cloudflare Tunnel、OAuth/API key/token、ChatGPT Connector 登錄、遠端連線、部署、重啟、資料庫寫入或正式 landing。

唯一正式啟用阻塞為 `HOLD_AUTHORIZED_REMOTE_MCP_REACHABILITY_NOT_ESTABLISHED`：`127.0.0.1` 不可由託管 ChatGPT 直接到達；未取得另案批准的遠端 HTTPS 或 OpenAI Secure MCP Tunnel 路徑及對應 workspace/identity/authorization 綁定。本輪依強制停止線不處理該阻塞。

## 官方文件基線

- OpenAI MCP server build: https://developers.openai.com/plugins/build/mcp-server
- OpenAI connect/test: https://developers.openai.com/plugins/deploy/connect-chatgpt
- OpenAI Secure MCP Tunnel: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- Tailscale Serve: https://tailscale.com/docs/features/tailscale-serve
- Tailscale Funnel: https://tailscale.com/docs/features/tailscale-funnel
- Tailscale SSH: https://tailscale.com/docs/features/tailscale-ssh

查核日：2026-08-19。正式化前必須重新核對版本、transport、驗證與 workspace policy；本候選固定的 MCP protocol version 僅為本機相容測試基線，不是正式相容性裁決。
