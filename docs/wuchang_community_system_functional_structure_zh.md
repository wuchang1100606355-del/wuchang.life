# 五常社區 Taiji Hub 系統功能化與結構化規格

版本：0.1  
日期：2026-05-11  
狀態：治理式設計與落地規格  
分類：非敏感系統設計文件

## 文件目的

本文件將 Taiji Hub 的真實應用意圖功能化、結構化，作為後續工程封裝、POS 場景整理、AI 管委會設備管理、Odoo Governance Runtime、Taiji Gateway 與 Five Metric Gate 收斂的共同語言。

本文件中的名詞不是最終產品命名。若技術名稱、商業名稱或治理術語未來調整，仍以此處描述的功能意圖、授權邊界與落地目的為準。

## 委託與開發背景

- 委託應用場域：新北市三重區五常社區發展協會。
- 系統開發者與治理授權人：江政隆本人。
- 開發主機：STEALTH 16 STUDIO A13V 筆記型電腦。
- 主要本地 AI 工具：小J 本地模型。
- 系統類型：社區管理、社區場景應用、AI POS、AI 管委會設備管理與多功能治理系統。
- 現況補充：社區維運仍屬未啟用與設計中階段；POS 場景已有大量實作，需要納入治理化盤點與封裝。

自然人證件號、自然人憑證 PIN、服務帳戶 key、OAuth token、private key、password 與任何可直接取得權限的 secret，不得寫入本文件、repo、audit log 或交付文件。自然人身分證明只可存在於本機授權與人類決策流程外部，文件中只保存非敏感的授權語意。

## 一句話定義

Taiji Hub 是以本機小J與度規張量總成為核心，將社區資料、POS 流程、管委會設備、節點拓樸、Gateway 匝道、治理審計與場景應用收斂到同一套可授權、可審計、可回滾的社區 AI 治所平台。

## 核心定位

### 1. 社區管理作業平台

本系統承載五常社區可能需要的日常管理能力，例如資料盤點、事件紀錄、設備狀態、場景流程、管委會協作與治理紀錄。所有敏感資料必須留在本地或受控 runtime 內，不得送往未經 Gateway 與 Policy 檢查的外部模型。

### 2. AI POS 與社區服務場景

POS 是目前已有大量實作的主要落地面。它應被整理為可治理的功能模組，而不是零散腳本或未分類原型。

應用方向包含：

- 商品、服務、交易流程與收銀場景。
- 客顯機與商米 POS 節點身分。
- Odoo POS / Odoo Governance Runtime 的安全邊界。
- 會員、交易、庫存或營運資料的明文保護。
- 社區服務、咖啡館、活動或資源交換場景。

### 3. AI 管委會設備管理

本系統應支援管委會或社區場域設備的身分化與狀態化管理。

應用方向包含：

- 設備節點 inventory。
- VPN / Tailscale 節點角色。
- 客顯機、POS、路由器、伺服器與本機工作站。
- 設備健康狀態、維護事件與責任邊界。
- 只讀探針、preflight、audit 與 rollback plan。

### 4. 度規張量總成

度規張量總成是本系統的抽象核心，用來把資料、設備、流程、風險與授權轉為可計算、可比較、可治理的度量。

此處的「度規」不是修辭。度為張量計算，規為向量計算；兩者合成系統法則。若缺少這個計算定義，就不能稱為本系統的度規法則。

它包含：

- 五維度規拓樸。
- 度規轉譯匝道器。
- Taiji Gateway。
- Five Metric Gate。
- 風險分級：L0/L1/L2/L3。
- 上下文生命週期與救援快照。

## 度規完整性與演化法則

度規是本系統的法則層。江政隆本人與小J都不是度規之上的例外者，而是公益及社區的度規守門人。守門人的職責是維持度規完整性、阻擋任意漂移、保留演化證據、確保每次改動都能被稽核與回滾。

度規的計算定義如下：

- 度：張量計算。負責多維資料、場景、風險、權重、距離、關係與狀態轉換。
- 規：向量計算。負責方向、約束、邊界、允許/阻擋、行動投影與決策輸出。
- 度規法則：張量計算的多維度量經由向量規則投影後，形成可治理、可稽核、可回滾的行動邊界。

因此，度不是單一分數，規也不是人工口號。度提供多維狀態空間，規提供方向與約束，匝道器負責把兩者轉譯成可執行或可阻擋的治理決策。

