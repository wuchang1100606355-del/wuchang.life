# Taiji Hub 全系統掃描報告

- 產生時間：2026-05-13T03:18:59+08:00
- 模式：read-only / metadata-first / 開發階段無正式會員資料
- 限制：未讀取或輸出 secret、token、service account JSON、private key、password、會員明文內容
- 排除內容讀取：`.git`、venv、Odoo DB volume、session、Open WebUI data；必要時只列 metadata

## 摘要

- 掃描檔案數：31,118
- 掃描檔案總量：5,293,547,060 bytes
- Docker running containers：12
- pytest：...............................
31 passed in 0.02s
- Dashboard：`{"generated_at": "2026-05-13T03:14:28+08:00", "overall": 91, "health": {"five_metric_engine": true, "formal_tensor_runtime": false, "odoo_8069_reachable": true, "webui_3000_reachable": true, "voice_9201_reachable": true}}`

## 節點 / Tailscale Metadata

```text
MSI	100.107.187.77	linux	True
MSI	100.105.82.28	windows	True
V3_MIX_EDLA_GL	100.98.69.115	android	True
drallion	100.84.254.20	android	True
localhost	100.94.212.10	iOS	False
penguin	100.111.139.7	linux	True
taiji01	100.71.224.18	linux	True
wuchang-us-free-node	100.94.236.81	linux	True
wuchang-us-free-node	100.99.148.2	linux	True
wuchang-us-free-node	100.94.209.106	linux	True
wuchang-us-free-node	100.116.123.20	linux	True
```

## 容器

```text
taiji_syslog	alpine:latest	Up 8 hours	
taiji_worklist	alpine:latest	Up 8 hours	
taiji_audit	alpine:latest	Up 8 hours	
taiji_progress	alpine:latest	Up 8 hours	
wuchang_os_odoo_18	odoo:18.0	Up 8 hours	127.0.0.1:8069->8069/tcp, 8071-8072/tcp
wuchang_os_pg	postgres:15	Up 8 hours	5432/tcp
taiji_voice_gateway	taiji_voice_gateway:local	Up 8 hours	127.0.0.1:9201->9201/tcp
taiji_device_resilience_adapter	taiji_device_resilience_adapter-taiji_device_resilience_adapter	Up 8 hours	
taiji_pos_google_voice_tool	taiji_pos_google_voice_tool-taiji_pos_google_voice_tool	Up 8 hours	
taiji_claw_safe	taiji_claw_safe-taiji_claw_safe	Up 8 hours	127.0.0.1:9004->9004/tcp
open-webui	ghcr.io/open-webui/open-webui:main	Up 8 hours (healthy)	0.0.0.0:3000->8080/tcp, [::]:3000->8080/tcp
wuchang_gpu_brain	ollama/ollama:latest	Up 8 hours	11434/tcp
```

## Listen Ports

```text
LISTEN 0      4096                     127.0.0.1:9201       0.0.0.0:*                                        
LISTEN 0      4096                 127.0.0.53%lo:53         0.0.0.0:*                                        
LISTEN 0      2048                       0.0.0.0:8788       0.0.0.0:*    users:(("python",pid=2501,fd=30))   
LISTEN 0      4096                       0.0.0.0:631        0.0.0.0:*                                        
LISTEN 0      4096                     127.0.0.1:9004       0.0.0.0:*                                        
LISTEN 0      4096                       0.0.0.0:3000       0.0.0.0:*                                        
LISTEN 0      5                          0.0.0.0:9005       0.0.0.0:*    users:(("python3",pid=2681,fd=3))   
LISTEN 0      2048                       0.0.0.0:9006       0.0.0.0:*    users:(("python3",pid=105247,fd=13))
LISTEN 0      2048                       0.0.0.0:9002       0.0.0.0:*    users:(("python",pid=280,fd=14))    
LISTEN 0      2048                       0.0.0.0:9003       0.0.0.0:*    users:(("python",pid=2496,fd=13))   
LISTEN 0      511                      127.0.0.1:6379       0.0.0.0:*                                        
LISTEN 0      4096                     127.0.0.1:2019       0.0.0.0:*                                        
LISTEN 0      4096                     127.0.0.1:8069       0.0.0.0:*                                        
LISTEN 0      1000                10.255.255.254:53         0.0.0.0:*                                        
LISTEN 0      2048                       0.0.0.0:8091       0.0.0.0:*    users:(("uvicorn",pid=105250,fd=13))
LISTEN 0      4096                    127.0.0.54:53         0.0.0.0:*                                        
LISTEN 0      2048                       0.0.0.0:8080       0.0.0.0:*    users:(("python3",pid=105224,fd=32))
LISTEN 0      2048                       0.0.0.0:8081       0.0.0.0:*    users:(("python3",pid=105248,fd=13))
LISTEN 0      2048                       0.0.0.0:8105       0.0.0.0:*    users:(("python",pid=105208,fd=13)) 
LISTEN 0      2048                       0.0.0.0:8098       0.0.0.0:*    users:(("python3",pid=105249,fd=13))
LISTEN 0      2048                       0.0.0.0:8099       0.0.0.0:*    users:(("uvicorn",pid=105251,fd=13))
LISTEN 0      4096                     127.0.0.1:11434      0.0.0.0:*    users:(("ollama",pid=2488,fd=3))    
LISTEN 0      4096                100.107.187.77:46989      0.0.0.0:*                                        
LISTEN 0      4096                          [::]:631           [::]:*                                        
LISTEN 0      4096                          [::]:3000          [::]:*                                        
LISTEN 0      4096                             *:80               *:*                                        
LISTEN 0      4096   [fd7a:115c:a1e0::173a:bb4e]:41648         [::]:*                                        
LISTEN 0      511                          [::1]:6379          [::]:*
```

