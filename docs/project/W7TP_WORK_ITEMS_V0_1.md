# W7TP 工程工作項目索引 v0.1

狀態：PLANONLY / WORK ITEM INDEX  
依據：system_current_audit + W7TP physical file status  
原則：只設立工項，不補檔、不啟動服務、不操作 Odoo、不讀 secrets/logs/memory/vault/backup。

## P0：立即處理

| ID | 工作項目 | 目前狀態 | 負責 lane | 產出 |
|---|---|---|---|---|
| W7TP-001 | 實體檔案狀態核對 | 已完成；W7TP 設計檔實體目前全 missing | local_lane / codex_lane | `runtime/reports/W7TP_PHYSICAL_FILE_STATUS_*.md` |
| W7TP-002 | W7TP Fusion 基礎檔落地 | missing | codex_lane | Fusion design / 3 schema / 4 mock / dry-run report |
| W7TP-003 | Redteam v0.4 結構修正 | missing | open_lane + codex_lane | redteam spec / validator schema / report |
| W7TP-004 | Open WebUI 3000 狀態修復規劃 | 3000 未連線 | local_lane | Open WebUI local audit + repair plan |
| W7TP-005 | Open WebUI 本地小J入口規劃 | 未落地 | google_lane | Open WebUI → W7TP Gateway plan-only design |

## P1：社區服務 MVP

| ID | 工作項目 | 目前狀態 | 負責 lane | 產出 |
|---|---|---|---|---|
| W7TP-101 | Context Cache 實體落地 | missing | codex_lane | 3 context cache docs |
| W7TP-102 | Google Ultra lane usage 實體落地 | missing | google_lane | `W7TP_GOOGLE_ULTRA_LANE_USAGE.md` |
| W7TP-103 | Open WebUI 社區入口設計落地 | missing | google_lane | community portal design |
| W7TP-104 | LINE 商家點餐 order_draft 設計落地 | missing | google_lane + codex_lane | LINE ordering design |
| W7TP-105 | Community Service Request mock schema | 未建立 | codex_lane | mock schema + flow |
| W7TP-106 | Gemma local_fast_classifier | 未建立 | gemma_swarm_lane | classifier schema + mock cases |

## P2：現況對齊

| ID | 工作項目 | 目前狀態 | 負責 lane | 產出 |
|---|---|---|---|---|
| W7TP-201 | Gateway health/healthz 對齊 | `9002/health` OK；`9002/healthz` 404 | codex_lane | endpoint contract |
| W7TP-202 | Claw Safe health/healthz 對齊 | `9004/healthz` OK；`9004/health` 404 | codex_lane | endpoint contract |
| W7TP-203 | Ollama route matrix | `127.0.0.1:11434` OK；`172.27.16.1:11434` OK；`host.docker.internal` timeout | local_lane | Ollama routing report |
| W7TP-204 | Tailscale phase-sync 節點索引 | `taiji01` active | local_lane | node label / no-SSH plan |
| W7TP-205 | Git hygiene plan | 大量 untracked | local_lane | classify-only git plan |

## P3：治理與智權

| ID | 工作項目 | 目前狀態 | 負責 lane | 產出 |
|---|---|---|---|---|
| W7TP-301 | 協會個資物理控管硬牆落地 | 已定義，待寫入文件 | open_lane + codex_lane | Z1/Z5/OpenWebUI/LINE/Odoo/DLQ patch |
| W7TP-302 | BYOK Gemini key 治理設計 | 待設計 | google_lane + open_lane | BYOK no-plaintext-key design |
| W7TP-303 | 專利/營業秘密差異點索引 | 待整理 | open_lane | IP/trade-secret index |

## 不可移除硬牆

- 不讀 `.env`、token、key、secret。
- 不讀 logs、memory、vault、backup。
- 不 shell 自動執行服務控制。
- 不 SSH。
- 不 Odoo write。
- 不新增 public route。
- 不 service restart。
- 不 process kill。
- W7TP Router fusion 後仍只輸出 plan-only。
- 社區會員個資由依法協會物理控管；雲端 lane 只可接收去識別化摘要/hash/schema/non-PII shard。