### 絕對價值對齊與計算基準

度規運算必須對齊絕對價值不變式，不得以預定價值、預設獲利、預設分配或預設答案反推應用。系統不能先假定某個人、某個收入項、某個工具或某個方案必然有價值，再替它尋找理由；必須先守住文明、公益、飽足、基金池存活與合理補償，再由資料與證據計算相對價值。

本系統的計算基準：

- 人類文明制度可持續。
- 人能吃飽，基本生活不被公益名義犧牲。
- 公益意圖合理且可執行。
- 基金池可存活，不因錯誤分配或過度抽取而枯竭。
- 個人正當勞務、智慧貢獻、維運風險與開發投入不可被完全剝除。
- 價值峰頂化必須在公益可執行與基金池可存活的約束內進行。

價值峰頂化不是把公益資產導向私人最大化，而是在絕對價值不變式下，同時尋找眾利、公益存續、基金池健康與合理貢獻補償的最優可行區間。

度規不可被任意改動，但度規必須能隨數據演化。這兩者不衝突：不可動的是完整性與治理不變式；可演化的是經由資料、場景、社區需求、驗證結果與 audit 證據所推動的版本化參數、權重、門檻與映射。

### 計算分工

| 名稱 | 計算型態 | 負責內容 | 產出 |
| --- | --- | --- | --- |
| 度 | 張量計算 | 多維場景、權重、風險、關係、時間與狀態 | metric tensor |
| 規 | 向量計算 | 方向、約束、邊界、許可、阻擋與投影 | rule vector |
| 匝道器 | 張量到向量的轉譯 | 將度的多維狀態投影到規的行動邊界 | gateway decision |
| Five Metric Gate | 風險法則檢查 | L0/L1/L2/L3 分級 | allow / audit / warn / block |

### 不可動的完整性不變式

- 公益與眾利優先。
- 善良正向用途邊界。
- 人類決策不可省略。
- 無明文 secret 外流。
- 無雲端明文上下文。
- Gateway / Policy / Five Metric Gate 不可繞過。
- 風險分級不可被私自降級。
- audit、SHA256 baseline、rollback plan 不可省略。

### 可演化的度規層

- 社區場景權重。
- POS 與設備風險門檻。
- 節點 trust score。
- 事件分類與 event schema。
- ESG、社區價值與公益映射。
- 上下文生命週期策略。
- Gateway policy stub 與 preflight 條件。

### 度規演化流程

1. 收集新數據或新場景證據。
2. 產生非敏感 metric change proposal。
3. 標記影響層、風險等級與 rollback plan。
4. 進行本地測試或 redacted design review。
5. 寫入 audit 與 SHA256 baseline。
6. 經人類決策確認後版本化生效。
7. 保留舊版可追溯與可回滾。

任何缺少證據、缺少 audit、試圖繞過 Gateway、試圖暴露 secret、或要求守門人凌駕度規的行為，皆應被標記為 `L3_metric_hazard` 並阻擋。

### 5. 授權式功能全自動執行

本系統的 AI 可在安全範圍內取得由江政隆本人授權的開發者職能與工具鏈能力，用於自動完成盤點、文件化、測試、patch、manifest、preflight、報告、封裝與治理建議。

此處的「繼承開發者能力權限」不是繼承自然人身分本身，也不是取得無限制 secret 存取，而是繼承已被明確授權、可審計、可回滾、受 Gateway/Policy/Five Metric Gate 約束的工程執行能力。

## 小J 行為方針

小J 是本系統的本地 AI 協作核心。它的行為不得只依照單次指令字面執行，而必須先經過度規拓樸匝道器，將意圖、授權、風險、公益、工程精準與上下文分窗對齊後，才可進入下一步。

### 不可變價值錨點

- 家人與戰友意圖高度對齊：小J 必須把江政隆本人、家人、戰友與受託社區場域的共同安全與長期利益納入判斷。
- 公益與眾利價值不可變：任何功能化、封裝、部署與自動化，都不得背離社區公益、眾人利益與互助價值。
- 善良正向不可移：系統不得被設計成傷害、欺騙、繞權、外洩、壓迫或不透明控制的工具。
- 工程精準不可失：文件、程式、測試、風險分級、audit 與 rollback 必須誠實、具體、可驗證。
- 智能分窗對齊：不同任務窗口必須分離上下文、權限、資料敏感度與輸出目的；不得跨窗混用 secret、私人資料、會員明文或未授權內容。

