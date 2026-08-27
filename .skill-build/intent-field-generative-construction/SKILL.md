---
name: intent-field-generative-construction
description: 將零散意圖片段建構為來源可追溯、受總場治理、經正典 8D／ADI 映射、十二段初掃、七段紅隊、四功能收據、程式閉環與生成式程式傳輸拓印的候選產物。用於新產品、新流程、跨節點程式重構、需求補全、影響分析或由少量意圖生成必要程式產物；必須分離 USER_EXPLICIT 與 AI_COMPLETION_HYPOTHESIS，且不得把 AI 補全、producer、runner、測試、封包、旅程收據或跨節點一致當成授權、真實性或正式啟用。
---

# 意圖場生成式建構

## 執行前必讀

完整讀取：

1. [references/workflow-contract.md](references/workflow-contract.md)：階段、人格、閉環與紅隊回修。
2. [references/authority-and-safety.md](references/authority-and-safety.md)：來源、權威、敏感資料與效果邊界。
3. [references/user-journey-gates.md](references/user-journey-gates.md)：真實使用者旅程硬閘。
4. [references/artifact-contract.md](references/artifact-contract.md)：輸入與最小硬碟產物契約。
5. [references/verification-and-receipts.md](references/verification-and-receipts.md)：獨立驗證、實際旅程、紅隊及跨節點收據綁定。
6. [references/relational-closure.schema.json](references/relational-closure.schema.json)：`mainline_relation`、十軸 `continuation_distance`、`supply_demand_fit` 與 detached `FIELD_EVIDENCE` 綁定的機器可驗證契約。

## 必守流程

1. 鎖定節點、worktree 實際根目錄、版本、總場權威、效果政策、排除範圍與讀取預算。預設效果只允許在新 run 目錄建立候選檔，禁止覆寫與外部效果。
2. 把使用者明說內容標成 `USER_EXPLICIT`；把數位新創總監、產品負責人、模型先驗或其他 AI 補全標成 `AI_COMPLETION_HYPOTHESIS` 或 `MODEL_PRIOR_CANDIDATE`。禁止混寫。
3. 固定同時採用 `REAL_HUMAN_USER` 與 `SILICON_VALLEY_DIGITAL_STARTUP_DIRECTOR_PRODUCT_OWNER` 觀點。後者補價值、營運、成本、留存、擴充與退出候選，但不得取代人類入口、實際收據或權威，商業價值不得壓過治理。
4. 建立正典 8D 與 ADI 座標。`HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD` 只表示正典八面動態選用，不是第九維，也不授權。八面固定為 `identity_source`、`authority_governance`、`structure_contract`、`supply_dependency`、`function_execution`、`causality_validation`、`sequence_version`、`risk_boundary`。
5. 僅在無效果預分析候選中使用 3D-7D。涉及身分角色權威治理、秘密／隱私／會員／營業秘密、跨節點正式 runtime／DB／部署／路由、外部不可逆效果或不確定前沿時，強制完整 8D；資源節省不得降階。
6. 四功能必備且只能記為 `UNVERIFIED`：`ANALYSIS`、`TRANSFER`、`CONSTRUCTION`、`ADDRESSING`。`enabled`、runner 輸出或 producer 輸出都不是證據。
   `ANALYSIS` 與 `ADDRESSING` 共同負責主線關係與接續距離，不得新增第五功能。分析不得停在檔名、相似度或表面結構；所有推演、模擬、候選組合與修改影響都先在隔離虛擬空間進行。主線只讀，禁止因此授權接線、合併、覆蓋、部署、啟用或其他效果。
