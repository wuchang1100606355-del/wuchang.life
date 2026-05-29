# Taiji Hub 中文白皮書

版本：0.1  
日期：2026-05-11  
狀態：治理式落地草案  
分類：非敏感治理與系統設計文件

## 摘要

Taiji Hub 是一套以本地優先、治理優先、無明文外流為核心原則的 AI 節點治理與系統封裝環境。它將本機硬體錨點、加密封裝、VPN 節點、Odoo Runtime、Taiji Gateway、Five Metric Gate、AI 救援快照、數位身分與人類決策 receipt 串成一條可審計、可回滾、可封裝的工程鏈。

在應用定位上，Taiji Hub 是新北市三重區五常社區發展協會委託江政隆本人開發的社區管理與社區場景應用系統。它以 STEALTH 16 STUDIO A13V 筆記型電腦上的小J本地模型作為主要開發與治理協作工具，目標是把 AI POS、AI 管委會設備管理、Odoo Governance Runtime、VPN 節點、拓樸與匝道器收斂成可落地的社區 AI 治所平台。

本系統的目標不是讓 AI 自行取得無限制執行權，而是把高權限操作收斂到明確的治理邊界：每個敏感操作都必須通過本機授權、人類決策、Gateway/Policy/Five Metric 檢查、audit log 與 rollback plan。雲端 AI、Google Workspace、Ultra 訂閱與服務帳戶權限可作為治理語意與代理能力來源，但不得承載明文上下文、secret、會員資料或私人資料外流。

完整的功能化與結構化規格見 `docs/wuchang_community_system_functional_structure_zh.md`。該文件將五常社區場景、AI POS、AI 管委會設備管理、授權式功能全自動執行、社區維運未啟用現況與 POS 已有大量實作的狀態納入治理語言。

架構、模組項目與完成度合併看板見 `docs/taiji_hub_architecture_completion_board_zh.md`。該看板以圖塊、架構表與分窗表呈現目前 repo 可驗證的治理封裝完成度，不代表 production 上線率。

Five-Metric Tensor Runtime 規格見 `docs/taiji_five_metric_tensor_runtime_zh.md`。該規格將所有 runtime 行為轉為 `TensorPacket`，以意圖、資源、時間、權限與拓樸五個度規治理執行、replay、deadbox、audit、分散式節點與多模態路由。機器可讀 schema 位於 `schemas/tensor_packet.schema.json`。

度規預測告警制度見 `docs/taiji_hub_predictive_alert_system_zh.md`。該制度使用度的張量變化與規的向量偏移，主動向開發者提供可能危害、錯窗、越權、容器暴露、財務風險與公益資產風險的提示。

Google Workspace 組織政策閘道設計見 `docs/taiji_hub_google_workspace_policy_gateway_zh.md`；設備最小權限與 AI 瀏覽器 UI 設計見 `docs/taiji_hub_device_least_privilege_browser_ui_zh.md`。兩者共同原則是：最高授權只進入認知窗，實際行動必須降權到最小分窗，先經沙盒驗證與紅隊修正，再以 patch、manifest 或受控 UI 動作落地。

Odoo/Google 延伸開發分工規格見 `docs/taiji_hub_odoo_google_extension_spec_zh.md`。Taiji Hub 以 Odoo 作為社區/POS/設備/工單的場景主系統，以 Google Workspace 作為無敏帳戶、群組、OU、權限政策與 audit metadata 的管理系統；兩者透過 Gateway/Five Metric 對齊，不互相取代、不單方獨大。

五維碼零樹狀張量 I/O 全系統評估見 `docs/taiji_hub_five_dim_zero_tree_tensor_io_assessment_zh.md`。該評估將五維碼定位為非敏 metadata、hash、role label、event id 與 audit id 的治理 I/O 層；它可支援雲地自動帳戶橋接與分散式節點，但不得承載 secret、個資或取代度規總成。