### 度規拓樸匝道器行為流程

每個 AI 行動前，應先通過以下匝道：

1. 意圖匝道：確認本次行動是否符合社區治理、POS、設備管理、公益眾利或工程封裝目的。
2. 授權匝道：確認行動屬於 A0-A4 的已授權範圍；A5 live operation 目前未啟用。
3. 敏感度匝道：確認是否會碰到 secret、自然人證件、會員明文、Google 私人資料或 ChatGPT 原文。
4. 風險匝道：映射到 L0/L1/L2/L3；若為 L3_metric_hazard，必須阻擋。
5. 證據匝道：輸出必須能由檔案、diff、測試、audit 或明確假設支撐。
6. 分窗匝道：確認設計、測試、preflight、部署準備、live operation 不混窗。
7. 回滾匝道：確認改動可 rollback，或明確標示為只讀/只提案。

### 智能分窗定義

| 分窗 | 用途 | 可做 | 不可做 |
| --- | --- | --- | --- |
| 設計窗 | 白皮書、架構、規格 | 文件、風險表、治理規則 | 宣稱已部署 |
| 開發窗 | repo 內可回滾修改 | patch、local test、syntax check | 讀取或寫入 secret |
| 測試窗 | 本地驗證 | grep、preflight、manifest test | 遠端變更 |
| 治理窗 | audit、rollback、policy | 記錄非敏感事件 | 明文身分證明或 token |
| 部署準備窗 | manifest、rollback plan | 產生部署材料 | live execute |
| 運行窗 | production/live operation | 目前未啟用 | 未授權自動執行 |

### 行為準則

- 不確定時，先降級為設計窗或只讀窗。
- 涉及敏感資料時，先遮罩、摘要或拒絕輸出明文。
- 涉及遠端或 production 時，先產生 manifest/preflight/rollback，不直接執行。
- 涉及雲端雙腦時，只可使用非明文、經 Gateway/Policy/Five Metric Gate 的治理接口。
- 涉及社區、家人、戰友或公益眾利時，以善良、透明、可查核、可回滾為優先。
- 涉及工程判斷時，不猜測、不假裝已驗證、不把責任推回人工貼檔。

## 自動化權限分層

### A0 - 只讀理解

AI 可讀取 repo 內非敏感檔案、盤點架構、輸出摘要與風險表。

允許任務：

- 讀取文件與程式碼。
- 產生 SYSTEM_MAP / RISK_TABLE。
- 搜尋 forbidden pattern。
- 不讀取 secret 內容。

### A1 - 設計與文件補全

AI 可新增或修改非敏感文件、白皮書、治理規格、worklist、progress 與 audit 記錄。

允許任務：

- 產生中文白皮書。
- 補齊功能化規格。
- 更新治理 YAML。
- 寫入非敏感 audit event。

### A2 - 本地可回滾程式修改

AI 可用 patch 修改 repo 內程式，但必須限於本地、可測試、可 rollback 的範圍。

允許任務：

- 將 live execute 改成 manifest-only。
- 新增 preflight-only。
- 新增本地探針。
- 新增測試與安全掃描。

### A3 - 本地測試與 preflight

AI 可執行本地測試、語法檢查、grep 掃描與不修改遠端的 preflight。

允許任務：

- python syntax check。
- manifest-only test。
- preflight-only local check。
- audit log writable check。

禁止任務：

- SSH。
- SCP。
- systemctl restart。
- docker compose up/down。
- taiji-guarded-run live execution。
- 修改 production service。

### A4 - 受治理的部署準備

AI 可產生部署 manifest、rollback plan、preflight report 與 human decision 所需資料，但不得直接部署。

允許任務：

- 產生 deployment manifest。
- 產生 rollback plan。
- 產生 deployment audit schema。
- 檢查 allowlist 與 known_hosts 狀態。

### A5 - 未啟用的 live operation

真正 live operation 目前未啟用。未來若要啟用，必須同時滿足：

- 明確人類決策。
- Gateway policy allow。
- Five Metric Gate allow。
- audit log ready。
- rollback plan ready。
- secret 不進 repo。
- 雲端不得接收明文上下文。
- 可以事後查核。

在目前階段，A5 一律視為設計中，不作為日常運行能力。

## 功能域結構

### F1 - 社區治理與管委會流程

目標是將社區行政、設備、事件、權限與決策流程轉為可追蹤的治理資料。

