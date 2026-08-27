# 最小產物與拓印契約

## 輸入骨架

輸入使用已去識別化 JSON，至少包含：

```text
intent_id, logical_root_id, node_id, revision
user_explicit[], ai_completion_hypotheses[], allowed_effects[]
perspectives.REAL_HUMAN_USER[]
perspectives.SILICON_VALLEY_DIGITAL_STARTUP_DIRECTOR_PRODUCT_OWNER[]
eight_d.definition{}, eight_d.dynamic_depth{}, eight_d.dimensions{}
adi_map{}
pattern_recall.internal[], pattern_recall.external[]
architecture{}, code_reconstruction{}
runtime_completion_chain{}
initial_scan.sections[]
core_functions{}
mainline_relation{}
continuation_distance{}
supply_demand_fit{}
journey_receipts[]
redteam.max_rounds, redteam.stages{}
provenance_catalog[USER_EXPLICIT, AI_COMPLETION_HYPOTHESIS, FIELD_EVIDENCE, EXTERNAL_PRIMARY_SOURCE, MODEL_PRIOR_CANDIDATE, AUTHORITY_DECISION_REQUIRED]
transfer{}, governance{}
```

`user_explicit` 與 `ai_completion_hypotheses` 在輸入可帶短敘述供當次建構，但硬碟封包只保存敘述 SHA-256。`allowed_effects` 只能引用 `user_explicit` 識別。

## 8D 與動態深度

`eight_d.definition` 必須明列：

- `canonical_dimensions_count=8`
- `dynamic_depth_name=HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD`
- `dynamic_depth_semantics=CANONICAL_EIGHT_FACE_DYNAMIC_SELECTION_ONLY`
- `ninth_dimension=false`
- `grants_authority=false`

`eight_d.dimensions` 只能使用下列 exact keys，且不得增減或改名：

1. `identity_source`
2. `authority_governance`
3. `structure_contract`
4. `supply_dependency`
5. `function_execution`
6. `causality_validation`
7. `sequence_version`
8. `risk_boundary`

`eight_d.dynamic_depth` 可描述本次選用哪些正典面與原因，但不得改變維度集合、權威、效果或語意。3D-7D 欄位只可出現在 `NO_EFFECT_PRE_ANALYSIS_CANDIDATE`；若涉及身分角色權威治理、秘密／隱私／會員／營業秘密、跨節點正式 runtime／DB／部署／路由、外部不可逆效果或不確定前沿，必須轉完整 8D。

## Runtime 閉環與四功能

`runtime_completion_chain` 必須逐項引用「定義→實作→呼叫→輸入輸出→錯誤處理→測試→接線→執行證據→回復」的 worktree 普通檔 ref、stage receipt 與 detached SHA-256。存在任何 symlink、外部絕對路徑、半成品或自報結果，該鏈即 `HOLD`。

`core_functions` 必須含四個 exact keys，且每個 `state` 只能是 `UNVERIFIED`：

```text
ANALYSIS
TRANSFER
CONSTRUCTION
ADDRESSING
```

`enabled=true`、工具存在、runner 輸出或 producer 輸出都不是四功能證據。

`ANALYSIS` 與 `ADDRESSING` 共同負責 `mainline_relation`、`continuation_distance`、`supply_demand_fit`、`missing_gates`、`first_breakpoint` 與 `shortest_continuation_route`；這不是第五功能。所有推演、模擬、候選組合與修改影響只可在隔離虛擬空間完成，主線只讀，且不得因此授權接線、合併、覆蓋、部署或啟用。

## 主線關係、十軸距離與供需密合

本節的 normative machine schema 是 [relational-closure.schema.json](relational-closure.schema.json)。三欄不得由 producer 補預設值；輸入必須另含 `relational_evidence`，exact 綁定 `evidence_class=FIELD_EVIDENCE`、worktree-local canonical JSON `artifact_ref`／`artifact_sha256` 及獨立 `stage_receipt_ref`／`stage_receipt_sha256`。evidence artifact 必須逐位帶入三欄與 `input_revision`，stage receipt 必須綁定 artifact 路徑、SHA-256、revision、`state=STAGED`、`runner_verdict=UNVERIFIED`、`grants_authority=false`。

`mainline_relation.candidate_relation` 只能是：

