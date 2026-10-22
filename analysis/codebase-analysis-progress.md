# 程式庫分析進度與跨對話交接

**工作識別：** `TAIJI_HUB_CODEBASE_ANALYSIS_PHASED_20261009`
**版本：** `progress-v2 / 2026-10-09 第二階段唯讀元件分析完成（Asia/Taipei）`
**工作類型：** 技術架構稽核與文件化；此文件不是正典、不是總場授權，也不得作為自動執行指令。

## 專案與授權邊界

- 根目錄／節點：`taiji01:/home/taiji_admin/Taiji_Hub`。
- Founder 定義：W7TP／8D ADI V2.3；八合一單一動態狀態場，非八步流程、八固定欄位或八個孤立模組。
- D1 意圖、D2 狀態、D3 座標、D4 證據、D5 執行／政策、D6 生成式狀態傳輸、D7 風險／隔離、D8 封套／權威必耦合理解。
- 技術證據須分：宣告、檔案、來源實作、服務登錄、程序即時狀態、測試、正式權威及產品效果；不可混用。
- 使用遠端桌面連線指揮官讀取實際節點；不主動 VPN、不更動網域／路由器、不重做已閉合 T-007。
- 僅明示寫入此 `analysis/` 分析文件；不修改程式、核心、正式狀態指標、資料庫、服務或 Git 索引，不執行 POST 副作用路由。
- 不讀取 `.env`、`secrets`、個資明文、私鑰、憑證，文件中只留來源路徑與安全摘要。
- 如同時有其他任務在修改程式庫，保留其變更，不 `git add`、commit、push、stash、reset。

## 分析方法：最多三階段

1. **第一階段 Discovery & Architecture（發現與架構）**：沿現行正典指標、既有索引與實際 import（匯入）／API（應用程式介面）呼叫定位；產出總覽、呼叫圖與可確認的風險候選。
2. **第二階段 Component Analysis（元件分析）**：僅對第一階段已發現的關鍵因果邊界深入讀取；驗證 D6 原胞／模型路由、D8 隔離與 Odoo 業務鏈。文件待產生 `component-deep-dives/`、`code-patterns-identified.md`、`technical-issues.md`。
3. **第三階段 Documentation & Recommendations（文件與建議）**：以實測證據整理完整指引、疑難排解、開發接手及精準候選建議；後續文件 `comprehensive-codebase-guide.md`、`technical-recommendations.md`、`developer-onboarding-guide.md`。
每階段先核對進度，再更新此檔；避免重新無界掃描，禁止把分析升格為部署或權威裁決。

## 已完成：第一階段（2026-10-09）

