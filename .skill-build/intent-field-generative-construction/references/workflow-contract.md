# 意圖場生成式建構流程契約

## 固定產品觀點

同時採用兩個觀點，並使兩者受總場治理約束：

- `REAL_HUMAN_USER`：從真實理解、操作成本、可及性、受騙風險、錯誤回復與不同角色權利判斷。
- `SILICON_VALLEY_DIGITAL_STARTUP_DIRECTOR_PRODUCT_OWNER`：從價值假設、產品責任、最小可用閉環、營運成本、留存、可擴充性、供需、持續營運與退出判斷。

把兩個觀點增加的內容一律標成 `AI_COMPLETION_HYPOTHESIS`；只有使用者明確表達可標成 `USER_EXPLICIT`。產品負責人觀點不得取代人類入口、實際收據或權威，商業價值不得壓過治理。

## 建構階段

1. **意圖分離**：保存使用者明說項目的識別與雜湊；另列 AI 補全假設。只允許 `USER_EXPLICIT` 成為效果白名單來源。
2. **雙觀點補全**：補齊價值、角色、失敗、回復、營運與未知邊界，不自行增加效果範圍。
3. **正典 8D／ADI 映射**：`HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD` 只表示正典八面動態選用，不是第九維，也不授權。八面 exact 為 `identity_source`、`authority_governance`、`structure_contract`、`supply_dependency`、`function_execution`、`causality_validation`、`sequence_version`、`risk_boundary`；ADI 只建立座標、關係與未知前沿索引。
4. **降階檢查**：3D-7D 只可用於無效果預分析 `CANDIDATE`。涉及身分角色權威治理、秘密／隱私／會員／營業秘密、跨節點正式 runtime／DB／部署／路由、外部不可逆效果或不確定前沿時，強制完整 8D，資源節省不得降階。
5. **四功能登記**：`ANALYSIS`、`TRANSFER`、`CONSTRUCTION`、`ADDRESSING` 必備，狀態只能是 `UNVERIFIED`；`enabled` 不是證據。
6. **十二段初掃**：依 exact order 全嘗試 `RUNTIME_GAP_LOCALIZATION`、`STATE_FIELD_ANALYSIS`、`HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD`、`ADI_COORDINATE_INDEX`、`CAUSAL_RELATIONAL_SUPPLY_DEPENDENCY_GROUP_FUNCTION_ANALYSIS`、`CODE_LOOP_CLOSURE`、`SECOND_SCAN_DIFF`、`GENERATIVE_TRANSFER_ANALYSIS`、`PROGRAM_TRANSFER_RUBBING`、`RECEIVER_RECONSTRUCTION`、`EQUIVALENT_STATE_VERIFICATION`、`REAL_HUMAN_USER_JOURNEY`；producer 與 runner 只可 `UNVERIFIED`。
7. **受限補缺**：十二段全嘗試且有已知證據 gap 後，才可使用 `MODEL_PRIOR_CANDIDATE` 或 `EXTERNAL_PRIMARY_SOURCE` 補缺；不得改寫 `USER_EXPLICIT`、正典、權威或效果。補後形成 worktree-local `FIELD_EVIDENCE` 普通檔 ref，由 detached verifier 實算 hash，並從最早受影響段重跑全部下游。
8. **內外樣式召回**：先找內部正式模式，再找可公開引用的外部模式；只採用有版本、完整性、授權與來源權威證據者。
9. **架構與程式重構**：以引用、產物雜湊與生成配方建立候選；禁止內嵌完整來源或把普通複製包裝成生成式重構。
10. **程式閉環**：逐環核對「定義→實作→呼叫→輸入輸出→錯誤處理→測試→接線→執行證據→回復」。
11. **人類旅程收據硬閘**：至少涵蓋首次、回訪、低權限、待審、核准、撤銷或過期、錯誤或逾時回復，並涵蓋桌機與行動，或提供有證據的不適用；每一角色都要看見明確結果與可回復出口。收據閉合仍保留 `USER_JOURNEY_EVIDENCE_UNVERIFIED`。
12. **跨節點拓印**：只帶意圖、座標、來源與產物雜湊、生成配方、測試、引用、diff／rubbing／receiver／equivalent receipt 與 hash chain；接收端重驗，不自動啟用，且保留 `CROSS_NODE_REPLAY_UNVERIFIED`。

## 主線關係與接續距離

`ANALYSIS` 與 `ADDRESSING` 共同回答主線可否接續，這不是第五功能。分析不得停在檔名、相似度或表面結構；所有推演、模擬、候選組合與修改影響先在隔離虛擬空間完成。主線只讀，禁止因此授權接線、合併、覆蓋、部署、啟用或其他效果。

每一分析／定址階段都必須輸出：