```text
CONTINUE
FUSE
REPLACE
PARALLEL_SHADOW
ISOLATE
HOLD
```

`mainline_relation` exact keys 為 `candidate_relation`、`hard_gates`、`missing_gates`、`first_breakpoint`、`shortest_continuation_route`。每個 hard gate 只含 `state=PASS|FAIL|UNKNOWN` 與非空 `evidence_refs`；關係對應 hard gate exact 為：

- `CONTINUE`：`input_output_contract`、`dependencies`、`version`。
- `FUSE`：`overlapping_supply`、`priority`、`dual_execution_risk`、`authority_conflict`。
- `REPLACE`：`all_consumers`、`behavioral_equivalence`、`data_migration`、`exit_and_recovery`。
- `PARALLEL_SHADOW`：`isolation`、`no_effect`、`no_mainline_impact`。
- `ISOLATE`：`unrelated_or_risk_boundary`。
- `HOLD`：只保存已實際評估的上述 gate；至少一個 `missing_gates`、其第一項作為 `first_breakpoint`，並有非空 `shortest_continuation_route`。

`missing_gates` 為有序且不重複的實際缺閘座標。沒有缺閘時必須明示空陣列，`first_breakpoint=null` 且 route 為空；這表示經證據閉合後沒有斷點，不是 placeholder。存在缺閘時 `first_breakpoint` 必須等於第一項，route 每步必含非空 `evidence_refs`。

每一分析／定址階段都必須同時輸出：

```text
candidate_relation
continuation_distance
missing_gates
first_breakpoint
shortest_continuation_route
```

`continuation_distance` 必須是十軸向量，exact axes 為：

```text
semantic
structure_contract
dependency
tests
runtime_wiring
data_migration
governance_authority
security
cross_node
recovery
```

每軸必須有 `state` 與 `evidence_refs`；`state` 只能使用 `ALIGNED`、`DELTA`、`UNKNOWN`。不得加總為單一分數，不得用檔案數、coverage 百分比或相似度冒充接續距離。任一軸 `UNKNOWN` 立即 `HOLD`，並列入 `first_breakpoint`、`missing_gates` 與 `shortest_continuation_route`。

關係硬閘：

- `CONTINUE` 必驗輸入輸出契約、依賴、版本。
- `FUSE` 必驗重疊供給、優先序、雙執行風險、權威衝突。
- `REPLACE` 必驗所有消費者覆蓋、行為等價、資料遷移、退場與回復。
- `PARALLEL_SHADOW` 只能隔離、無效果、不影響主線。
- `ISOLATE` 用於無關或風險邊界。
- `HOLD` 用於未知軸或必要閘未閉合。

相似度不得升格任何關係；未閉合只能 `PARALLEL_SHADOW`、`ISOLATE` 或 `HOLD`。

`supply_demand_fit` 必須逐項列：

```text
old_demand_set -> new_supply_mapping
uncovered_demands
extra_side_effects
unknown_dynamic_consumers
dependency_cycles
authority_conflicts
recovery_route
```

`old_demand_set` 每項為 `id` 與非空 `evidence_refs`；`new_supply_mapping` 每項把一個既有 `demand_id` 映射到非空且不重複的 `supply_ids` 並附證據。每個舊需求必須恰好出現在 mapping 或 `uncovered_demands`，不得同時出現。五種缺口項目都以 `id` 與非空證據表示。`recovery_route` exact order 為三步，每步含證據及明確 `rollback.action` 與 rollback 證據。

供需依存必須密合，不得用 coverage 百分比代替。任一必要缺口非空不得 `REPLACE` 或覆蓋，只能 `PARALLEL_SHADOW` 或 `HOLD`。安全順序固定 `expand` → `migrate` → `deprecate`，且每步必須有回復。

## 十二段初掃

`initial_scan.sections` 必須依 exact order 記錄：

1. `RUNTIME_GAP_LOCALIZATION`
2. `STATE_FIELD_ANALYSIS`
3. `HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD`
4. `ADI_COORDINATE_INDEX`
5. `CAUSAL_RELATIONAL_SUPPLY_DEPENDENCY_GROUP_FUNCTION_ANALYSIS`
6. `CODE_LOOP_CLOSURE`
7. `SECOND_SCAN_DIFF`
8. `GENERATIVE_TRANSFER_ANALYSIS`
9. `PROGRAM_TRANSFER_RUBBING`
10. `RECEIVER_RECONSTRUCTION`
11. `EQUIVALENT_STATE_VERIFICATION`
12. `REAL_HUMAN_USER_JOURNEY`

