# 本機匝道管控生效紀錄

版本：2026-05-13  
狀態：ACTIVE  
節點：MSI / Windows 11 Pro / WSL Ubuntu  

## 目的

將本機 Windows 11 Pro、WSL Ubuntu、Ollama、OpenWebUI、瀏覽器預覽與開發 shell 納入 Taiji Gateway / Five Metric Gate 管控範圍。

## 本機身份

| Identity | 對應 | 用途 | 管控 |
|---|---|---|---|
| `TDI-NODE-admin-msi` | WSL Ubuntu / `/home/taiji_admin/Taiji_Hub` | 開發、治理檔、runtime orchestration | Gateway required for system action |
| `TDI-NODE-msi-win11-operator-console` | Windows 11 Pro / Ollama UI / browser | 人類操作窗、預覽、確認 | Gateway required for mutation |
| `TDI-SERVICE-local-ollama` | `127.0.0.1:11434` | 本地 LLM backend | no direct production mutation |
| `TDI-SERVICE-local-openwebui` | `127.0.0.1:8080` | 本地 AI UI | preview/chat only unless gateway routed |

## 允許

- 本地聊天。
- 模型測試。
- 草稿生成。
- 文件、schema、manifest、測試與本地預覽。
- 只讀健康檢查。
- 經 Gateway 轉換後的治理封包。

## 禁止

- Ollama UI 直接改 production Odoo / Google / router / Docker / systemd。
- OpenWebUI 直接讀取或輸出 secret、token、service account JSON、OAuth credential。
- 本地 LLM 直接執行 payment、refund、discount override、manager override。
- 未經 Gateway / audit / human decision 的會員明文匯出。
- 未經授權的遠端部署、SSH/SCP、production DB write。

## 判定

本機可以是系統控制台與低延遲 LLM 後端，但不是最高權限繞道。
自然語言輸入不等於執行權；本機 LLM 輸出必須依任務風險轉成五維度規封包後，由 Gateway / Five Metric Gate 判斷。

