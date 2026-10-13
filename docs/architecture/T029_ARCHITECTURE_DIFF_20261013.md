# T-029｜雲地多模型總成：來源差異與驗收契約

觀測時間（UTC）：2026-10-13T10:01:07.220382+00:00。工程根：taiji01。工作樹：`/home/taiji_admin/Taiji_Hub_worktrees/T029_20261013/review`。

當次動態上下文：`context:task-state:T-029:8c904cfc505d6b84`；只保存引用及雜湊，不保存完整總場上下文。

## 收斂設計

依江政隆 V2.3 定義，八維耦合同一動態狀態場。模型是可替換能力供給；自然人的意圖、身分封包、委任及總場權威共同約束選擇與作用。既有仲裁、會員上下文、封包Broker、可信發行與執行器優先重用。taiji01 為無頭、無GPU伺服器；MSI提供已核實的開發與算力，不取得另一總場權威。

本交付不是新核心、授權收據、已完成部署或產品驗收。原始任務、暫停任務、仁義分店及其他工作成果維持原狀。

## R01–R24逐項追溯

### R01
8D ADI 是八維耦合的單一動態狀態場：D1 意圖、D2 狀態、D3 座標、D4 證據、D5 執行／政策、D6 生成式狀態傳輸、D7 風險／隔離、D8 封套／權威。不是八步、八欄位或八個孤立核心。
差異引用：G09；驗收：A01, A10。

### R02
主權在自然人；模型沒有主權。總場承接江政隆的技術定義及授權意圖，不自行創設權威。MSI、Google、Codex、Git、測試與多模型共識均不是 D8。
差異引用：G01, G02；驗收：A02, A03, A17。

### R03
開發者以外的使用者，依已驗證自然人身分封包、角色／組織／物件／用途／時間／撤銷狀態與當次意圖執行。已授權日常業務不必逐筆再請 Founder 核准；越權、權限擴張與不屬原授權的動作不得執行。不能把所有輸入硬標成 FOUNDER_NATURAL_LANGUAGE。
差異引用：G01, G02；驗收：A02, A03, A17。

### R04
小J是易懂自然語言介面，呈現候選差異、證據、成本及限制；可按有效委任自動選模及完成授權工作。模型排名或文字承諾不得代替使用者授權，不能要求使用者理解內部機器碼才能操作。
差異引用：G01, G03；驗收：A04。

### R05
是多設備、雲地多模型，不是雙模型。Google 也有多模型，依任務採用不同模型；不得用單一固定 Google 型號或不受約束的逐型號重試迴圈替代能力調度。
差異引用：G03, G04；驗收：A05, A06, A07。

### R06
taiji01 是無頭、無 GPU 伺服器；只計已觀測 CPU、RAM、儲存及相關服務能力。不安裝 GPU 驅動，不安排 GPU 工作。MSI 的 RTX 4070 Laptop GPU 約 8 GiB；實際可用量、既有小J表情及推論占用須當次觀測，不可直接吃滿。
差異引用：需按既有驗收補齊當次證據；驗收：A13, A20。

### R07
taiji01 工程入口 /home/taiji_admin/Taiji_Hub；MSI 為開發及算力來源，不因有舊同名權威檔或 Exact-V3 服務取得第二總場。其他節點是可授權能力供給，不是新權威根。
差異引用：G06, G09；驗收：A12, A16。

### R08
統一能力登記／授權不等於所有資料須經伺服器轉送。對每個任務綁定其來源、目的、介面、區域、協定、服務及效果；區網正常時節點用合格 LAN 路徑，不自動改走 VPN。既有反向 SSH 是獨立載體，不能不查路徑便稱外網或 VPN。
差異引用：G07；驗收：A14。

### R09
不改 wuchang.life、路由器、防火牆、DNS、IPv6 全域設定；不開放 WAN ADB、Ollama、資料庫或核心管理埠。使用者有固定 IP／DDNS 是可用資源，不等於本次已授權公開核心。RDC 雲端管理通道不可宣稱為全本地區網通道。
差異引用：G07；驗收：A14, A20。

