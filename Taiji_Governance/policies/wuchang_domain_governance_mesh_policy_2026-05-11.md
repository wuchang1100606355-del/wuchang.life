# wuchang.life 組織網域治理網政策

版本：2026-05-11  
適用網域：wuchang.life  
組織主體：新北市三重區五常社區發展協會  
數位代表號：admin@wuchang.life  

## 核心條款

凡本網域所轄設備，均為本會五維度規 AI 治理總成之服務對象。

五維度規 AI 治理總成包含：

- 度規拓樸
- 度規轉譯匝道器
- Taiji Gateway
- Five Metric Gate
- Audit Runtime
- Replay / Deadbox Governance
- Human Decision Boundary

凡本網域所轄設備，均受本會五常數位大陣保護及算力支援。

## 權限邊界

「服務對象」不等於「可任意控制」。

所有設備與容器之可見、不可見、可讀、可寫、可調用，須受以下機制共同治理：

- Google Workspace 組織政策
- wuchang.life 網域身份
- 群組 / 角色 / OU 權限分窗
- Taiji Gateway
- Five Metric Gate
- Audit / Rollback
- 公益度規

## 設備責任

無論設備是否對一般使用者可見，只要承擔本系統之任一功能，即須納入治理責任：

- 運算
- 儲存
- 轉譯
- 路由
- 日誌
- 審查
- POS/Odoo 服務
- 語音 / 瀏覽器介面
- 組織雲端 staging
- 本地封存

## 五維度規調用

每一設備或容器被調用時，必須映射為：

```text
Intent Metric
Resource Metric
Time Metric
Authority Metric
Topology Metric
```

並產生可稽核之 TensorPacket / audit record / rollback reference。

## 分散式算力支援

本會五常數位大陣可對合規節點提供：

- 本地運算支援
- 分散式任務協調
- 低風險自動化
- 文件與 schema 產生
- Runtime 健康檢查
- Audit / SHA256 baseline
- 無敏雲端唯讀 staging

不得提供：

- 未審查 secret 讀取
- 未審查會員明文處理
- 未審查 production mutation
- 未審查 payment / refund / manager override
- 繞過 Gateway 的高權限執行

## L3 Metric Hazard

以下一律封鎖：

- 將「本網域所轄設備」解釋為可任意遠端控制
- 不可見設備私自處理會員明文、secret 或營業機密
- 設備繞過 Google 組織政策與 Taiji Gateway
- 容器繞過 Five Metric Gate 或 Audit
- 任何節點刪除 rollback / SHA256 / audit
- 將公益算力轉為私人利益

## 最終原則

```text
本網域所轄設備皆為本會五維度規 AI 治理總成服務對象。
設備受五常數位大陣保護及算力支援。
服務不等於任意控制。
不可見不等於無責任。
所有節點都必須受度規、拓樸、匝道器、Audit 與公益目的約束。
```

