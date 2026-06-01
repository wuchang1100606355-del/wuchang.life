# Taiji Hub 主要系統與負責人設備拓樸

版本：2026-05-11  
資料性質：節點拓樸與治理邊界  

## 主要系統所在

```text
taiji_01@taiji01
```

定位：

- Taiji Hub 主要系統所在節點
- Five-Metric Runtime / Gateway / Governance Runtime 之主要承載節點
- VPN / Tailscale 拓樸中應列入高信任但仍需審查之核心節點

治理要求：

- 不得繞過 Taiji Gateway
- 不得繞過 Five Metric Gate
- 不得繞過 Audit / Rollback
- 不得直接執行未審查 production mutation
- 應保留 SHA256 baseline
- 應保留節點 health / policy / audit 狀態

## 負責人設備

```text
taiji_admin@MSI:~/Taiji_Hub
```

定位：

- 資訊負責人設備工作區
- Linux 子系統原生工作區
- Taiji Hub 開發、測試、Runtime 驗證與封裝空間
- 本機負責人操作與審查窗口

治理要求：

- 可作為開發與 runtime 測試主機
- 可執行 local preflight、pytest、hash baseline
- 可啟動 localhost runtime
- 不得直接將高敏資料上傳雲端
- 不得直接修改 production Odoo/POS
- 不得輸出 secret / token / service account JSON

## Topology Mapping

| 節點 | 類型 | 角色 | 信任等級 | 風險 |
|---|---|---|---|---|
| `taiji_01@taiji01` | primary system node | 主要系統所在 | high-trust governed | 需 Gateway/Audit |
| `taiji_admin@MSI:~/Taiji_Hub` | owner workstation | 負責人設備 / 開發工作區 | high-trust governed | 不可外送 secret |

## Five-Metric Node Mapping

| Metric | `taiji_01@taiji01` | `taiji_admin@MSI` |
|---|---|---|
| Intent | 主要系統運行 | 開發、審查、封裝、驗證 |
| Resource | Runtime / Gateway / VPN / Audit | Linux workspace / test / local runtime |
| Time | 長期運行 / 維運 | 開發期 / 測試期 / 封裝期 |
| Authority | 受治理核心節點 | 資訊負責人授權設備 |
| Topology | primary node | owner workstation |

## L3 Metric Hazard

以下一律封鎖：

- 使用 `taiji_01@taiji01` 直接執行未審查 production mutation
- 使用 `taiji_admin@MSI` 直接輸出或上傳 secret
- 任何節點繞過 Gateway / Five Metric / Audit
- 將負責人設備資料夾作為無限制共享
- 將 C/D 磁碟高敏資料直接同步雲端