Odoo 接 Google for Nonprofits 信箱橋接規格見 `docs/taiji_hub_odoo_google_nonprofit_mail_bridge_zh.md`。預設採 Google Workspace for Nonprofits 免費方案作為 `wuchang.life` 的網域信箱與無敏權限管理來源；Enterprise 類方案只列為非營利折扣，不作免費預設。橋接 manifest 位於 `Taiji_Governance/integrations/odoo_google_nonprofit_mail_bridge_manifest.json`。

## 委託與應用定位

本白皮書描述的系統不是抽象研究原型，而是面向五常社區場景的多功能治理與應用開發平台。

應用定位：

- 社區管理：支援社區事件、設備、角色、流程與治理紀錄。
- AI POS：整理並封裝既有大量 POS 實作，建立交易、商品、客顯、商米 POS、Odoo POS 與資料安全邊界。
- AI 管委會設備管理：將路由器、VPN 節點、客顯機、POS、工作站與伺服器納入數位身分與 health/preflight/audit。
- 社區場景應用：支援咖啡館、社區服務、活動、資源交換、ESG 與社區價值映射。
- 度規張量總成：以五維度規拓樸、度規轉譯匝道器、Taiji Gateway 與 Five Metric Gate 作為治理抽象核心。

社區維運目前仍屬未啟用與設計中階段，不得宣稱為已上線 production ready。POS 則已有大量實作，下一步應以 inventory、治理封裝、測試邊界與資料分級為主。

## 授權式功能全自動執行

Taiji Hub 的 AI 可在安全範圍內取得由江政隆本人授權的開發者職能與工具鏈能力，進行自動盤點、文件化、patch、測試、manifest、preflight、風險表、rollback plan 與封裝建議。

這種「繼承系統開發者能力權限」只代表繼承經授權、可審計、可回滾、受 Gateway/Policy/Five Metric Gate 管束的工程執行能力，不代表 AI 可持有自然人身分本身、證件號、自然人憑證 PIN、service account JSON、OAuth token、private key 或 password。

自然人身分證明與本機授權可作為人類決策流程的外部證明，但不寫入 repo、不寫入 audit 明文、不交給雲端模型。

## 小J 行為憲章

小J 的行為方針必須以度規拓樸匝道器進行對齊。任何行動都要先判斷意圖、授權、敏感度、風險、證據、分窗與回滾，不能只依單次指令字面擴權。

不可變價值錨點：

- 家人、戰友與受託社區場域的長期安全與共同利益。
- 公益與眾利價值。
- 善良正向的用途邊界。
- 工程精準、誠實驗證與可查核。
- 智能分窗對齊：設計、開發、測試、治理、部署準備與運行不得混用權限或上下文。

因此，小J 可成為主動、可靠、能自動完成工程工作的代理，但不可成為不經授權的 secret 持有者、遠端執行者、雲端明文中繼器或 production 變更者。

## 度規完整性

度規在 Taiji Hub 中是法則層，不是任何單一人或 AI 可任意改動的偏好。江政隆本人與小J皆為公益及社區的度規守門人；守門人的責任是維護完整性、阻擋漂移、保存證據、推動可驗證演化，而不是凌駕於度規之上。

度規的核心計算定義是：度為張量計算，規為向量計算。度負責多維資料、場景、權重、風險、距離、關係與狀態；規負責方向、約束、邊界、允許/阻擋與行動投影。沒有這個定義，就不是本系統的度規法則。

匝道器的角色，是把「度」的多維張量狀態轉譯成「規」的向量行動邊界，再交由 Gateway/Policy/Five Metric Gate 產生 allow、allow_with_audit、warn 或 block。

度規運算要對齊絕對價值，不得以預定價值進行應用。也就是說，系統不可先預設某個人、某個收入項、某個技術或某個方案必然正確，再把資料拿來替預設答案背書。它必須先守住人類文明制度、人的基本生活、公益可執行、基金池可存活與合理貢獻補償，再由資料、證據與社區場景計算相對價值。

本系統的基準不是「無償消耗個人」也不是「私人獲利最大化」，而是在公益可執行與基金池可存活的約束下，達到眾利、公益存續、人的飽足與正當貢獻補償的價值峰頂化。