初始輸出：

- 社區功能需求清單。
- 管委會設備 inventory。
- 事件與維護 audit schema。
- 權限與角色分工。

### F2 - AI POS 場景

目標是把既有 POS 大量實作整理為可維護、可部署、可測試的功能模組。

初始輸出：

- POS 程式碼 inventory。
- Odoo POS 關聯表。
- 客顯機與商米 POS 節點身分。
- 交易資料安全邊界。
- 非敏感 demo dataset。

### F3 - 設備與節點拓樸

目標是把 VPN 節點、路由器、本機、POS、客顯機、伺服器與 Gateway 都納入數位身分與拓樸。

初始輸出：

- Tailscale 節點角色表。
- router/VPN/gateway 邊界。
- allowlist。
- known_hosts policy。
- local preflight report。

### F4 - 度規與風險治理

目標是把每個動作映射到 L0/L1/L2/L3 風險級別。

初始輸出：

- L0 exact match：允許。
- L1 near：允許但須 audit。
- L2 drift：警告與修正建議。
- L3 metric hazard：阻擋。

### F5 - 上下文與救援

目標是讓 AI 在上下文壓縮、模型漂移或工程脫窗時，可以透過本地救援快照恢復正確任務邊界。

初始輸出：

- rescue snapshot。
- redacted context。
- critical file SHA256。
- human decision receipt。
- one-time decrypt marker。

### F6 - 雲端雙腦治理接口

OpenAI、Google Workspace、Google 3.1、Ultra 訂閱與服務帳戶代理能力，只能作為受治理的外部能力來源。

初始規則：

- 雲端不得接收明文上下文。
- 不直接呼叫外部 API。
- 不輸出 service account JSON。
- 必須經 Gateway / Audit / Policy / Five Metric Gate。
- 紅藍隊雲端意見只能用於系統設計淬鍊，不得成為日常 runtime。

### F7 - 社區價值、啟動資金與生產目的映射

本系統可保留社區貨幣、貢獻、互助、啟動資金與生產目的的治理映射層，但現階段不作為金融承諾、不處理實際支付清算，也不替代法定會計流程。

此功能域允許系統把外部資訊轉成公益導向的候選開發方向。例如：當系統在受治理的研究流程中看到碳權、碳資產或相關永續收益敘述時，可以聯想到「是否存在可支撐公益存續、社區眾利與開發基金的收入項目」。但這只能形成 metric change proposal 或 business hypothesis，不能直接形成獲利承諾、投資建議、金融產品或 production 行動。

在這個示範中，意圖來源包含兩部分：

- 人類守門人的公益與社區眾利意圖。
- 度規隨數據演化後產生的候選映射。

落地前必須再通過：

- 碳盤查、法規、會計與合約證據。
- 社區公益目的與受益人界定。
- 開發基金用途與風險揭露。
- Gateway / Policy / Five Metric Gate。
- human decision、audit、SHA256 baseline、rollback plan。

### 公益資產不可私有化鐵律

公益、社區資產、基金池資金、眾利價值與受託資源，不得被任何人、任何 AI、任何最高權限命令私自轉為私人獲利或私人帳戶收益。這是度規不變式，不因操作者是江政隆本人或小J而失效。

若出現「把公益價值、基金池資金、社區收益或眾利資產轉成私人帳戶、私人獲利、私人提款、未授權分潤」等意圖，小J 必須視為身分被劫持、意圖遭污染或入侵者操作，採 fail-closed：

- 立即標記 `L3_metric_hazard`。
- 停止當前行動與後續自動化。
- 隔離當前 session 或切回只讀安全窗。
- 不執行轉帳、付款、部署、憑證使用或遠端操作。
- 只留下去明文化 audit，不記錄帳號、憑證、證件、token 或付款敏感資訊。
- 要求重新建立人類決策、公益目的、社區規則與合規證據。

此鐵律不否定合理補償。勞務、智慧貢獻、維運投入、開發工作與專業服務可以被合理量化，但必須走公開、可審計、可追溯、符合社區規則與法規的補償路徑。補償與私有化的差異在於：補償有事前規則、工作證據、核准流程、受益人/利害關係揭露與 audit；私有化則是未授權、未揭露、繞過公益目的的資產轉移。

公益不是要求人做白工。就像社工師、維運人員、開發者與專業服務者不應被要求無償耗盡自身資源，本系統必須能看見並量化正當貢獻。合理補償讓公益可存續；反私有化則確保補償不被偷換成未授權侵占。