### R10
分散式算力須有任務／物件／依賴／能力／負載／取消／結果歸屬的真實協作。多台在線或多模型登錄不等於分散式計算通過；不能把 45 標籤、41 雜湊或顯存容量相加當成已聚合算力。跨機權重／張量切分不是本次預設新增目標。
差異引用：G03；驗收：A12, A13。

### R11
先重用 core/resource_arbitration.py 及現有能力索引；規則閘道器先檢查硬條件，再按使用者指定策略選擇。LLM 可提出任務解讀候選，但不得以自由生成的分數更改授權。相同已固定輸入、策略及來源版本應輸出相同合格集合與排序；同分以固定 resource_id 排序。
差異引用：G03；驗收：A01, A04。

### R12
已登錄、已配置、端點健康、模型存在、已載入、能力實測、任務合格、已選擇、已執行、效果通過要分開。缺測值是 UNKNOWN，不能當零、不能當可用；單次健康 GET 200 不代表推論、工具或業務效果成功。
差異引用：G03, G07；驗收：A06, A16。

### R13
所有需上下文的模型經既有當次 Dynamic Context（動態上下文），綁定唯一 TASK_ID、provider/model/version、授權及有效時間。先沿 taiji01 與 MSI 實際索引和呼叫鏈定位；不能只查伺服器就宣告 MSI 缺能力。
差異引用：G06, G10；驗收：A08, A15, A19。

### R14
Google 靜態封包拉取重用 tools/total_field_cloud_fill_packet.py、既有上下文 Broker 與 receive_candidate。由受控 adapter／worker 拉取，不聲稱模型自行具備網路權限。packet_id 精確拉取，綁定不可由雲端修改的欄位、允許填寫部分、nonce、期限、provider/model/version、輸出與回傳座標。
差異引用：G04, G05；驗收：A07, A08。

### R15
Google 型號改選須在當次合格集合及預算內；不同模型的工作各有獨立子封包／嘗試識別，父任務總次數與總費用仍封頂。每封包 single-use 與 max_cloud_calls=1 不得靠重試或拆單偷渡。模型退役、配額、地區、專案權限及工具能力須查官方和已授權專案；不能把 Workspace／Code Assist 訂閱等同 Vertex API 額度。
差異引用：G04, G05, G06；驗收：A04, A05, A07。

### R16
雲端只收完成任務所需的去識別資料及非核心規則引用，不收完整總場、會員明文、憑證、受保護 ADI／碼本、私鑰或無關歷史。雲端結果只回候選，當地驗證器檢查來源、任務、時效、模型版本、權限及結果；哈希一致不證明內容真實。
差異引用：G04, G06；驗收：A08, A15。

### R17
D6 是生成式狀態傳輸，不是普通 JSON、API 呼叫、壓縮、差分或檔案複製。需接收端相容規則、重構條件、狀態關係、可驗證結果。重新查詢、遠端呼叫、原胞重構分別記錄；不以「零原始位元組」隱藏規則前置成本。
差異引用：G08；驗收：A10。

### R18
總效果成本包括完整傳輸、前置規則、狀態取得、SSH 及額外查詢、重構、驗證、授權、CPU/GPU 時間、記憶體、能源、持久／暫存空間及失敗恢復。不同單位不得無政策混成一個分數；首次、穩態、冷啟動與暖機分開。T-025 成本候選只作其範圍的證據，不擅自擴充或部署。
差異引用：G08；驗收：A11。

### R19
靜態封包 Broker 的記憶體 single-use 不等於跨程序／重啟防重放。重用既有持久化與可信發行能力；需證明並行、逾期、撤銷、重啟、重複回傳、傳送逾時及收據遺失情況。不另造簽章根。
差異引用：G05；驗收：A08, A09, A20。

### R20
必要依賴失效，僅停止相關動作；已確認獨立且仍獲授權者可繼續。不能因總場暫失聯自行授權，也不能因可選雲端模型故障令所有本地服務停擺。重試不可造成重複訂單／核銷／付款。
差異引用：G02, G04, G05, G10；驗收：A09, A15, A20。