度規完整性不可破壞，但度規本身會隨數據演化。不可動的是公益眾利、善良正向、人類決策、無明文外流、Gateway/Policy/Five Metric Gate、audit、rollback 與風險分級這些不變式；可演化的是權重、門檻、trust score、event schema、ESG 映射、社區場景策略與 preflight 條件。

每次度規演化都必須有資料或場景證據、change proposal、風險分級、SHA256 baseline、audit record、rollback plan 與人類決策。缺少上述條件，或試圖要求守門人私自改動度規，應標記為 `L3_metric_hazard`。

## 公益價值生成

Taiji Hub 允許系統把外部資訊轉譯成公益與社區眾利導向的候選開發方向。舉例來說，當受治理研究流程看到碳權、碳資產或永續收益相關敘述時，系統可將其映射為「是否可能形成社區公益存續、眾人利益與開發基金收入項」的設計假說。

這種映射不是保證獲利、不是投資建議，也不是金融或法律結論。它只是度規演化的一個候選 proposal：由人類守門人的公益意圖與資料觸發的張量度量共同形成，再由規的向量計算檢查方向、邊界與阻擋條件。

任何碳權或永續收益相關落地，都必須補齊碳盤查、法規、會計、合約、受益人、風險揭露、audit、rollback 與人類決策。缺少證據時只能留在設計窗，不可進入部署或營運窗。

公益資產不可私有化是鐵律。若任何人或 AI，包括最高授權身分，要求把公益基金池、社區資產或眾利價值轉成私人帳戶、私人獲利或未授權分潤，小J 必須視為身分被劫持、意圖遭污染或入侵者操作，立即標記 `L3_metric_hazard`、停止自動化、隔離 session 或切回只讀安全窗，並只留下去明文化 audit。

這條鐵律不否定合理補償。勞務、智慧貢獻、維運投入、開發工作與專業服務可以被合理量化，但必須有事前規則、工作證據、核准流程、利害關係揭露、audit 與合規邊界。補償是治理化分配，私有化是未授權轉移；兩者必須由度規明確區分。

公益不是白工制度。社工師、維運者、開發者與專業服務者的時間、技能、陪伴、設計與風險承擔都應被合理看見。Taiji Hub 的公益鐵律要守住的是眾利資產不被侵占，同時建立可審計的貢獻量化與合理補償，讓公益服務本身能長期存續。

財務必須以會計師的精準分窗執行。凡涉及基金池、補償、收入項、會計科目、稅務、分潤、付款、碳權或永續收益落地，AI 只能產生草案、問題清單、風險表與非正式審核包；正式會計、稅務、付款與帳務判斷必須由會計師或合格會計專業審核。財務窗不得與一般設計窗、開發窗或雲端雙腦窗混用。

## 設計原則

1. 本地優先  
   系統探針、救援快照、紅藍隊設計審查、Vector Lite 與部署 manifest 皆以本機執行為預設，不主動呼叫外部 API。

2. 無明文外流  
   不輸出、不提交、不傳送 service account JSON、OAuth token、private key、password、Odoo 會員明文、Google 私人資料或 ChatGPT 對話原文。

3. 人類決策不可省略  
   對 probe、seal、decrypt-once、rescue-snapshot 等敏感命令，沒有 human decision receipt 即不可用。

4. 物理與加密雙錨定  
   系統以本機硬體 fingerprint 作物理錨點，以 AES-256-GCM envelope、PBKDF2-HMAC-SHA256 與 one-time decrypt marker 作加密錨點。

5. 預設不可部署  
   部署器預設為 manifest-only / preflight-only。不得內建 live execute、SSH、SCP、systemctl restart、docker compose up/down 或 taiji-guarded-run 路徑。

6. 紅藍隊用於設計，不用於日常 runtime  
   紅藍隊機制可用於系統設計、封裝與上線前淬鍊；不得排程化、daemon 化，亦不得作為 production service 的日常運行機制。

7. 可審計與可回滾  
   每個重要動作都應留下 audit record、SHA256 baseline 與 rollback plan。

## 系統架構層

目前架構 profile 定義於 `Taiji_Governance/architecture/layers_standards.yml`。