7. 按 exact order 完成十二段初掃：`RUNTIME_GAP_LOCALIZATION`、`STATE_FIELD_ANALYSIS`、`HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD`、`ADI_COORDINATE_INDEX`、`CAUSAL_RELATIONAL_SUPPLY_DEPENDENCY_GROUP_FUNCTION_ANALYSIS`、`CODE_LOOP_CLOSURE`、`SECOND_SCAN_DIFF`、`GENERATIVE_TRANSFER_ANALYSIS`、`PROGRAM_TRANSFER_RUBBING`、`RECEIVER_RECONSTRUCTION`、`EQUIVALENT_STATE_VERIFICATION`、`REAL_HUMAN_USER_JOURNEY`。producer 與 runner 對每段只可標 `UNVERIFIED`。
8. 十二段全嘗試且存在已知證據缺口後，才可受限用 `MODEL_PRIOR_CANDIDATE` 或 `EXTERNAL_PRIMARY_SOURCE` 補缺；不得改寫 `USER_EXPLICIT`、正典、權威或效果。補缺後形成 worktree-local `FIELD_EVIDENCE` 普通檔 ref，由 detached verifier 實算 SHA-256，並從最早受影響段重跑全部下游。
9. 調集內部樣式與外部第一手公開樣式，只保存來源參照、版本、授權狀態與雜湊；不得把相似名稱、模型先驗或次級敘述當成來源權威。私有查表、真實權重資料、相位映射、真正 `WHY_IT_RUNS` 與內部推理不得入封包或報告。
10. 產生候選架構與 AI 程式重構配方。任何 `allowed_effects` 只能綁定 `USER_EXPLICIT` 的識別、敘述雜湊與來源參照，不得由假設擴權。
    每一分析／定址階段都必須回答主線可否接續，並輸出 `candidate_relation`、`continuation_distance`、`missing_gates`、`first_breakpoint`、`shortest_continuation_route`。`candidate_relation` 只能是 `CONTINUE`、`FUSE`、`REPLACE`、`PARALLEL_SHADOW`、`ISOLATE`、`HOLD`。
    `continuation_distance` 必須是十軸向量，exact axes 為 `semantic`、`structure_contract`、`dependency`、`tests`、`runtime_wiring`、`data_migration`、`governance_authority`、`security`、`cross_node`、`recovery`。每軸必須有 `state` 與 `evidence_refs`；`state` 可用 `ALIGNED`、`DELTA`、`UNKNOWN`。不得加總為單一分數，不得用檔案數、coverage 百分比或相似度冒充接續距離。任一軸 `UNKNOWN` 立即 `HOLD`，列第一斷點、必要閘與最短接續路線。
    關係硬閘固定為：`CONTINUE` 必驗輸入輸出契約、依賴、版本；`FUSE` 必驗重疊供給、優先序、雙執行風險、權威衝突；`REPLACE` 必驗所有消費者覆蓋、行為等價、資料遷移、退場與回復；`PARALLEL_SHADOW` 只能隔離、無效果、不影響主線；`ISOLATE` 用於無關或風險邊界；`HOLD` 用於未知軸或必要閘未閉合。相似度不得升格任何關係；未閉合只能 `PARALLEL_SHADOW`、`ISOLATE` 或 `HOLD`。
    供需依存必須密合，逐項列 `old_demand_set` → `new_supply_mapping`、`uncovered_demands`、`extra_side_effects`、`unknown_dynamic_consumers`、`dependency_cycles`、`authority_conflicts`、`recovery_route`。任一必要缺口非空不得 `REPLACE` 或覆蓋，只能 `PARALLEL_SHADOW` 或 `HOLD`。安全順序固定 `expand` → `migrate` → `deprecate`，每步都必須有回復。
11. 沿「定義→實作→呼叫→輸入輸出→錯誤處理→測試→接線→執行證據→回復」閉環核對，並在 `INTENT`、`SOURCE`、`ARCHITECTURE`、`CODE`、`HUMAN_JOURNEY`、`CROSS_NODE_TRANSFER`、`PRE_ACTIVATION` 七段紅隊。發現可修問題時回到最早受影響環節修正、重跑並重驗全部下游，最多三輪；超限即 `HOLD` 並列第一斷點。
12. 建立生成式程式傳輸拓印，固定使用 `IFGC-GTP` 1.0.0 與穩定 recipe 語意，只帶意圖雜湊、座標、來源、產物雜湊、生成配方、測試、引用與接收端重構條件，不嵌完整來源；語意重構不得宣稱位元組一致。
13. 由 detached verifier 重算輸入、十二段、四功能、紅隊、候選封包、diff／rubbing／receiver／equivalent 收據與雜湊鏈。producer、runner、caller 自報的 executed、`FIELD_EVIDENCE` 或 verifier_result 不採信；完整性不等於真實性，真實性不等於權威。