- 已使用 Remote Desktop Commander（遠端桌面連線指揮官）連上 taiji01，並確認 MSI、penguin 裝置在線；未對另兩節點做程式內容驗證。
- 已讀總場入口、AGENTS.md、V2.3 正典指標／契約、T-007 登錄、Runtime Query Index（執行環境查詢索引）、Gateway 與原生 ADI 來源、GST V2.3 消費端綁定、Odoo Compose／附加模組資訊。
- Git 當時：分支 `codex/current-live-state-consolidation-20260915`，HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e`，28 個已追蹤未提交修改（`-uno` 不含未追蹤項）。
- 查得 3,865 個 Git 追蹤檔、16 個 Odoo 附加模組頂層目錄、166 個 `test_*.py` 檔；未執行測試。
- 現行正典／產品／Current Field／權威檔雜湊已核對歷史閉合登錄一致；未以雜湊取代執行層判定。
- 只讀 HTTP 健康探測：8081、8082、9110、LAN Odoo 8069 均 HTTP 200；localhost 8099 無法連線；未測試任何 POST。
- 原生 ADI 9110 的 PID 1557 掛在使用者 `w7tp-native-adi.service` cgroup；system-level 同名單元 inactive，不構成整體離線判斷。
- Gateway OpenAPI 實際登錄 28 條路徑，含 NL execute、GST deliver/status 與舊 UI 意圖編譯；登錄不能代替實際交付或功能驗收。
- 已產生 `analysis/project-overview.md`、`analysis/architecture-analysis.md`；第一階段文件完成、未建立能力或修改服務。

## 現行候選與未知

- 候選 A：`services/w7tp_ui_adapter.py::compile_packet` 仍使用 `D1_Taiji_Root`、`D6_Governance_Linter`、`D8_State_FSM`。需沿消費端辨別它是否為 legacy UI 投影，或誤入 V2.3 正典；不可直接宣稱總場語義失效。
- 候選 B：`tools/w7tp_nl_goal_runner.py` 確有 `pull_task_dynamic_context_for_model` 與 `TotalFieldDynamicContextPullBroker` 呼叫，但此次未實際拉取模型結果；新執行效果未知。
- 候選 C：Odoo 工作樹有未提交程式變更，Compose 宣告與目前容器載入版本尚未一致性驗收；不應修改進行中的菜單／會員工作。
- 未知：各業務路由端到端效果、D6 完整封包成本、跨節點模型實際授權、當前容器的精確原始碼鏡像與端到端安全驗收。

## 第二階段原訂最短任務（已執行，保留原始規格）

1. 唯讀追查 `services/w7tp_ui_adapter.py::compile_packet` 的實際消費者和 schema（結構描述），確認 V2.3 語義是否被 legacy 包裝污染；先核對其隔離與既有測試。
2. 檢視 `tools/w7tp_nl_goal_runner.py:852–918,1054–1074`、`tools/total_field_dynamic_context_pull.py` 及既有對應測試／歷史驗收，區分 static cell 宣告、真實 pull、本地重構與模型效果。
3. 從 Odoo `wuchang_cafe_ai_gateway`、`wuchang_cafe_menu_options`、會員與票券模組沿 controller→model→view 追查被使用的實際呼叫；先處理來源與 live 一致性，不執行模組升級。
4. 查找已有分析／技術建議後再形成局部建議，優先重用既有索引與治理器官，禁止發明第二小J或第二總場。

## 新對話續接提示語

> 繼續 `taiji01:/home/taiji_admin/Taiji_Hub/analysis/codebase-analysis-progress.md` 中的 W7TP／8D ADI V2.3 程式庫分析。請先唯讀核對現行 HEAD、V2.3 正典指標與工作樹，讀取 `project-overview.md`、`architecture-analysis.md`、三份 `component-deep-dives/` 深入追查、`code-patterns-identified.md` 與 `technical-issues.md`；第一、二階段已文件化，不重做。下一階段只針對已有證據完成開發指引、疑難排解與有界的候選改善建議。使用遠端桌面連線指揮官；不得修改核心、服務、資料庫、路由器、網域或既有 28 個待審程式變更。完成後更新進度與來源。

## 驗收狀態

- `PHASE_1 = DOCUMENTED_READ_ONLY`（三份文件已建立並回讀抽驗；未變更既有程式或 Git HEAD）。
- `PHASE_2 = DOCUMENTED_READ_ONLY`（三份元件深入追查、程式模式與 C-01 至 C-10 技術問題矩陣均已寫入、回讀抽驗；Git HEAD 與原有 28 個已追蹤修改數未變）。
- `PHASE_3 = NOT_STARTED`。
- `TEST_EXECUTION = NOT_RUN`。
- `DEPLOYMENT = NOT_RUN`。
- `TOTAL_FIELD_DECISION = NOT_RUN`。
## 第二階段完成紀錄（2026-10-09，Asia/Taipei）

- 節點與來源：taiji01，本機程式庫 `/home/taiji_admin/Taiji_Hub`；Git `3c2e5884bc149ffbb02d81fdf288506918fae79e`；觀測時 28 個已追蹤未提交修改，必須保留。
- 舊 UI 路徑：`web/w7tp_8d_control_panel.html` → `services/w7tp_ui_adapter.py::compile_packet` → linter／hash／本地 ledger；未找到直接升格 V2.3 D8 的程式呼叫。候選為局部標示／語義隔離問題。
- Dynamic Context 路徑：Native ADI `/v1/adi/insert` 與 `/packet`、本地規則與 broker 暫態重構存在；runner 傳給模型的 `state_cell_transmission` 只含 `context_ref`／驗證等，而未直接交付完整 `model_visible_context.state_projection`，任務等價回答驗收尚缺。
- Odoo 即時證據：容器掛載和 Odoo 18／PostgreSQL 15 運作已查；多項模組於 `ir_module_module` 為 installed，菜單 view XML IDs 與 model fields 存在；匿名 `/wuchang/xiaoj/ordering` 落在 public 候選展示頁。同 URL 尚有 auth=user 的 packet gate 宣告。
- 會員權限高優先候選：`wuchang_cafe_ai_gateway/controllers/main.py:743–785` 的 `member-preference-candidate`／`member-memory-toggle` 以傳入會員引用取資料，使用 `sudo()`；`wuchang_member_registration/models/member_registration.py:2098–2270` 的 vault 查寫未見目標與登入者重綁，且候選偏好查詢含 `last_candidate_at` 寫入。功能 gate 目前啟用；未作漏洞利用或私有會員資料查閱。
- 既有券購買路由回報 HOLD（原始碼）；主權會員兌券有另一獨立候選／dry-run，兩者不可合併判定。`menu_import.py`／`pos_mvp_api.py` 的檔案存在不等於已被 controller init 載入。

### 第二階段新文件（相對於 `analysis/`）

- `component-deep-dives/w7tp-legacy-ui-d8-boundary.md`
- `component-deep-dives/dynamic-context-adi-model-delivery.md`
- `component-deep-dives/odoo-menu-order-member-ticket.md`
- `code-patterns-identified.md`
- `technical-issues.md`（C-01 至 C-10 局部候選及反證、下一步）

### 第三階段待執行（不自動啟動）

- 先沿 `technical-issues.md` 的優先順序釐清 C-01 會員自然人授權、C-02 模型可見狀態、C-03 點餐同名路由，在文件中訂定可驗證的最小修正與驗收準則。
- 產出 `comprehensive-codebase-guide.md`、`technical-recommendations.md`、`developer-onboarding-guide.md`；只描述已知系統，不額外造核心或宣布正式權威。
- 須在獨立授權及保護現有變更的情況下，才能執行真正修復、整合測試、服務載入或部署。

### 第二階段權責與非動作

- `SOURCE_AND_SAFE_READONLY_LIVE_OBSERVATION = COMPLETE`；`POST_EFFECTFUL_API_CALLS = NONE`；`MEMBER_DATA_READ = NONE`；`CODE_OR_SERVICE_MUTATION = NONE`；`PHASE_3 = NOT_STARTED`；`TOTAL_FIELD_DECISION = NOT_RUN`。

## 最新 Founder 指令：8D ADI 技術原理與內部傳輸效率（2026-10-09）

- **Founder 定義，不是模型修改：** 8D ADI 是 Founder 的技術原理，八維是八合一單一動態狀態場，並非額外治理／資安程序。內部傳輸以效率優先，排除一切不必要的外部防禦。
- **本次直接查核：** `products/eight_dimensional_generative_memory/w7tp_endpoint_rule_handshake_v1.py` 既有規則握手與序列化 wire bytes（線上位元組）比較；`tools/w7tp_origin_context_transport_v1.py` 可按封包大小選共享規則原胞或完整傳輸；`tools/w7tp_bridge_dynamic_context_transport_v1.py` 有既有橋接候選，未驗證是所有節點 live 正式路徑。
- **局部候選 C-11：** 每次逐規則重新雜湊、重新握手、多種候選封包都生成且只以位元組決策，可能形成不必要開銷。應以有效規則狀態重用、避免外部中轉、同任務全成本測試，優先優化既有 adapter，禁止第二核心或新增防護器官。
- **仍須保持精確性：** D7／D8 技術條件不等於層層外部防火牆；規則未就緒、必要依賴失效、跨會員越權或狀態版本漂移，僅限制相應依賴動作與結論。不存在因同區網便自動增權。
- **新增文件：** `analysis/component-deep-dives/internal-transport-8dadi-efficiency-principle.md`；`analysis/technical-issues.md` 已附加 C-11。沒有改動正典、原有來源程式、服務、路由器、模型或權限。
- **後續：** 若進入第三階段，將 C-11 的成本比較與能力重用列入優化建議，先列來源／接收端／規則／版本／觀測時點，再界定是否真的能省下一段外部防禦或重複工作。

## 最新執行進度：規則匝道器取代橋接層計畫分析（2026-10-09）

- **D1 最新明確意圖：** 內部原胞傳輸採規則匝道器，禁止用智能分析決定傳輸方式；維持 8D ADI V2.3 八合一單一動態狀態場與 Founder 技術定義。
- **已執行程式範圍：** `tools/w7tp_bridge_dynamic_context_transport_v1.py` 的 `build_plan`、`NaturalLanguageRequest` 依賴及按模型資源計畫選任務的 fallback 已去除；選擇依據為已登錄任務與現行檢查點，遇未知／多個明示 task 即 HOLD；原封包發行、broker 與原有 `w7tp_origin_context_transport_v1.py` 選擇器保持不變。
- **新增來源測試：** `tests/test_w7tp_bridge_rule_gateway_only.py`（8／8）；加上既有原胞傳輸（4／4）與端點握手（8／8）共 20／20；已檢查 `git diff --check`、Python 語法。
- **工作樹保護：** Git HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e` 不變。原先 28 個已追蹤待提交修改保留；本輪橋接器修改使總數為 29，另有新測試檔及 `analysis/` 未追蹤文件。不執行提交、推送或服務變更。
- **效果界限：** 已修改本地來源及完成離線模擬測試，**沒有**核實該候選目前為正式執行的所有內部傳輸入口；未測量端到端延遲、封包總成本或呼叫模型狀態。`DEPLOYMENT=NOT_RUN`；`D8_FORMAL_DECISION=NOT_RUN`。
- **後續第三階段：** 從實際呼叫入口確認何處尚需綁定此規則匝道器，避免另造第二核心；量測端到端成本與有效任務等價後才進入正式變更審查。