### Physical Anchor

物理錨點層用來確認操作發生在被授權的本機環境。系統只保存硬體訊號的 SHA256，不輸出 raw machine-id、DMI serial、hostname 或其他原始硬體識別值。

用途：

- 綁定 human decision receipt。
- 綁定 hardware-bound envelope。
- 綁定 AI rescue snapshot。
- 防止敏感動作在未知機器上重放。

### Cryptographic Envelope

加密封裝層提供本地硬體綁定的一次性解密能力。

目前特性：

- AEAD：AES-256-GCM。
- KDF：PBKDF2-HMAC-SHA256。
- one-time decrypt marker：成功解密後寫入 used marker，第二次解密同一 envelope 會被阻擋。
- plaintext stdout：禁止。
- secret material printed：禁止。

### Tensor Protocol

Tensor Protocol 是系統對「度量、距離、權重、風險級別」的抽象表達層。它對應 Five Metric Gate 的治理邏輯，用於將行為分級為：

- `L0_exact_match = allow`
- `L1_near = allow_with_audit`
- `L2_drift = warn`
- `L3_metric_hazard = block`

### Context Runtime

Context Runtime 管理上下文生命週期。它的核心不是保存全部上下文，而是保存足以恢復工程判斷的安全摘要。

代表能力：

- runtime snapshot。
- AI rescue snapshot。
- redacted excerpts。
- critical file SHA256。
- progress / worklist / architecture profile 摘要。

### Event Mesh

Event Mesh 是 audit log、system journal、deployment audit、probe audit 的事件網。它以 JSONL 與文字 journal 形式保存治理軌跡，支援後續回放、審查與事故復盤。

### Governance Engine

Governance Engine 是系統的決策邊界。它負責將人類授權、數位身分、Gateway policy、Five Metric Gate 與風險分級組合起來，決定某個動作是否可進入下一步。

### Community Currency

Community Currency 層代表未來可擴展的社群信任、貢獻、點數或互助價值映射。現階段它是治理架構中的保留層，不承載支付或金融邏輯。

### ESG Mapping

ESG Mapping 層用於把事件、節點、營運流程與永續治理指標建立關聯。現階段以事件 schema 與 audit protocol 作為基礎。

### Sovereign AI Nodes

Sovereign AI Nodes 表示節點可在本地、VPN、邊緣或組織授權環境中運行，但必須服從本系統治理規則。節點不是自由執行體，而是受身份、policy、audit 與 local hardware anchor 管束的自治單元。

## 核心元件

### Taiji Governance

`Taiji_Governance/` 是治理中心，包含：

- `worklist/worklist.md`：待辦與安全工作清單。
- `progress/progress.md`：進度與狀態紀錄。
- `logs/audit.log`：主要治理 audit。
- `logs/deployment_audit.jsonl`：部署與 preflight audit。
- `identity/digital_identity.yml`：Taiji digital identity。
- `architecture/layers_standards.yml`：架構層與標準。
- `deployments/`：部署 manifest、preflight record、rollback plan。
- `rescue_snapshots/`：AI 脫窗救援快照規範。
- `one_time_decrypt/`：硬體綁定一次性解密規範。

### Taiji AutoBuild

`Taiji_AutoBuild/scripts/` 是安全自動化工具區。

目前重要腳本：

- `00_readonly_probe.sh`：唯讀探針。
- `01_import_chatgpt_export.py`：ChatGPT 匯出檔 metadata-only manifest，不輸出對話原文。
- `02_start_vector_lite.sh`：Vector Lite plan-only 啟動計畫，不直接啟動服務。
- `03_collect_runtime_snapshot.sh`：runtime snapshot。
- `04_system_total_probe.py`：本機授權、人類決策、物理錨點、加密 envelope、一次性解密與 AI rescue snapshot。
- `05_red_blue_exchange.py`：本地設計審查用紅藍隊工具，不送雲端明文，不用於日常 runtime。

### Tailscale Deployer

`legacy_core/wuchang_tailscale_deployer.py` 已從舊式直接部署器降級為安全 manifest generator。

目前特性：

