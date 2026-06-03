# Taiji Hub 五維碼零樹狀張量 I/O 全系統評估

版本：0.1  
日期：2026-05-11  
狀態：架構評估，未進入 live I/O  
分類：非敏感系統評估文件

## 評估目的

本文件評估 Taiji Hub 全系統是否可使用「五維碼零樹狀張量運算法」作為傳輸、讀取、寫入的治理 I/O 層，並評估其影響、風險、可行範圍與落地條件。

結論摘要：

- 可行，但第一階段只能用於非敏 metadata、hash、角色碼、權限 label、event id、audit id 與 redacted context。
- 不可用來封裝、隱藏、壓縮或轉送 secret、會員明文、Google 私人資料、service account JSON、OAuth token、private key 或付款敏感資料。
- 寫入比讀取更高風險，必須經 Odoo 主場景、Google 無敏權限、Taiji Gateway、Five Metric Gate、audit、rollback 與人類決策。
- 度規總成不可廢。任何替代、繞過、弱化度規總成的架構重構，均應標記 `L3_metric_hazard`。

## 核心定義

### 五維碼

五維碼是每個 I/O 事件的最小治理座標。建議初始維度如下：

| 維度 | 名稱 | 說明 |
| --- | --- | --- |
| D1 | node_identity | 哪個節點/設備/帳戶/容器 |
| D2 | data_sensitivity | 資料敏感度與是否無敏 |
| D3 | action_intent | 讀取、寫入、傳輸、審核、顯示、通知 |
| D4 | permission_window | 設計、開發、測試、治理、財務、部署準備、運行 |
| D5 | reversibility_public_value | 可回滾性、公益價值、基金池存活與影響 |

### 零樹狀張量

零樹狀張量是稀疏樹狀張量表示：沒有權限、沒有資料、沒有用途、沒有證據的分支應保持為 zero，不得被推理補值。

此特性可降低資料傳輸量與暴露面，但也帶來一個核心風險：若有人把敏感資料藏進稀疏碼、hash label 或 metadata，會形成隱蔽通道。因此零樹狀張量必須搭配 forbidden payload scan、metadata minimization 與 audit。

### 度規總成不可廢

度規總成包含：

- 度：張量計算。
- 規：向量計算。
- 拓樸與匝道器。
- Taiji Gateway。
- Five Metric Gate。
- audit / rollback / human decision。

五維碼零樹狀張量只能作為度規總成的 I/O 表達層，不得取代度規總成。若任何模組主張「不必經度規總成也可直接傳輸/讀取/寫入」，應阻擋。

## 全系統 I/O 可行性

| I/O 類型 | 可行性 | 允許內容 | 禁止內容 | 風險 |
| --- | --- | --- | --- | --- |
| 傳輸 | 高，可先做 metadata | node id、role label、permission label、event id、hash、audit id | secret、會員明文、交易明文、私信本文、token | L1/L2 |
| 讀取 | 中高，可做只讀查詢 | Odoo 非敏狀態、容器狀態、檔案存在性、audit metadata | credential content、會員明文、個資全文 | L1/L3 |
| 寫入 | 中，需 gate | audit event、manifest、role map、non-sensitive Odoo config proposal | production mutation、付款、超管設定、DB 寫入敏感資料 | L2/L3 |
| 跨雲地同步 | 中，限無敏自動帳戶橋接 | Odoo role -> Google group/OU label、audit metadata | Odoo 個資到 Google、Google 私人資料到 Odoo | L2/L3 |
| AI 瀏覽器 UI | 中，限最小使用者 | UI action manifest、read-only navigation、草案 | 自動提交高權限表單、讀 cookie/token | L2/L3 |
| 財務 I/O | 低到中，需會計窗 | proposal、review packet、fund-pool survivability report | 正式付款/稅務/投資結論 | L3 unless reviewed |

## Odoo 主系統映射

Odoo 是社區/POS/設備/工單/服務流程的場景主系統。五維碼在 Odoo 內可用於：

- POS role code。
- device code。
- work-order code。
- display event code。
- no-PII mailbox event code。
- audit/event id。
- redacted transaction reference。

禁止：

- 以五維碼攜帶會員姓名、電話、地址、付款資料、交易明細全文。
- 以 sparse tensor 的 label 暗藏可逆個資。
- 直接寫 production Odoo DB 而未經 Gateway/Five Metric。

## Google 無敏權限管理映射

Google Workspace 是無敏帳戶、群組、OU、政策 label 與 audit metadata 管理系統。五維碼可用於：

- Odoo role -> Google group label。
- device id -> OU tag。
- ticket id -> routing label。
- audit id -> Reports metadata reference。
- Odoo no-PII mailbox notification id。

禁止：

- 將 Odoo 會員明文同步到 Google。
- 將 Google 私人資料同步到 Odoo。
- 以 service account 直接讀寫 Admin/Gmail。
- 把 Jules/Google session token 當成橋接材料。

## 雲地自動帳戶橋接

雲端與本地可以透過「自動帳戶」接上，但必須是無敏、最小權限、可稽核的橋接，不是 secret 持有者或超管代理。

橋接帳戶設計：