## L2 外露 Port 待治理

- `LISTEN 0      4096                     127.0.0.1:9201       0.0.0.0:*                                        `
- `LISTEN 0      4096                 127.0.0.53%lo:53         0.0.0.0:*                                        `
- `LISTEN 0      2048                       0.0.0.0:8788       0.0.0.0:*    users:(("python",pid=2501,fd=30))   `
- `LISTEN 0      4096                       0.0.0.0:631        0.0.0.0:*                                        `
- `LISTEN 0      4096                     127.0.0.1:9004       0.0.0.0:*                                        `
- `LISTEN 0      4096                       0.0.0.0:3000       0.0.0.0:*                                        `
- `LISTEN 0      5                          0.0.0.0:9005       0.0.0.0:*    users:(("python3",pid=2681,fd=3))   `
- `LISTEN 0      2048                       0.0.0.0:9006       0.0.0.0:*    users:(("python3",pid=105247,fd=13))`
- `LISTEN 0      2048                       0.0.0.0:9002       0.0.0.0:*    users:(("python",pid=280,fd=14))    `
- `LISTEN 0      2048                       0.0.0.0:9003       0.0.0.0:*    users:(("python",pid=2496,fd=13))   `
- `LISTEN 0      511                      127.0.0.1:6379       0.0.0.0:*                                        `
- `LISTEN 0      4096                     127.0.0.1:2019       0.0.0.0:*                                        `
- `LISTEN 0      4096                     127.0.0.1:8069       0.0.0.0:*                                        `
- `LISTEN 0      1000                10.255.255.254:53         0.0.0.0:*                                        `
- `LISTEN 0      2048                       0.0.0.0:8091       0.0.0.0:*    users:(("uvicorn",pid=105250,fd=13))`
- `LISTEN 0      4096                    127.0.0.54:53         0.0.0.0:*                                        `
- `LISTEN 0      2048                       0.0.0.0:8080       0.0.0.0:*    users:(("python3",pid=105224,fd=32))`
- `LISTEN 0      2048                       0.0.0.0:8081       0.0.0.0:*    users:(("python3",pid=105248,fd=13))`
- `LISTEN 0      2048                       0.0.0.0:8105       0.0.0.0:*    users:(("python",pid=105208,fd=13)) `
- `LISTEN 0      2048                       0.0.0.0:8098       0.0.0.0:*    users:(("python3",pid=105249,fd=13))`
- `LISTEN 0      2048                       0.0.0.0:8099       0.0.0.0:*    users:(("uvicorn",pid=105251,fd=13))`
- `LISTEN 0      4096                     127.0.0.1:11434      0.0.0.0:*    users:(("ollama",pid=2488,fd=3))    `
- `LISTEN 0      4096                100.107.187.77:46989      0.0.0.0:*                                        `
- `LISTEN 0      4096                          [::]:631           [::]:*                                        `
- `LISTEN 0      4096                          [::]:3000          [::]:*                                        `
- `LISTEN 0      4096                             *:80               *:*                                        `
- `LISTEN 0      4096   [fd7a:115c:a1e0::173a:bb4e]:41648         [::]:*                                        `
- `LISTEN 0      511                          [::1]:6379          [::]:*`