### R21
不重開 T-007、T-005、T-008、T-026、T-027 等已完成工作；不恢復 T-014、T-018、XJ-018 等暫停工作。T-028 F3/F4/F5 只限制真正依賴它的正式作用；保留其他可獨立候選／測試。仁義分店不動作。
差異引用：G09；驗收：A18, A20。

### R22
不把主線、MSI 舊樹、已安裝規則基座、運行程序、D6 待審來源或 PR 混成同一版本。先證明哪個程序載入哪個實體來源；檔案不存在於 MSI 舊 Git 樹不表示 MSI 實際橋接缺失。
差異引用：G06, G07, G08, G09；驗收：A16, A18, A19。

### R23
source/query/verification hashes、檔名與狀態字不是授權證明。Owner Seal（所有者授權封套）只能走既有可信機制；不得生成測試 seal 給正式接件。所有簽核前檢查完成後，需真人簽署時才提出一次精確申請，不索取私鑰／密碼到對話。
差異引用：G02；驗收：A03, A17, A19。

### R24
調度單一動態場，不另造核心、自然人根、總場、模型權威、平行登錄主冊或預設新服務。必要薄接點必有既有呼叫位置、依賴與測試；沒有現況證據不得宣稱已落地。
差異引用：G02, G10；驗收：A17, A18。

## 精確差異與第一未驗證接點

### G01｜GAP
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/services/gateway/natural_language_control.py:227`；SHA-256：`6b09f69e3ac8b75a56574d6cd340c1e71becb22a67d359211177a952f45a63cb`。
D1_INTENT.source固定為FOUNDER_NATURAL_LANGUAGE；本次只證實來源表示，尚未證實一般會員經此入口或實際越權。
第一未驗證接點：一般身分封包到此入口的真實呼叫與驗簽。
最小處理：沿既有member_sovereign_context_adapter綁定經驗證的來源、委任、組織及效果；保留開發者入口，避免推定所有呼叫都是Founder。

### G02｜GAP
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/core/external_effect_gate.py:44-104`；SHA-256：`564361835f5df7153fe4eb889c37279860245d7e2297e982009c927f522997e4`。
函式存在；限定core/services/tools/tests搜尋只發現測試直接呼叫，入口亦含模組名稱文字，尚未證明正式執行器接線。
第一未驗證接點：正式身分→可信許可→實際執行器→效果收據。
最小處理：沿現有執行器定位接點，重用可信驗簽及既有許可種類；不得自行合成許可或放寬權威清單。

### G03｜GAP
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/core/resource_arbitration.py:620-816`；SHA-256：`de97051b9b5bf87fa8e680488b80c9e2ba7be637e64b72f40142ae7b0a0a6219`。
已分登錄、可用、合格、偏好及並行集合；雲端選擇主要為供應商級固定ID，尚未見同供應商逐型號、負載、成本及任務版本的完整合格集合。
第一未驗證接點：使用者委任策略→模型級合格集合與固定排序。
最小處理：在既有仲裁函式和能力索引擴充有證據的模型級條件，固定同分resource_id排序，UNKNOWN不得轉0或可用。

### G04｜GAP
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/tools/total_field/w7tp_vertex_candidate_gateway.py:325-389`；SHA-256：`afcd79e436ab5c4f25f064165c32fe627798453113a5d27c95535a95f43f2ec2`。
來源附加固定模型列表並逐型號嘗試；本次未呼叫任何Google模型，無模型現行可用性或父任務預算覆蓋證明。
第一未驗證接點：合格模型及父任務預算→逐次呼叫封套。
最小處理：重用CloudFillPacketBroker；每次嘗試綁定允許模型版本與子封包，父任務次數和費用共同封頂。需官方/專案實測才可列模型合格。