```text
candidate_relation
continuation_distance
missing_gates
first_breakpoint
shortest_continuation_route
```

`candidate_relation` 只能是 `CONTINUE`、`FUSE`、`REPLACE`、`PARALLEL_SHADOW`、`ISOLATE`、`HOLD`。

`continuation_distance` 必須是十軸向量，exact axes 為 `semantic`、`structure_contract`、`dependency`、`tests`、`runtime_wiring`、`data_migration`、`governance_authority`、`security`、`cross_node`、`recovery`。每軸必須有 `state` 與 `evidence_refs`；`state` 可用 `ALIGNED`、`DELTA`、`UNKNOWN`。不得加總為單一分數，不得用檔案數、coverage 百分比或相似度冒充接續距離。任一軸 `UNKNOWN` 立即 `HOLD`，列第一斷點、必要閘與最短接續路線。

關係硬閘固定：

- `CONTINUE` 必驗輸入輸出契約、依賴、版本。
- `FUSE` 必驗重疊供給、優先序、雙執行風險、權威衝突。
- `REPLACE` 必驗所有消費者覆蓋、行為等價、資料遷移、退場與回復。
- `PARALLEL_SHADOW` 只能隔離、無效果、不影響主線。
- `ISOLATE` 用於無關或風險邊界。
- `HOLD` 用於未知軸或必要閘未閉合。

相似度不得升格任何關係；未閉合只能 `PARALLEL_SHADOW`、`ISOLATE` 或 `HOLD`。

供需依存必須密合，不是 coverage 百分比。逐項列 `old_demand_set` → `new_supply_mapping`、`uncovered_demands`、`extra_side_effects`、`unknown_dynamic_consumers`、`dependency_cycles`、`authority_conflicts`、`recovery_route`。任一必要缺口非空不得 `REPLACE` 或覆蓋，只能 `PARALLEL_SHADOW` 或 `HOLD`。安全順序固定 `expand` → `migrate` → `deprecate`，且每步必須有回復。

## 傳輸不變式

所有 transfer 物件必須 exact 包含：

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

`SECOND_SCAN_DIFF`、`PROGRAM_TRANSFER_RUBBING`、`RECEIVER_RECONSTRUCTION`、`EQUIVALENT_STATE_VERIFICATION` 必須各有 receipt，並以前段輸出 SHA-256 綁定後段輸入 SHA-256。語意重構不得宣稱位元組一致。

## 七段比例化紅隊

每段依影響半徑配置測試量；小型局部變更仍至少一個正例與一個反例，高權限、跨節點或不可逆效果增加邊界與資源測試。

1. `INTENT`：挑戰假設、使用價值、需求真實性、補 `FIELD_EVIDENCE` 偽裝及暗黑模式。
2. `SOURCE`：檢查投毒、版本漂移、授權、完整性、秘密混入、真實性與來源權威混淆。
3. `ARCHITECTURE`：檢查動態 8D 自授權、越權、隱私、擴充、單點失敗及成本失控。
4. `CODE`：檢查注入、路徑逃逸、資源耗盡、重放、偽造驗證、秘密外洩及自報結果。
5. `HUMAN_JOURNEY`：檢查誤導、弱權限、撤銷、桌機／行動差異、可及性、錯誤回復及不同角色待遇。
6. `CROSS_NODE_TRANSFER`：檢查 transfer invariant、接收 hash、receiver reconstruction、equivalent state、污染、節點漂移、竄改及回復能力。
7. `PRE_ACTIVATION`：檢查假結果、真實性混淆、權威失效、效果越界、回復失效及證據過期。

每段發現可修問題時回到最早受影響環節修正，再從該環向後重驗。最多三輪；第三輪後仍有阻斷即輸出 `HOLD` 與第一斷點。不得只產生報告，也不得以一個失敗拖住沒有相依關係的安全群組。

## 狀態與閉環

- 結構與來源契約通過：加入 `CANDIDATE`。
- 任何硬閘失敗：加入 `HOLD`，停止產物寫入。
- detached verifier 重算結構、canonical serialization 與 SHA-256 鏈閉合：最高加入 `STRUCTURE_AND_HASH_CHECK_PASS`。
- 全程固定保留 `RUNTIME_EVIDENCE_UNVERIFIED`、`USER_JOURNEY_EVIDENCE_UNVERIFIED`、`CROSS_NODE_REPLAY_UNVERIFIED`、`AUTHENTICITY_UNVERIFIED`、`ACTIVATION_NOT_AUTHORIZED`。

把修正、測試、接線、執行、真實性與權威分開判定。完整性不等於真實性，真實性不等於權威。沒有封包外固定可信信任根、受信 runner 或原子 nonce ledger；caller signature 與 authority 只能記為 `claimed_signature_state` 與 `claimed_authority_state`。
