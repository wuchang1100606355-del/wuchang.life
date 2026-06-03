# 分散式算力架構邊界政策

版本：2026-05-11  
適用網域：wuchang.life  
組織主體：新北市三重區五常社區發展協會  
階段：先打通分散式算力架構；算力流動細節容後再議  

## 核心原則

本階段目標是先打通分散式算力架構之拓樸、節點登記、健康檢查、Gateway、Audit 與邊界，不急於定義完整算力流動調度策略。

正式原則：

```text
先打通架構。
先建立邊界。
先確認節點責任。
算力如何流動，容後再議。
```

## 容器區域與會員設備邊界

本會運算服務之容器區域，與會員設備之間，必須設立嚴密界線。

允許：

- 算力可用性訊號
- 健康狀態
- 任務能力摘要
- 經 Gateway 轉譯後的低敏任務封包
- hash-only / metadata-only audit
- replay-safe execution packet

禁止：

- 會員設備直接進入容器內部網路
- 容器直接讀取會員設備個資
- 會員設備取得容器 secret
- 容器取得會員設備 private data
- 未經授權的遠端控制
- 會員設備被當成 production server
- 會員設備被當成資料庫節點
- 會員設備與本會高權限容器共享 credential

## 邊界定義

| 區域 | 定位 | 可交換內容 | 不可交換內容 |
|---|---|---|---|
| 本會運算服務容器區 | Taiji Gateway / Runtime / Audit / POS/Odoo 服務 | TensorPacket、任務摘要、audit hash、健康狀態 | 會員明文、secret、未審查資料庫 |
| 會員設備區 | 使用者端、顯示端、低權限互動端 | UI 請求、狀態回報、低敏算力訊號 | 容器 admin 權限、service account、內部 DB |
| Gateway Boundary | 拓樸與匝道器 | 轉譯後封包、政策判斷 | raw production mutation |
| Audit Boundary | 稽核與追溯 | hash、時間、節點、決策 | secret 明文、會員完整資料 |

## 算力流動的暫定模型

本階段只允許以下抽象流：

```text
Member Device
→ request capability / UI action
→ Taiji Gateway
→ Five Metric Gate
→ Container Compute Service
→ Result Summary
→ Audit
→ Member Device
```

不允許：

```text
Member Device
→ direct container shell
```

```text
Container Service
→ read member device private files
```

```text
Member Device
→ production DB write
```

## 五維度規映射

每次跨邊界算力協作，必須標記：

```json
{
  "intent_metric": "compute_assist_or_service_interaction",
  "resource_metric": "bounded_compute",
  "time_metric": "limited_execution_window",
  "authority_metric": "least_privilege_member_boundary",
  "topology_metric": "gateway_mediated_container_to_member_device",
  "member_plaintext_access": false,
  "secret_access": false,
  "direct_remote_control": false,
  "audit_required": true
}
```

## 會員設備保護

會員設備在本系統中應視為：

- 服務互動端
- 最小權限使用端
- 顯示 / 輸入 / 確認端
- 算力可用性訊號端

會員設備不應視為：

- 本會資料庫
- 高權限運算容器
- secret store
- production admin node
- 可被任意遠端控制的設備

## L3 Metric Hazard

以下一律封鎖：

- 會員設備直接連入本會容器內網
- 容器直接讀取會員設備私有檔案
- 會員設備取得 service account、API key、token、private key
- 會員設備直接寫入 Odoo/POS production
- 容器透過會員設備繞過 Gateway
- 將會員設備當作無審查算力節點
- 算力流動夾帶會員明文或營業機密

## 下一階段待議

以下事項容後再議，不在本階段直接啟用：

- 算力計價
- 算力排程
- 任務分派優先級
- 節點貢獻量化
- 會員設備是否參與低風險邊緣運算
- GPU / CPU / storage quota
- 分散式任務回收與補償

## 最終原則

```text
本階段先打通分散式算力架構，不急於定義算力流動。
本會容器區與會員設備區必須嚴格隔離。
兩者只允許經 Gateway 與 Five Metric Gate 的受控算力協作。
算力可以流動，權限、secret、會員明文不可流動。
```