### G05｜GAP
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/tools/total_field_cloud_fill_packet.py:626-816`；SHA-256：`44c8ca234590698dcbb39283718c27deca909f7ca50e5988ef15164fb2951979`。
Broker使用程序內_requests與_consumed_nonces；本次尚未觀測跨程序/重啟持久防重放接點，不擴大為全系統無防重放。
第一未驗證接點：重啟/並行之後的唯一消耗與結果交付。
最小處理：定位並重用既有持久nonce帳本和可信發行機制，補足並行、逾期、重啟、收據遺失的限定反證。

### G06｜GAP
證據類別：SOURCE_IMPLEMENTATION；節點：MSI；物件：`/home/taiji_admin/continue_founder_total_field_ollama_bridge.py:116-543`；SHA-256：`efb9ddd5b56f81baad892e8dd032cb13685ab21424269188c4accab7fb3f1036`。
MSI實際橋接來源位於Git舊樹外，包含動態上下文及可選Gemini靜態補充；本次沒有推論或雲端呼叫，父任務預算接線未知。
第一未驗證接點：實際橋接載入來源→可選補充的委任與預算。
最小處理：只沿實際橋接及既有規則基座定位，不以舊Git樹缺檔判斷能力不存在，不另造橋接核心。

### G07｜UNKNOWN
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/core/msi_local_llm_route.py:125-189`；SHA-256：`a510e2e66dfafe7c1835c516f47c068b7d5d71757d69ad0eb46233a42cad8871`。
已有LAN主機可達與模型健康分離，並阻擋LAN可達時的替代路徑；本次尚未進行完整呼叫/重啟驗收。
第一未驗證接點：來源條件→當次實際路由及執行效果。
最小處理：保留既有LAN優先條件，針對精確節點/物件做觀測；不更動VPN、防火牆、DNS、路由器或遠端管理通路。

### G08｜UNKNOWN
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/products/eight_dimensional_generative_memory/w7tp_endpoint_rule_handshake_v1.py:SOURCE_BASELINE`；SHA-256：`7b3099d2d61d5355e4066fa8ff3a4deb287b47f7a3f0234cda9ab55e29b701e5`。
正式工作樹與D6隔離待審來源不同；差異不能單獨證明通訊不相容。成本候選維持獨立任務。
第一未驗證接點：相同任務和規則版本→完整成本與效果等價驗收。
最小處理：不擴充或部署D6候選；本任務只引用既有成本契約，記錄全部前置及額外查詢。

### G09｜ALIGNED
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json:1-34`；SHA-256：`74752efc39ab9cf035a91b9e3886450d24e7bbf6ca2464d367e94cffd157f1f2`。
SOURCE_BASELINE另列active目錄下不存在的同名指標；本次沿master_index讀到V2.3正典。此為座標修正，不是正典缺失。
第一未驗證接點：正確索引→所有必要消費者本次綁定。
最小處理：引用實際master_index指標；保留原始錯誤座標作更正脈絡，不重開已完成正典任務。

### G10｜UNKNOWN
證據類別：SOURCE_IMPLEMENTATION；節點：taiji01；物件：`/home/taiji_admin/Taiji_Hub/services/gateway/openai_compat.py:60-73`；SHA-256：`8eca754fbb8312e8fba86976882c06bba27bbb0b47f552a949f78371b125f4ac`。
相容chat入口的來源先回409導向受治理路徑；後方舊fallback程式不可據此當成執行中的繞行。
第一未驗證接點：實際HTTP入口是否載入此來源。
最小處理：保留受治理入口，限定重驗409與正式路由，不以不可達舊碼推定當前能力。

## 送審及交付邊界

原T-029兩次Codex工作均未產生指定三檔，這次接續該缺口而非重做已完成產品。驗收矩陣完整列出20個案例及24項要求；各產品案例維持NOT_RUN，沒有用格式檢查冒充端到端通過。來源審查的真實回執另留證據，不把固定點ALLOW誤當部署許可。正式發行、模型外部費用、會員作用及權限變更仍逐作用核對既有可信許可。

正典座標更正：原基線中的 `runtime/total_field/active/ACTIVE_W7TP_CANONICAL_POINTER.json` 缺檔；本次已沿 `master_index/ACTIVE_W7TP_CANONICAL_POINTER.json` 找到既有V2.3，不宣稱全系統正典失效。