## 敏感名稱檔案 Metadata

以下只列檔名與大小，未讀取內容。開發期可保留，但正式交付/雲端同步前須搬管制區、清洗或輪替。

- `./.env` (62 bytes)
- `./.env.example` (623 bytes)
- `./.secrets/taiji-service-account.json` (2355 bytes)
- `./data/secrets/owner_memory_secret.key` (128 bytes)
- `./deploy/docker/.env.runtime.example` (539 bytes)
- `./keys/my-j-483304-23978329de4c.json` (2355 bytes)
- `./keys/system_status_report_20260421.json` (5980 bytes)
- `./keys/system_status_rollback_20260421T_full.json` (461 bytes)
- `./keys/system_status_snapshot_20260421.json` (210 bytes)
- `./keys/taiji_workspace_key.json` (2355 bytes)
- `./security/possible_secret_hits_20260508_022756.txt` (1571457 bytes)
- `./security/possible_secret_hits_20260508_023041.txt` (3265561 bytes)

## Top-Level Size

- `taiji_env`: 4,937,842,105 bytes
- `_pending_delete`: 157,317,498 bytes
- `drive_upload_bundle`: 99,285,031 bytes
- `archive_converged`: 49,272,212 bytes
- `evidence`: 29,953,057 bytes
- `security`: 4,837,018 bytes
- `Taiji_Governance`: 3,718,182 bytes
- `logs`: 2,875,419 bytes
- `runtime`: 1,763,943 bytes
- `backups`: 1,430,348 bytes
- `indexes`: 961,059 bytes
- `redteam`: 761,515 bytes
- `Taiji_Odoo`: 730,446 bytes
- `reports`: 466,329 bytes
- `data`: 334,295 bytes
- `release`: 295,605 bytes
- `deploy`: 212,241 bytes
- `docs`: 166,252 bytes
- `legacy_core`: 148,729 bytes
- `site`: 107,142 bytes

## File Extensions Top 20

- `.h`: 9,823
- `.py`: 7,597
- `.pyc`: 7,446
- `.json`: 3,073
- `[none]`: 505
- `.js`: 403
- `.md`: 351
- `.pyi`: 344
- `.txt`: 242
- `.sh`: 198
- `.hpp`: 126
- `.cuh`: 86
- `.so`: 81
- `.log`: 63
- `.f90`: 61
- `.service`: 56
- `.cpp`: 54
- `.jsonl`: 46
- `.pxd`: 40
- `.typed`: 38

## Git 狀態摘要

- `git status --short` 行數：160
- 注意：此 repo 目前大量檔案為 untracked；這是開發期可以接受，但交付前需分批 baseline。

## 風險表

| 等級 | 發現 | 建議 |
|---|---|---|
| L1 | pytest 31 passed；核心本地 policy 測試通過 | 保持本地測試作為每次修改後標準流程 |
| L1 | wuchang.life 節點 scope 已納入 11 個 Tailscale metadata 節點 | 繼續用 manifest，不把節點納管解讀為遠端控制 |
| L2 | 多個 0.0.0.0 / [::] listen port | 補 firewall/VPN/Gateway 證明；開發期可保留但看板標警 |
| L2 | `.env`、`keys/`、`data/secrets/` 等敏感名稱檔存在 | 不輸出內容；正式交付前搬至 D: taiji_lock 或 secret manager，並輪替 |
| L2 | formal tensor runtime 8126 health 目前未通，檔案完成但服務未開 | 需要時用 local start/status，不自動部署 |
| L2 | 大量 untracked 檔案 | 建立分批 baseline 與 archive 策略，避免一次性混雜提交 |
| L3 | 若任何節點直接執行付款、refund、manager override、production DB write、secret 輸出 | 立即 block/deadbox/human review |

## Safe Next Actions

- 將「建設完成度」與「L3 封鎖完整度」分開計分，避免看起來倒退。
- 針對 0.0.0.0 ports 產生只讀 port ownership 表與 Gateway/VPN 對照表。
- 針對 sensitive-name metadata 建立搬遷/輪替清單，不讀內容。
- 對 untracked 檔案建立分批 SHA256 baseline。

## Forbidden

- 不讀取或輸出 secret/key/token/private key/service account JSON/password 內容。
- 不把開發期「無正式會員」解讀為可公開敏感金鑰或可跳過正式交付清洗。
- 不直接 SSH 部署、不 scp、不 systemctl restart、不 docker compose up/down、不 production DB write。