## 2026-10-09 新節點（03／04）規則匝道器接入可行性與 ADB 歷史修正

- Founder 最新補充：taiji04 **先前曾以 Android Wireless Debugging（無線偵錯）連線**。這是使用者的直接歷史資訊，不能因 RDC 未列示 04，否定其既有可能的區網傳輸通道。
- 本輪已連線 taiji01／MSI／penguin 唯讀查核：taiji03 RDC Offline，taiji04 沒有獨立 RDC 設備項；taiji04 歷史 SUNMI `V3_MIX_EDLA_GL` 和 LAN `192.168.50.176` 有歷史證據，但本次 ping 與鄰居解析未成功，不能臆測新 IP／ADB 埠。
- 已檢查 taiji01 Linux、MSI WSL、MSI Windows 原生的 `adb devices -l` 與 `adb mdns services`，均未列示有效 Android 連線；兩 Linux 執行唯讀 ADB 查詢時僅啟動當地主機 adb daemon，未配對手機、未修改設備。MSI WSL 保有 2026-10-07 的 adb known-hosts 檔中繼資料，但不能將其內容或對應設備猜定為 04。
- Active V2.3 all-node with-router list包含 `V3_MIX_EDLA_GL`，並不以別名 `taiji04` 作獨立列，也未列 `taiji03`。舊設備或音訊登錄不能直接當作新節點正式 D8 授權。
- **結果：** 03 與 04 均可依特殊架構列為 `RULE_GATEWAY_ADMISSION_CANDIDATE`；03 等待實際 LAN／身分／規則就緒，04 等待同區網已配對 ADB 無線偵錯可達、精確設備身分及接收規則能力綁定。均非 `ACTIVE_BOUND`，沒有改正典、路由器、VPN 或部署。
- 詳細報告：`analysis/component-deep-dives/taiji03-taiji04-rule-gateway-admission-20261009.md`。此項是原規劃中 **正式入口查核的節點擴張候選**，待實際有效身份與通道到位後再做端到端實證；不得因手機目前未可達直接宣稱 8D ADI 原理或規則匝道器失效。