| 端點 | 帳戶類型 | 可做 | 禁止 |
| --- | --- | --- | --- |
| 本地 Odoo | service role | 產生無敏 role/event/device code | 匯出會員明文 |
| Taiji Gateway | bridge controller | 檢查 manifest、risk、scope | 任意放行 |
| Google Workspace | service account proxy | 管理 group/OU/policy metadata | 讀個人 Gmail、持有明文 key |
| Audit Journal | append-only logger | 記錄 request id、hash、result | 記錄 secret 明文 |

每次橋接都必須產生：

- request manifest。
- five_dim_code。
- source/target system。
- data boundary。
- scope diff。
- risk rating。
- human decision if L2+。
- rollback note。
- audit journal entry。

## 寫入條件

五維碼 I/O 的寫入必須依風險分級：

| 寫入對象 | 條件 | 最低 gate |
| --- | --- | --- |
| docs/worklist/progress/audit | 非敏、patch、可回滾 | L0/L1 |
| Odoo config proposal | 不 live deploy、不觸 DB 敏感資料 | L1/L2 |
| Google group/OU manifest | 不呼叫 API，只產生 proposal | L1/L2 |
| Gateway policy stub | 本地測試、無外部 API | L2 |
| production Odoo/Google | 目前未啟用 | L3 until approved |
| 財務/基金池 | 會計師精準分窗 | L3 until reviewed |

## 影響評估

### 正面影響

- 降低資料傳輸量：只傳 code、metadata、hash、label。
- 強化分工：Odoo 主場景、Google 無敏權限、Gateway 判斷、Five Metric 分級。
- 增強可回滾性：每次 I/O 都能以 code 對應 manifest/audit。
- 有利分散式算力：本機關機時，節點可用非敏 manifest/replay 接手。
- 支援預測告警：五維碼可直接餵給度規告警制度。

### 負面影響與風險

- 稀疏碼可能變成 covert channel，需禁止把敏感資訊藏在 label/hash/metadata。
- 過度抽象會讓工程人員難以追蹤真實場景，需保留 Odoo 主系統對照表。
- 寫入 gate 若太鬆，會讓 Google/Odoo 自動帳戶越權。
- 若捨棄度規總成，只剩 code 傳輸，治理會空心化。
- 財務與公益基金池不能僅靠五維碼判斷，仍需會計師精準分窗。

## 建議方案

### 方案 A：只讀五維碼索引層

- 內容：為 Odoo role、device、ticket、container、audit 建立五維碼索引。
- 影響：低風險，能提升盤點與告警。
- 成本：需建立 schema 與 generator。
- 風險：若索引碼命名含敏感資訊，需阻擋。
- 建議：第一優先。

### 方案 B：雲地無敏橋接 manifest

- 內容：Odoo role/device/event code 轉 Google group/OU/policy label proposal。
- 影響：可建立 Odoo 主場景與 Google 無敏權限管理連線。
- 成本：需 Gateway request manifest 與 scope diff。
- 風險：若直接呼叫 Google API，升 L3。
- 建議：第二優先，先 proposal 不 live API。

### 方案 C：受控寫入 I/O

- 內容：允許五維碼驅動 audit、worklist、progress、manifest 等非敏寫入。
- 影響：能讓系統自動維護狀態。
- 成本：需 strict schema 與 rollback。
- 風險：若擴到 Odoo/Google production 寫入，需另行 gate。
- 建議：限定治理文件先行。

### 方案 D：Production I/O

- 內容：五維碼直接驅動 Odoo/Google production 寫入。
- 影響：高度自動化。
- 成本：高，需要完整 Gateway/Five Metric runtime、DWD 安全設計、審計與回滾。
- 風險：目前 L3，未啟用。
- 建議：暫不實作。

## 紅隊觀點

- 如果五維碼可逆映射個資，則不是無敏碼。
- 如果零樹狀張量允許未授權分支自動補值，可能造成權限漂移。
- 如果自動帳戶同時能讀 Odoo 個資與寫 Google 權限，會形成單方獨大。
- 如果 AI 可根據五維碼直接寫 production，會繞過人類決策。
- 如果 audit 只記 code 不記 manifest hash，事後不可查。

## 藍隊修正

- 五維碼只保存無敏 code 與 hash，不保存可逆個資。
- 零值分支不可自動補值；缺資料即 warn/block。
- 自動帳戶分離：Odoo service role、Gateway bridge、Google proxy、Audit logger 不同職責。
- 寫入分級：docs/audit 可 L1，Odoo/Google production 仍 L3 until approved。
- 每次 I/O 寫入 request manifest、lineage、SHA256、rollback。

## 建議落地順序

1. 建立 `five_dim_code_schema`。
2. 為 Odoo role/device/ticket/event 產生無敏 code proposal。
3. 建立 Google group/OU label 對照 manifest。
4. 將五維碼納入度規預測告警 scanner。
5. 建立 append-only bridge audit journal。
6. 沙盒驗證紅隊修正後，再考慮 Gateway stub。

## 結論

五維碼零樹狀張量運算法適合作為 Taiji Hub 的非敏 I/O 表達層，尤其適合 Odoo 主場景、Google 無敏權限管理、分散式節點、預測告警與 audit/rollback 的連接。但它不可替代度規總成，不可承載 secret 或個資，不可直接驅動 production 寫入。第一階段應採「只讀索引 + 無敏橋接 manifest + 治理文件寫入」三步走。