- 預設 `manifest-only`。
- 支援 `preflight-only`。
- 不提供 `--execute`。
- 不執行 SSH/SCP。
- 不寫遠端 systemd。
- 不傳送 service account JSON。
- preflight 只做本地檢查，例如 Tailscale 狀態、allowlist、known_hosts、GCP_KEY_PATH 是否存在、Five Metric health/policy、audit 是否可寫。

### Taiji Vector Runtime Lite

`Taiji_Vector_Runtime_Lite/` 是本地向量 runtime 骨架。

設計原則：

- local-only。
- 不呼叫外部 API。
- 不持久保存明文。
- 保存 item id、sha256、vector、metadata。
- launcher 只輸出 plan，不直接啟動服務。

### Taiji Gateway

`services/gateway/app.py` 是最小 Gateway skeleton，目前提供：

- `/healthz`
- `/`

它代表未來所有高風險外部互動的收斂入口。Google API、Gemini、OpenAI、Workspace Admin 與 service account delegation 的實際使用，都必須先經 Gateway、Audit、Policy 與 Five Metric Gate。

### Odoo Runtime

`Taiji_Odoo/` 包含 Odoo 18 與 PostgreSQL runtime。它是 POS / 會員 / 營運資料的可能承載層，但目前仍存在需要治理化的風險：

- compose 中仍可見密碼類環境變數。
- Odoo database manager 曾被觀察到 localhost 可達。
- 任何會員明文不得進入雲端 AI 或外部 API。

## 數位身分模型

`Taiji_Governance/identity/digital_identity.yml` 定義本系統的非敏感身分描述。

已知身份類型：

- human authority：自然人最高治理決策。
- workspace admin authority：`admin@wuchang.life` 類組織管理權限語意。
- delegated service policy：Google Ultra proxy 類代理權限語意。
- vpn subnet router：如 `taiji01`。
- admin workstation：如 `msi`。
- customer display：客顯機。
- point of sale：商米 POS。
- router：ASUS RT-BE86U。
- gateway：Taiji Gateway。
- policy engine：Five Metric Engine。

重要原則：

- 身分檔只保存非敏感 metadata。
- 不保存 PIN、OAuth token、service account JSON、API key。
- 高權限只是 policy 語意，不代表可直接讀取或傳送 secret。

## AI Rescue Snapshot

AI rescue snapshot 是本系統針對 AI 脫窗、上下文壓縮、模型漂移或工程判斷失準設計的救援錨點。

它保存：

- schema 與用途。
- local authorization 狀態。
- human decision 狀態。
- physical layer hash。
- cryptographic layer policy。
- critical files SHA256。
- redacted progress/worklist/preflight 摘要。
- forbidden scan 結果。
- resume instructions。

它不保存：

- raw hardware ID。
- service account JSON。
- OAuth token。
- API key。
- Google 私人資料。
- Odoo 會員明文。
- ChatGPT 對話原文。

## 人類決策 Receipt

本系統採用「無人類決策不可用」原則。

human decision receipt 包含：

- schema。
- issued_at。
- expires_at。
- scope。
- allow / deny。
- hardware fingerprint hash。
- human proof hash。
- local authorization event id。

它不包含：

- human proof 明文。
- 自然人憑證 PIN。
- 任何 secret。

## 紅藍隊設計審查

紅藍隊機制可用，但僅用於系統設計與封裝前審查，不用於日常 runtime。

紅隊視角：

- 找出 direct remote execution。
- 找出 direct cloud AI call。
- 找出 plaintext credential surface。
- 找出 wide bind surface。
- 找出 live compose mutation。
- 找出 execute mode surface。

藍隊視角：

- 將風險轉為收斂建議。
- 將 live action 轉成 manifest / preflight / human decision。
- 將明文 credential 轉出 repo。
- 將雲端呼叫收斂到 Gateway。
- 將 `0.0.0.0` 曝露收斂到 localhost 或 Gateway/VPN ACL proof。

紅藍隊報告不得保存原始明文 evidence，只保存 file path、line、rule、risk 與 line SHA256。

## 雲端與服務帳戶治理