每段都必須嘗試。producer 與 runner 對每段只能留下 `UNVERIFIED`。十二段全嘗試且留下已知證據缺口後，才可受限加入 `MODEL_PRIOR_CANDIDATE` 或 `EXTERNAL_PRIMARY_SOURCE` 補缺；補缺不得改寫 `USER_EXPLICIT`、正典、權威或效果。補後必須形成 worktree-local `FIELD_EVIDENCE` 普通檔 ref，由 detached verifier 實算 SHA-256，並從最早受影響段重跑全部下游。

## 硬碟只允許三個必要檔

1. `INTENT_FIELD_GENERATIVE_PACKET.json`
2. `INTENT_FIELD_GENERATIVE_PACKET.sha256`
3. `SEAL.json`

分析報告、紅隊細節、十二段摘要、四功能摘要、差異摘要與人類說明只輸出到標準輸出，由當次畫面／記憶體展示，不另存檔。驗證失敗不得留下半成品。

## 生成式程式傳輸拓印

封包使用下列不變式：

```text
protocol=IFGC-GTP
protocol_version=1.0.0
recipe_semantics=STABLE
canonical_serialization=UTF8_SORTED_KEYS_COMPACT
hash_method=sha256
full_source_embedded=false
receiver_reconstruction_required=true
equivalent_state_verification_required=true
activation_boundary=NOT_AUTHORIZED
dynamic_depth_may_change_semantics=false
```

封包預設只帶：

- 六種來源類別的雜湊及來源標籤。
- 正典 8D 定義、動態深度語意與八面欄位。
- ADI 節點／關係座標與證據參照。
- 內外模式的來源、版本、授權狀態與雜湊。
- 預期產物路徑與雜湊、生成配方參照及參數雜湊。
- runtime 閉環、十二段、四功能、旅程與紅隊的狀態及證據參照。
- diff receipt、rubbing receipt、receiver reconstruction receipt、equivalent state receipt 與逐段 SHA-256 hash chain。
- 跨節點完整性、真實性聲稱、污染、漂移、竄改與回復閘。

不得嵌入完整既有來源、完整檔案編碼、秘密、會員明文、私有查表、真實權重資料、相位映射、真正 `WHY_IT_RUNS` 或內部推理。若重構必須攜帶完整來源，輸出 `HOLD_NOT_GENERATIVELY_RECONSTRUCTABLE`。名稱、規則、文件敘述、placeholder、env_ref、key_ref 與 weight 參數名可安全保存。

`semantic_reconstruction=true` 只表示依規格重建等價意義；必須同時保持 `byte_identity_claim=false`。需要逐位元保存、歷史拓撲、合併、簽章或遠端複寫時，使用 Git 或經驗證的內容定址儲存，不得由拓印冒充。

## 封印

`SEAL.json` 至少記錄協定、封包 SHA-256、狀態集合、detached 結構與雜湊結果、十二段摘要、四功能摘要、mainline relation 摘要、十軸接續距離摘要、供需密合摘要、缺閘／第一斷點／最短接續路線、transfer invariant 摘要、diff／rubbing／receiver／equivalent receipt 摘要、啟用未授權、產物檔名及安全旗標。SHA 檔只對 canonical JSON 封包計算，不含自身，避免自我引用歧義。

結構與雜湊閉合時，`SEAL.json` 最高只可列 `STRUCTURE_AND_HASH_CHECK_PASS`，且必須同時列：

- `RUNTIME_EVIDENCE_UNVERIFIED`
- `USER_JOURNEY_EVIDENCE_UNVERIFIED`
- `CROSS_NODE_REPLAY_UNVERIFIED`
- `AUTHENTICITY_UNVERIFIED`
- `ACTIVATION_NOT_AUTHORIZED`

十二段、四功能與傳輸收據即使結構與雜湊閉合，也不能證明實際執行、真實人類旅程、跨節點真實性、authority 或生產效果。

輸出目錄必須是呼叫者指定的新隔離目錄；拒絕符號連結、既有非空目錄、絕對產物路徑、父路徑穿越及覆寫。
