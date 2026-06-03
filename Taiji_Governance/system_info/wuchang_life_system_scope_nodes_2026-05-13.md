# wuchang.life 系統範圍與節點納管定義

版本：2026-05-13  
狀態：ACTIVE  
來源：使用者提供之 Tailscale Machines 截圖與既有 wuchang.life 治理政策  

## 核心定義

`wuchang.life` 為新北市三重區五常社區發展協會之組織數位網域。凡本網域所轄設備、容器、服務、公開摘要頁、VPN 節點與輔助算力節點，均納入五維度規 AI 治理總成服務範圍。

此處的「納入系統範圍」代表：

- 受到度規拓樸與匝道器保護。
- 可被列入節點健康檢查、能力摘要、audit 與拓樸圖。
- 可作為低敏、受控、可稽核的服務對象或算力候選節點。

但不代表：

- 可任意遠端控制。
- 可直接寫入 production。
- 可持有 secret、service account、OAuth token、會員明文或商業機密。
- 可繞過 Google 組織政策、Taiji Gateway、Five Metric Gate、人類決策與 audit。

## 已納管節點

| 節點 | Tailscale IP | 平台 | 節點類別 | 角色 | 預設寫入 |
|---|---:|---|---|---|---|
| taiji01 | 100.71.224.18 | Linux 6.8.0-111-generic | governance_host | governance / edge / memory / subnet router candidate | blocked |
| msi | 100.107.187.77 | Linux 6.6.87.2 WSL2 | developer_workstation | development / orchestration / temporal runtime | blocked |
| msi-win11-in | 100.105.82.28 | Windows 11 25H2 | windows_node | desktop UI / operator console | blocked |
| penguin | 100.111.139.7 | Linux ChromeOS container | linux_node | auxiliary dev / low-risk probe | blocked |
| drallion | 100.84.254.20 | Android 13 | mobile_device | least-privilege UI / confirmation | blocked |
| iphone-11 | 100.94.212.10 | iOS 26.4.2 | mobile_device | least-privilege UI / confirmation | blocked |
| v3-mix-edla-gl | 100.98.69.115 | Android 13 | mobile_device | least-privilege UI / confirmation | blocked |
| wuchang-us-free-node | 100.94.236.81 | Linux cloud amd64 | cloud_ephemeral_node | cloud metric auxiliary / ephemeral compute | blocked |
| wuchang-us-free-node-1 | 100.116.123.20 | Linux cloud amd64 | cloud_ephemeral_node | cloud metric auxiliary / ephemeral compute | blocked |
| wuchang-us-free-node-2 | 100.94.209.106 | Linux cloud amd64 | cloud_ephemeral_node | cloud metric auxiliary / ephemeral compute | blocked |
| wuchang-us-free-node-4 | 100.99.148.2 | Linux cloud amd64 | cloud_ephemeral_node | cloud metric auxiliary / ephemeral compute | blocked |

## wuchang.life 路由範圍

| host | 用途 | 暴露原則 |
|---|---|---|
| wuchang.life | 組織主域 | manual_dns_only |
| www.wuchang.life | 公開首頁 | public_summary_only |
| docs.wuchang.life | 無敏唯讀文件 | public_summary_only |
| business.wuchang.life | 商業協力雲摘要 | public_summary_only |
| property.wuchang.life | 物業管理雲摘要 | public_summary_only |
| fund.wuchang.life | 公益基金池科目與摘要 | public_summary_only |
| carbon.wuchang.life | ESG / 碳資料摘要 | public_summary_only |
| api.wuchang.life | Gateway API | vpn_only |
| odoo.wuchang.life | Odoo runtime | vpn_only |
| ai.wuchang.life | AI runtime | vpn_only |
| spatial.wuchang.life | 轄區圖與空間資料 | vpn_only |
| voice.wuchang.life | 語音 gateway | vpn_only |
| admin.wuchang.life | 人類管理入口 | vpn_only |

## 預設權限

所有納管節點預設：

```text
default_write_permission = blocked_until_gateway_authorized
```

可允許：

- health check
- capability summary
- non-sensitive metric packet
- hash-only audit
- local preview
- human-approved review packet

不可允許：

- direct SSH deployment by AI
- direct production DB write
- secret / token / service account transfer
- member plaintext cloud sync
- admin browser session automation
- payment / refund / manager override
- physical delete of audit / accounting / rollback records

## 生效結論

`wuchang.life` 之下的節點與容器，統一視為五常數位大陣服務對象與責任範圍；可見與不可見均須承擔治理責任。但任何寫入、執行、部署、金流、管理者設定與資料跨界，都必須經 Taiji Gateway / Five Metric Gate / Audit / Human Decision。
