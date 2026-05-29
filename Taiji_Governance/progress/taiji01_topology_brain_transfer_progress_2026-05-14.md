# taiji01 拓樸腦轉移工作進度圖

日期：2026-05-14  
工作區：`/home/taiji_admin/Taiji_Hub`  
目標節點：`taiji01` / `192.168.50.249` / `100.71.224.18`

## 目前狀態

```text
Windows 11 前端 LLM
  └─ sister-j-brain
      │
      │ 直連，但需由身分五維碼 / 節點白名單確認
      ▼
taiji01 五維碼身分匝道器
  ├─ listen: 100.71.224.18:11435
  ├─ allowlist: 已建立
  ├─ audit: 已建立
  └─ target: 127.0.0.1:11434
      │
      ▼
taiji01 Ollama 核心
  └─ metric-language-gateway-ai:latest
      │
      ▼
taiji01 權威記憶 / 知識庫
  ├─ data/f5_core_memory.db
  ├─ data/wuchang_5d_knowledge_vault.db
  └─ data/ledger/metric_memory.sqlite3  作為輔助 ledger，不列為主記憶庫
```

## 完成度圖塊

| 項目 | 狀態 | 完成度 | 驗證結果 |
|---|---:|---:|---|
| LAN SSH 指紋確認 | 完成 | 100% | `SHA256:ZmueqjkR3MUwm6gcCBTZqumCzdADnAWpgk1FLM56PK4` |
| 本機拓樸腦 Modelfile 轉換 | 完成 | 100% | 01 專用 `FROM llama3.1:8b` |
| 01 建立拓樸模型 | 完成 | 100% | `metric-language-gateway-ai:latest` available |
| 01 權威記憶庫同步 | 完成 | 100% | `canonical_memory_refs: 2/2` |
| 01 ledger 輔助庫 | 完成 | 100% | `metric_ledger_ref: available` |
| 01 五維碼身分匝道器 | 已啟動待固定化 | 80% | `100.71.224.18:11435 /health ok` |
| 01 正確開機檔 | 待實作 | 30% | 需改為 read-only health check + conditional start |
| Windows 11 前端直連設定 | 待驗證 | 40% | 建議連 `http://100.71.224.18:11435` |
| 系統架構完成度網頁 | 待刷新 | 60% | `state.json` 尚未產出 |
| 專利送件 PDF | 待修正 | 50% | 目前截圖顯示中文字型/編碼亂碼 |

## 已完成驗證

```text
[ai] topology_model metric-language-gateway-ai:latest: available
[memory] canonical_memory_refs: 2/2
[memory] metric_ledger_ref: available
[guard] readonly only; no SSH, no process kill, no auto-start
```

## 風險與修正

| 風險 | 等級 | 說明 | 建議 |
|---|---:|---|---|
| `11434` Ollama 裸露 | L2 | 目前 01 有 `*:11434` listener | 正式入口改為 `11435` 五維碼匝道器 |
| 01 匝道器目前是手動 nohup | L2 | 重開機後不一定自動恢復 | 改寫 systemd 或 login guard 為檢查後啟動 |
| Windows Ollama GUI 可能不能加自訂 header | L1 | 不能直接送五維碼 header | 使用設備 IP / 節點白名單映射五維碼 |
| 主記憶庫雙寫風險 | L2 | 01 與本機都可能有副本 | 01 為唯一權威，本機僅 cache，同步預設只 pull |
| PDF 中文亂碼 | L1 | 字型未嵌入或編碼錯誤 | 用可嵌入中文字型重新輸出 PDF |

## 下一步

1. 編寫 01 正確開機檔：只檢查，不亂殺進程，不無條件重啟。
2. 將 01 匝道器固定為受控 systemd service。
3. 將 Windows 前端連線設定導向 `100.71.224.18:11435`。
4. 刷新系統架構完成度網頁，加入 taiji01 權威記憶節點與 11435 匝道器。
5. 重新產出專利送件 PDF，處理中文字型嵌入。