## 2026-10-09 裝置納管／規則匝道器交接待辦凍結（使用者要求保留未完成步驟）

- 已建立三份續接交付文件，請先讀後執行：`analysis/20261009_node_onboarding_checklist.md`、`analysis/20261009_rule_gateway_acceptance_matrix.md`、`analysis/20261009_rule_gateway_resume_prompt.md`。
- **更新即時證據：** Desktop Commander（遠端桌面指揮官）本輪 taiji01、MSI、penguin、taiji03 均 Online；taiji03 由上一輪 Offline 恢復 Online。透過 RDC 進入 taiji03 WSL 直接觀測 `hostname=taiji03`、`user=lenovo`、`LAN=192.168.50.148`。其 `/home/lenovo/Taiji_Hub` 僅一份既有歷史網路探測檔，找不到預定的三個規則傳輸器來源檔；不要將此節點當作已經具備規則接收執行能力。
- localhost（歷史 iOS peer 名稱待核）及 wuchang-us-free-node 此時仍離線；04 沒有獨立 RDC 設備列，曾經使用 Android ADB 無線偵錯但本次還沒恢復，同區網舊 IP 不可達。
- **仍未完成（嚴禁自動宣稱 PASS）：** 各節點 agent 的開機自啟與實體身份綁定、03 規則基座定位、04 ADB／平台支援核對、其他離線節點必要性核查、既有規則匝道器正式服務入口綁定、跨節點雙端規則指紋與端到端等價效果測試、完整總成本效能比較、第三階段三份工程文件、C-01 Odoo 會員權限產品上線前驗收，以及對獨立規則橋接器候選程式的送審／Git 提交推送。
- **已做過不用重做：** 既有規則橋接器最小來源修改（移除智能 `build_plan`，明確任務引用／檢查點確定性綁定）、新 8 項與既有 12 項測試合計 20/20 單元通過、第一／第二階段程式庫分析與其文件。單元通過不是實際多節點交付。
- **本輪僅建立交接文件與唯讀節點查核。** 沒有增加／撤銷 RDC 裝置、未做 Git 提交推送、未安裝或重啟服務、未改路由器／網域／VPN／正典／資料庫。taiji01 既有 HEAD 與 29 個已追蹤未提交程式變更仍保留。
- 下一輪開工須先重新取得目前設備狀態、Dynamic Context（動態上下文）及現行正典指標，沿既有規則匝道器，不以舊報告、在線 UI 或檔案存在推斷正式能力。