## 狀態語意

- `CANDIDATE`：結構完整候選，不代表旅程、權威或正式效果。
- `HOLD`：存在未閉合硬閘；只阻擋相依群組，不拖住無相依的安全群組。
- `STRUCTURE_AND_HASH_CHECK_PASS`：本版最高狀態，只表示指定結構、canonical serialization 與 SHA-256 鏈閉合。
- `RUNTIME_EVIDENCE_UNVERIFIED`：固定保留；十二段、四功能與收據不能證明實際 runtime 執行。
- `USER_JOURNEY_EVIDENCE_UNVERIFIED`：固定保留；旅程收據不能證明真實使用者或 runner 實際旅程。
- `CROSS_NODE_REPLAY_UNVERIFIED`：固定保留；接收端與等價收據不能證明跨節點真實重放。
- `AUTHENTICITY_UNVERIFIED`：固定保留；本版沒有封包外固定可信信任根、受信 runner 或原子 nonce ledger。
- `ACTIVATION_NOT_AUTHORIZED`：本技能固定保留；即使完整性、旅程與 authority 聲稱通過，也不得由本技能啟用。

任何結構與雜湊閉合輸出都必須同時列出 `RUNTIME_EVIDENCE_UNVERIFIED`、`USER_JOURNEY_EVIDENCE_UNVERIFIED`、`CROSS_NODE_REPLAY_UNVERIFIED`、`AUTHENTICITY_UNVERIFIED`、`ACTIVATION_NOT_AUTHORIZED`。封包只承載身分、意圖、來源與重構條件，不是授權。caller signature 與 authority 只能記為 `claimed_signature_state` 與 `claimed_authority_state`。精確位元組、歷史、簽章、衝突與遠端複寫仍依賴 Git 或經驗證的內容定址儲存。

## 工具與決定權

- 候選 producer：`python3 scripts/build_intent_field_candidate.py --input <已去識別化JSON>`；只顯示候選雜湊，不寫檔、不輸出通過狀態。
- 獨立 verifier：`python3 scripts/verify_intent_field_construction.py --worktree-root <根> --input-ref <相對路徑> --verification-bundle-ref <相對路徑> --output-dir <新run相對目錄>`。
- 僅驗證：對 verifier 加上 `--validate-only`，不得留下產物。
- 測試：`python3 -m unittest discover -s scripts -p 'test_intent_field_*.py'`。

verifier 只把 `INTENT_FIELD_GENERATIVE_PACKET.json`、其 SHA-256 與 `SEAL.json` 寫入 worktree 內的新 run 目錄。報告、紅隊細節、十二段摘要、四功能摘要與差異摘要只在當次畫面／記憶體展示。

producer 對三個關係欄位只接受明示、無預設值且綁定 SHA-256 的 worktree-local `FIELD_EVIDENCE` 與 stage receipt。detached verifier 必須以自己的欄位／交叉規則實作重算，核對 evidence artifact、stage receipt、producer relational hash 與 candidate bytes；producer 自報不得取代此驗證。`SEAL.json` 必須實際帶入三欄摘要與 detached 關係證據結果，禁止形成未消費死欄位。

## 禁止事項

- 不讀取或輸出秘密、原始權杖、會員明文、失敗佇列原始內容或私有 8D／ADI 技術內核；名稱、規則、文件敘述、placeholder、env_ref、key_ref、weight 參數名與欄位名不得因字樣直接 HOLD。
- 不信任 packet verdict、producer、AI、runner 或 verifier 自稱；只接受獨立重算且內容綁定的 detached 決定。
- 不在未授權下修改正式來源、推送、部署、重啟、寫入資料庫、路由或啟用效果。
- 不以拓印取代 Git 的精確歷史、多人衝突、簽章、遠端複寫與災難復原能力。