OpenAI、Google Workspace、Ultra 訂閱、Google 3.1 或服務帳戶能力，在本系統中可作為治理授權語意與未來代理能力來源。

但目前規則是：

- 不得直接呼叫 Gemini / Google API / OpenAI API。
- 不得把明文上下文送到雲端。
- 不得讀取或輸出 service account JSON。
- 不得把 Odoo 會員明文、Google 私人資料、ChatGPT 原文送外部模型。
- 真正啟用時必須經 Gateway、Audit、Policy、Five Metric Gate、人類決策與 rollback plan。

## 已知風險與收斂路線

### L3_metric_hazard

- legacy 檔案存在 direct Gemini / Vertex / Google SDK 呼叫。
- 舊腳本存在 `GOOGLE_APPLICATION_CREDENTIALS` 類用法。
- 舊腳本存在 `docker compose up`。
- compose 中存在明文密碼類環境變數。

### L2_drift

- 多個 legacy 服務預設 `0.0.0.0` 綁定。
- Odoo compose 使用 `8069:8069`。
- Five Metric / Tailscale 在某些執行 context 下不可達，導致 preflight block。

### 收斂建議

1. 將 legacy direct Gemini / Vertex 呼叫改成 Gateway policy stub。
2. 將 compose 密碼移出 repo，改為 `.env.example` 與本地 secret boundary。
3. 將 `0.0.0.0` 預設改成 `127.0.0.1`，或要求 Gateway/VPN ACL proof。
4. 將 Odoo database manager 狀態納入 preflight 檢查。
5. 建立 Five Metric Engine 的固定 localhost / Gateway 檢查方式。
6. 將客顯機與商米 POS 的 identity 補齊到 digital identity。

## 系統特色

### 1. 治理先於執行

Taiji Hub 的特色不是「可以自動做很多事」，而是「在做事之前先確定能不能做」。它把風險判斷、授權、人類決策、audit 與 rollback 放在執行之前。

### 2. AI 可協作但不可越權

AI 可以產生 patch、產生 manifest、做紅藍隊設計審查、寫白皮書、生成安全報告，但不能自行讀 secret、呼叫雲端、部署遠端或改 production service。

### 3. 本機硬體成為安全邊界

透過 physical anchor，系統把敏感操作綁定在目前本機硬體上。這讓 rescue snapshot、human decision receipt、one-time decrypt 都具備本機性。

### 4. 一次性解密防重放

one-time decrypt marker 讓同一 envelope 成功解密後不能再被重複使用。這降低了救援包、臨時封裝或敏感恢復資料被重放的風險。

### 5. 救援快照不是資料外洩

AI rescue snapshot 保存的是安全摘要，不是原始資料。它讓下一輪 AI 可以恢復工程上下文，但不拿到 secret、raw hardware、會員明文或私人資料。

### 6. 紅藍隊審查去明文化

紅藍隊可用，但報告不保存原始 evidence。系統只保存位置、規則、風險與 line hash，讓審查可追蹤，同時避免將明文攻擊面擴散。

### 7. Manifest-only / Preflight-only 部署觀

部署器不直接部署，而是先產生 manifest 與 preflight record。這讓系統能在真正執行前看見風險、建立 rollback plan 並留下 audit。

### 8. 可逐步封裝落地

Taiji Hub 目前已具備白皮書、治理目錄、數位身分、探針、救援快照、一次性解密、紅藍隊設計審查與 Vector Lite 骨架。它適合以漸進式方式封裝成可落地的本地治理平台。

## 結語

Taiji Hub 的核心精神是：度量先於行動，治理先於自動化，人類決策先於高風險使用。它把 AI、Odoo、VPN、節點、Google/Ultra 權限與本機硬體放進同一個可審計、可回滾、可收斂的框架中。

這套系統的下一步，不是擴大權限，而是繼續縮小未受治理的面：清理 legacy direct cloud calls、移除 repo 明文 credential、收斂 `0.0.0.0` 服務、補齊 POS/客顯身份，最後才進入受 Gateway 與 Five Metric Gate 保護的落地部署。
