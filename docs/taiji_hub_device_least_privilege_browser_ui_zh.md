# Taiji Hub 設備最小權限與 AI 瀏覽器 UI 設計

版本：0.1  
日期：2026-05-11  
狀態：設計中  
分類：非敏感設備與 UI 治理文件

## 目的

本文件定義各節點設備如何依最小權限原則開發應用，並將 AI 控制瀏覽器定位為「使用者介面」，不是管理員繞權工具。每個設備只能取得其任務所需的最小角色，所有跨設備、跨帳號、跨雲端或高風險操作都必須經 Gateway / Five Metric / Audit / Human Decision。

## 最小權限設備模型

| 設備/節點 | 角色 | 最小權限 | 禁止 |
| --- | --- | --- | --- |
| 開發者電腦 `msi` | 治理與開發基準 | repo patch、本地測試、audit、human decision | 無 gate 直接遠端部署 |
| `taiji01` VPN server 01 | subnet/router 節點 | VPN 路由與節點盤點 | 任意 router mutation |
| ASUS RT-BE86U | 網路邊界 | 受控 ACL/路由設計 | AI 直接登入管理面 |
| Odoo container | 社區/POS runtime | Odoo service role、localhost/Gateway access | database manager 暴露、明文會員外送 |
| PostgreSQL container | Odoo DB | 僅 Odoo 內部連線 | host 任意暴露 |
| 商米 POS | POS 終端 | POS kiosk role、Odoo-approved client | 管理員 shell、Google 私人資料 |
| 客顯機 02 | 顯示終端 | read-only display role | 交易/會員資料保存 |
| Voice Gateway | 語音 UI | localhost/VPN-approved voice endpoint | 雲端明文語音內容外送 |
| Device Resilience Adapter | 設備韌性 | health/status adapter | 遠端修改設備設定 |
| GPU Brain / Ollama | 本地模型算力 | local inference for redacted prompt | secret/context 明文持久化 |
| Open WebUI | AI 使用者 UI | 受控使用者介面 | `0.0.0.0` 未授權暴露、管理員越權 |
| Claw Safe | 本地工具 | sandboxed local tool | production mutation |

## AI 瀏覽器 UI 原則

AI 控制瀏覽器只能作為受限使用者介面：

- 使用最小權限帳號或 kiosk 帳號。
- 預設不登入超管、router admin、銀行、付款、自然人憑證或個人 Gmail。
- 不讀取密碼管理器、session cookie、token 或 private key。
- 不操作付款、轉帳、分潤、提款、憑證簽章或 production mutation。
- 若需要高權限頁面，只能停在 human review step，不能自動提交。
- 所有瀏覽器自動化必須保留 action manifest 與 redacted audit。

## AI 認知窗與權限合併規則

最高權限只可進入「認知窗」作為授權語意，不得直接變成執行權限。系統必須把最高授權降權到任務所需的最小分窗：

1. 認知窗接收最高授權意圖。
2. 度規拓樸匝道器分解為目標、風險、資料、節點與分窗。
3. 權限向量投影到最小可執行角色。
4. 先在沙盒驗證邏輯。
5. 紅隊觀點檢查越權、繞 gate、secret exposure、公益私有化與財務錯窗。
6. 修正後才以 patch 或 manifest 實作。

公式：最高授權語意 + 最小權限執行 + 沙盒驗證 + 紅隊修正 = 可治理自動化。

## 沙盒驗證流程

| 步驟 | 輸出 | 不可做 |
| --- | --- | --- |
| 設計邏輯 | design manifest | live execute |
| 沙盒掃描 | local-only report | secret readout |
| 紅隊檢查 | findings + line hash | 攻擊利用 |
| 藍隊修正 | patch proposal | production mutation |
| 本地驗證 | syntax/YAML/test | SSH/SCP |
| 治理落檔 | audit/progress/worklist | 明文憑證 |

## 新式大樓管理設備應用映射

使用者提供的專利/技術資料可作為新式大樓管理設備設計來源，但必須先本地抽取非敏感摘要，再轉成模組化設計：

- 門禁/訪客/公告/設備巡檢。
- POS/繳費/社區服務台。
- 客顯/看板/多媒體通知。
- 管委會設備 inventory。
- ESG/碳權/能源資料候選 mapping。
- 財務與基金池只進會計師精準分窗。

專利全文或未公開技術細節不得被送雲端；文件只保存功能映射、模組名稱、風險與非敏感摘要。