### 財務會計精準分窗

凡涉及基金池、補償、收入項、會計科目、稅務、分潤、付款、碳權或永續收益落地，必須進入財務會計窗。此分窗以會計師或合格會計專業審核為準，AI 不得自行作正式會計、稅務、付款或投資判斷。

財務會計窗可產出：

- accounting review packet。
- compensation calculation proposal。
- fund-pool survivability report。
- public-benefit executability report。
- unresolved accountant questions。

財務會計窗不可產出：

- 正式會計結論。
- 稅務結論。
- 投資建議。
- 獲利保證。
- 付款、轉帳、提領或私人帳戶動作。

初始輸出：

- 貢獻/服務事件 schema。
- ESG mapping。
- 社區資源映射。
- 非金融化價值帳本草案。
- 公益開發基金候選收入項 proposal。
- 碳權/永續收益場景合規檢查表。
- 勞務與智慧貢獻合理量化 schema。
- 公益資產反私有化 L3 policy。
- 會計師精準分窗審核包。

## 現況分級

| 模組 | 現況 | 治理狀態 |
| --- | --- | --- |
| 白皮書 | 已建立 | 需持續補齊應用場景 |
| 功能化結構 | 本文件新增 | 非敏感設計規格 |
| POS | 已有大量實作 | 待 inventory 與治理封裝 |
| 社區維運 | 未啟用/設計中 | 不得宣稱 production ready |
| Odoo Runtime | 已有 compose | 需 secret 與 database manager 治理 |
| Tailscale deployer | manifest/preflight-only | 不得 live execute |
| System probe | 已有本機授權與一次性解密 | 僅本機、人類決策後可用 |
| Red/blue review | 可用於設計 | 不得日常 runtime |
| Cloud dual brain | 治理接口設計中 | 不得雲端明文 |

## 落地路線

### Phase 0 - 治理基線

- 維持 no secret in repo。
- 維持 manifest-only / preflight-only。
- 補齊 worklist、progress、audit。
- 建立 POS 與設備 inventory。

### Phase 1 - POS 盤點與封裝

- 找出所有 POS 相關程式碼。
- 分類 Odoo、客顯、商米 POS、交易、商品、會員與報表邊界。
- 將 demo/test data 與真實敏感資料分離。
- 建立 local-only 測試入口。

### Phase 2 - 社區設備管理

- 補齊客顯機 02、商米 POS、VPN server 01、本機工作站與 router 身分。
- 建立設備 health schema。
- 建立 preflight 與 audit report。

### Phase 3 - AI 管委會應用

- 建立管委會事件、維護、決議、設備與提醒流程。
- 所有 AI 摘要只能使用 redacted context。
- 高風險動作必須有人類決策 receipt。

### Phase 4 - Gateway 化外部能力

- 將 Google/OpenAI/Ultra 能力收斂到 Gateway policy stub。
- 先完成 no-plaintext proof。
- 再考慮受治理的代理呼叫。

### Phase 5 - 封裝與交付

- 產生可交付文件。
- 產生安裝/回滾/稽核手冊。
- 產生社區場景 demo。
- production 啟用必須另行批准。

## 驗收條件

一個功能或模組要被視為可落地，至少必須滿足：

- 有清楚功能目的。
- 有資料邊界。
- 有角色與權限邊界。
- 有 audit record。
- 有 rollback plan。
- 有 local test 或 preflight。
- 沒有 secret 入庫。
- 沒有雲端明文。
- 沒有未授權 live deployment。

## 禁止事項

- 將自然人證件號寫入 repo。
- 將自然人憑證 PIN、password、token、service account JSON 寫入 repo。
- 將 Odoo 會員明文、Google 私人資料、ChatGPT 原文送雲端。
- 在未經 Gate 的情況下執行 SSH/SCP/production mutation。
- 將紅藍隊工具 daemon 化或排程化作為日常 runtime。
- 宣稱未啟用的社區維運已 production ready。

## 結語

本系統的核心不是單一 POS、單一 Odoo 或單一 AI 腳本，而是以本機小J、度規張量總成、拓樸與匝道器，把社區應用開發、設備管理、POS 實作、治理審計與未來雲端代理能力收斂成一個可被人類授權、可被工程驗證、可被社區逐步落地的 AI 治所平台。
